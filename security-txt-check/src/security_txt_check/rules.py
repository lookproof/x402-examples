"""Parsing and validation of security.txt content (RFC 9116 sections 2 and 4)."""

from __future__ import annotations

import re
import urllib.parse
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from .findings import Finding, Severity
from .signature import WEAK_HASHES, SignatureFormatError, Verifier, VerifyResult, is_signed, split_cleartext

# Field name (as written in RFC 9116 / the IANA registry) -> allowed URI schemes.
URI_FIELDS: dict[str, tuple[str, ...]] = {
    "Acknowledgments": ("https",),
    "Canonical": ("https",),
    "Contact": ("https", "mailto", "tel"),
    "Encryption": ("https", "dns", "openpgp4fpr"),
    "Hiring": ("https",),
    "Policy": ("https",),
    "CSAF": ("https",),
}
KNOWN_FIELDS = {name.lower(): name for name in [*URI_FIELDS, "Expires", "Preferred-Languages"]}
SINGLE_FIELDS = {"Preferred-Languages"}  # Expires has its own check
MISSPELLINGS = {
    "acknowledgements": "Acknowledgments",
    "acknowledgement": "Acknowledgments",
    "acknowledgment": "Acknowledgments",
    "contacts": "Contact",
    "expiry": "Expires",
    "expire": "Expires",
    "expiration": "Expires",
    "preferred-language": "Preferred-Languages",
    "signature": "Encryption",
}

_FIELD_RE = re.compile(r"^([A-Za-z0-9-]+):[ \t]*(.*?)[ \t]*$")
_RFC3339_RE = re.compile(
    r"^(\d{4})-(\d{2})-(\d{2})[Tt](\d{2}):(\d{2}):(\d{2})(\.\d+)?([Zz]|[+-]\d{2}:\d{2})$",
)
_LANG_RE = re.compile(r"^[A-Za-z]{1,8}(-[A-Za-z0-9]{1,8})*$")
_SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
MAX_SYNTAX_ERRORS = 5


@dataclass
class Context:
    target: str
    findings: list[Finding] = field(default_factory=list)

    def add(self, check: str, fid: str, severity: Severity, message: str) -> None:
        # Messages quote file content; strip control characters so a file
        # cannot inject lines into logs or GitHub workflow commands.
        clean = "".join(c if c.isprintable() else "?" for c in message)
        if len(clean) > 300:
            clean = clean[:297] + "..."
        self.findings.append(Finding(fid, severity, check, clean, self.target))


@dataclass
class Field:
    name: str
    value: str
    line: int


@dataclass
class Options:
    expires_warn_days: int = 30
    signing_key: str | None = None
    now: datetime | None = None
    verifier: Verifier | None = None


def parse_rfc3339(value: str) -> datetime | None:
    m = _RFC3339_RE.match(value)
    if not m:
        return None
    offset = m.group(8)
    tz = timezone.utc
    if offset not in ("Z", "z"):
        sign = 1 if offset[0] == "+" else -1
        hours, minutes = int(offset[1:3]), int(offset[4:6])
        if hours > 23 or minutes > 59:
            return None
        tz = timezone(sign * timedelta(hours=hours, minutes=minutes))
    second = min(int(m.group(6)), 59)  # RFC 3339 allows a leap second (60)
    frac = m.group(7)
    micro = int((frac[1:] + "000000")[:6]) if frac else 0
    try:
        return datetime(
            int(m.group(1)),
            int(m.group(2)),
            int(m.group(3)),
            int(m.group(4)),
            int(m.group(5)),
            second,
            micro,
            tzinfo=tz,
        )
    except ValueError:
        return None


def parse_fields(ctx: Context, text: str, first_line: int = 1) -> list[Field]:
    fields: list[Field] = []
    errors = 0
    for n, raw in enumerate(text.split("\n"), start=first_line):
        line = raw.rstrip("\r")
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        m = _FIELD_RE.match(line)
        if not m or not m.group(2):
            errors += 1
            if errors <= MAX_SYNTAX_ERRORS:
                why = "field with no value" if m else "not a comment, blank line or 'Field: value'"
                ctx.add("format", "securitytxt-syntax-error", Severity.ERROR, f"Line {n}: {why}: {line.strip()[:80]!r}")
            continue
        name, value = m.group(1), m.group(2)
        fields.append(Field(KNOWN_FIELDS.get(name.lower(), name), value, n))
    if errors > MAX_SYNTAX_ERRORS:
        ctx.add(
            "format",
            "securitytxt-syntax-error",
            Severity.ERROR,
            f"{errors - MAX_SYNTAX_ERRORS} more line(s) with syntax errors not shown",
        )
    return fields


def _check_uri(ctx: Context, f: Field, schemes: tuple[str, ...]) -> None:
    value = f.value
    if not _SCHEME_RE.match(value) or any(c.isspace() for c in value):
        hint = " (write mailto: in front of an email address)" if f.name == "Contact" and "@" in value else ""
        ctx.add("fields", "securitytxt-invalid-uri", Severity.ERROR, f"Line {f.line}: {f.name} is not a URI{hint}")
        return
    scheme = value.split(":", 1)[0].lower()
    if scheme == "http":
        ctx.add(
            "fields",
            "securitytxt-insecure-uri",
            Severity.ERROR,
            f"Line {f.line}: {f.name} uses http://; web URIs must use https://",
        )
        return
    if scheme not in schemes:
        allowed = ", ".join(s + ":" for s in schemes)
        ctx.add(
            "fields",
            "securitytxt-invalid-uri",
            Severity.ERROR,
            f"Line {f.line}: {f.name} uses {scheme}:, expected {allowed}",
        )
        return
    if scheme == "https":
        parts = urllib.parse.urlsplit(value)
        if not parts.hostname:
            ctx.add("fields", "securitytxt-invalid-uri", Severity.ERROR, f"Line {f.line}: {f.name} has no host name")
    elif scheme == "mailto" and "@" not in value[7:]:
        ctx.add("fields", "securitytxt-invalid-uri", Severity.ERROR, f"Line {f.line}: {f.name} mailto: has no address")


def _same_url(a: str, b: str) -> bool:
    pa, pb = urllib.parse.urlsplit(a), urllib.parse.urlsplit(b)
    return (pa.scheme.lower(), (pa.hostname or ""), pa.port, pa.path or "/") == (
        pb.scheme.lower(),
        (pb.hostname or ""),
        pb.port,
        pb.path or "/",
    )


def check_fields(ctx: Context, fields: list[Field], opts: Options, source_url: str | None, signed: bool) -> None:
    by_name: dict[str, list[Field]] = {}
    for f in fields:
        by_name.setdefault(f.name, []).append(f)

    for name, items in by_name.items():
        if name.lower() not in KNOWN_FIELDS:
            hint = MISSPELLINGS.get(name.lower())
            extra = f"; did you mean {hint}?" if hint else ""
            ctx.add(
                "fields",
                "securitytxt-unknown-field",
                Severity.INFO,
                f"Line {items[0].line}: unknown field {name}{extra}",
            )
        elif name in SINGLE_FIELDS and len(items) > 1:
            lines = ", ".join(str(f.line) for f in items)
            ctx.add(
                "fields",
                "securitytxt-field-repeated",
                Severity.ERROR,
                f"{name} must appear at most once (lines {lines})",
            )

    for f in fields:
        if f.name in URI_FIELDS:
            _check_uri(ctx, f, URI_FIELDS[f.name])

    if not by_name.get("Contact"):
        ctx.add("fields", "securitytxt-contact-missing", Severity.ERROR, "No Contact field; at least one is required")

    _check_expires(ctx, by_name.get("Expires", []), opts)

    for f in by_name.get("Preferred-Languages", []):
        bad = [t.strip() for t in f.value.split(",") if not _LANG_RE.match(t.strip())]
        if bad:
            ctx.add(
                "fields",
                "securitytxt-invalid-language",
                Severity.WARN,
                f"Line {f.line}: not language tags (RFC 5646): {', '.join(bad)[:80]}",
            )

    canonical = [f.value for f in by_name.get("Canonical", [])]
    if canonical and source_url and not any(_same_url(c, source_url) for c in canonical):
        ctx.add(
            "fields",
            "securitytxt-canonical-mismatch",
            Severity.WARN,
            f"Fetched from {source_url}, which is not listed in Canonical ({', '.join(canonical)[:120]})",
        )
    if signed and not canonical:
        ctx.add(
            "signature",
            "securitytxt-signed-no-canonical",
            Severity.WARN,
            "The file is signed but has no Canonical field, so the signed file could be served from any site",
        )


def _check_expires(ctx: Context, items: list[Field], opts: Options) -> None:
    if not items:
        ctx.add("expires", "securitytxt-expires-missing", Severity.ERROR, "No Expires field; exactly one is required")
        return
    if len(items) > 1:
        lines = ", ".join(str(f.line) for f in items)
        ctx.add(
            "expires",
            "securitytxt-expires-multiple",
            Severity.ERROR,
            f"Expires appears {len(items)} times (lines {lines})",
        )
    f = items[0]
    when = parse_rfc3339(f.value)
    if when is None:
        ctx.add(
            "expires",
            "securitytxt-expires-invalid",
            Severity.ERROR,
            f"Line {f.line}: Expires {f.value[:40]!r} is not an RFC 3339 date-time, e.g. 2027-01-31T23:59:59Z",
        )
        return
    now = opts.now or datetime.now(timezone.utc)
    left = when - now
    stamp = when.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    if left <= timedelta(0):
        days = (-left).days
        ago = "today" if days == 0 else f"{days} day{'s' if days != 1 else ''} ago"
        ctx.add(
            "expires",
            "securitytxt-expired",
            Severity.ERROR,
            f"Expired {stamp} ({ago}); researchers should treat it as stale",
        )
    elif left < timedelta(days=opts.expires_warn_days):
        days = left.days
        when_txt = "within a day" if days == 0 else f"in {days} day{'s' if days != 1 else ''}"
        ctx.add("expires", "securitytxt-expires-soon", Severity.WARN, f"Expires {stamp}, {when_txt}")
    elif left > timedelta(days=366):
        ctx.add(
            "expires",
            "securitytxt-expires-too-far",
            Severity.WARN,
            f"Expires {stamp}, {left.days} days away; RFC 9116 recommends less than a year",
        )


def _verify(ctx: Context, raw: bytes, opts: Options) -> None:
    if not opts.signing_key:
        ctx.add(
            "signature",
            "securitytxt-signature-not-verified",
            Severity.INFO,
            "Signed, but no signing key was given, so the signature was not verified",
        )
        return
    from .signature import gpg_verify

    verifier = opts.verifier or gpg_verify
    try:
        result = verifier(raw, opts.signing_key)
    except Exception as exc:  # noqa: BLE001 - report, never pass silently
        result = VerifyResult("error", f"{type(exc).__name__}: {exc}")
    if result.status == "good":
        return
    if result.status == "expired-key":
        ctx.add("signature", "securitytxt-signature-key-expired", Severity.WARN, result.detail)
    elif result.status == "error":
        ctx.add("signature", "securitytxt-signature-check-failed", Severity.ERROR, result.detail)
    else:
        ctx.add("signature", "securitytxt-signature-invalid", Severity.ERROR, result.detail)


def check_content(ctx: Context, raw: bytes, opts: Options, source_url: str | None = None) -> None:
    """Validate the bytes of a security.txt file."""
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        ctx.add("format", "securitytxt-invalid-encoding", Severity.ERROR, f"Not valid UTF-8 (byte {exc.start})")
        text = raw.decode("utf-8", "replace")
    text = text.removeprefix("﻿")

    signed = is_signed(text)
    first_line = 1
    if signed:
        try:
            clear = split_cleartext(text)
        except SignatureFormatError as exc:
            ctx.add("signature", "securitytxt-signature-malformed", Severity.ERROR, str(exc))
            # Still check the fields: keep only lines that name a known field.
            kept = [ln.removeprefix("- ") for ln in text.split("\n")]
            text = "\n".join(ln for ln in kept if ln.split(":", 1)[0].strip().lower() in KNOWN_FIELDS)
        else:
            if clear.leading or clear.trailing:
                where = "before the signed message" if clear.leading else "after the signature"
                ctx.add(
                    "signature",
                    "securitytxt-unsigned-content",
                    Severity.ERROR,
                    f"There is text {where}; it is not covered by the signature",
                )
            weak = [h for h in [*clear.hash_headers, clear.packet_hash or ""] if h in WEAK_HASHES]
            if weak:
                ctx.add(
                    "signature",
                    "securitytxt-signature-weak-hash",
                    Severity.WARN,
                    f"Signed with {weak[0]}; use SHA256 or stronger",
                )
            _verify(ctx, raw, opts)
            text, first_line = clear.text, clear.text_start_line
    else:
        ctx.add("signature", "securitytxt-not-signed", Severity.INFO, "The file has no OpenPGP signature")

    fields = parse_fields(ctx, text, first_line)
    check_fields(ctx, fields, opts, source_url, signed)
