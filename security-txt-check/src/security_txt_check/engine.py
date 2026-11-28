"""Runs the checks for a list of targets (domains, URLs, local files) and decides pass/fail."""

from __future__ import annotations

import urllib.parse
from collections.abc import Iterable
from dataclasses import dataclass, field

from . import __version__
from .fetch import MAX_BYTES, Fetcher, FetchError, HttpResponse, fetch
from .findings import REGISTRY, Finding, Severity
from .rules import Context, Options, check_content

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_USAGE = 2

WELL_KNOWN = "/.well-known/security.txt"
LEGACY = "/security.txt"
MAX_REDIRECTS = 5


class UsageError(ValueError):
    pass


@dataclass
class Target:
    name: str
    """What the user asked for: a domain, URL or file path."""
    url: str | None = None
    path: str | None = None


@dataclass
class TargetResult:
    target: str
    source: str | None = None
    """URL or path the file was finally read from."""
    findings: list[Finding] = field(default_factory=list)


@dataclass
class FailOn:
    threshold: Severity | None = Severity.ERROR
    ids: frozenset[str] = frozenset()

    def matches(self, finding: Finding) -> bool:
        if finding.id in self.ids:
            return True
        return self.threshold is not None and finding.severity.rank >= self.threshold.rank

    def describe(self) -> str:
        parts = [self.threshold.value] if self.threshold else []
        parts += sorted(self.ids)
        return ",".join(parts) or "none"


def parse_fail_on(value: str) -> FailOn:
    """Parse ``error``, ``warn``, ``info``, ``none`` and/or a comma list of finding ids.

    A severity sets a threshold; ids fail the run regardless of severity, e.g.
    ``error,securitytxt-not-signed`` also fails unsigned files.
    """
    tokens = [t.strip().lower() for t in value.replace("\n", ",").split(",") if t.strip()]
    if not tokens:
        return FailOn()
    threshold: Severity | None = None
    ids: set[str] = set()
    for tok in tokens:
        if tok in ("error", "warn", "info"):
            sev = Severity(tok)
            if threshold is None or sev.rank < threshold.rank:
                threshold = sev
        elif tok in ("none", "never"):
            continue
        elif tok in REGISTRY:
            ids.add(tok)
        else:
            raise UsageError(f"fail-on: unknown severity or finding id {tok!r}")
    return FailOn(threshold, frozenset(ids))


def parse_list(values: Iterable[str]) -> list[str]:
    out: list[str] = []
    for value in values:
        for part in value.replace("\n", ",").replace(" ", ",").split(","):
            part = part.strip()
            if part and part not in out:
                out.append(part)
    return out


def validate_domain(domain: str) -> str:
    name = domain.strip().lower().rstrip(".")
    if "/" in name or "@" in name or ":" in name:
        raise UsageError(f"{domain!r} is not a domain name")
    try:
        name = name.encode("idna").decode("ascii")
    except UnicodeError as exc:
        raise UsageError(f"{domain!r} is not a valid domain name") from exc
    labels = name.split(".")
    if len(labels) < 2 or any(not label or len(label) > 63 for label in labels) or len(name) > 253:
        raise UsageError(f"{domain!r} is not a valid domain name")
    return name


def parse_target(value: str) -> Target:
    """A domain checks ``https://<domain>/.well-known/security.txt``; an https URL is checked as given."""
    if "://" in value:
        parts = urllib.parse.urlsplit(value)
        if parts.scheme.lower() != "https":
            raise UsageError(f"{value!r}: security.txt must be served over https")
        if not parts.hostname:
            raise UsageError(f"{value!r} has no host name")
        return Target(value, url=value)
    domain = validate_domain(value)
    return Target(domain, url=f"https://{domain}{WELL_KNOWN}")


def _host(url: str) -> str:
    return (urllib.parse.urlsplit(url).hostname or "").lower()


def _within(host: str, origin: str) -> bool:
    return host == origin or host.endswith("." + origin) or origin.endswith("." + host)


def _get(ctx: Context, url: str, fetcher: Fetcher) -> tuple[str, HttpResponse] | None:
    """GET ``url``, following up to MAX_REDIRECTS https redirects. Returns (final URL, response)."""
    origin = _host(url)
    current = url
    for _ in range(MAX_REDIRECTS + 1):
        try:
            resp = fetcher(current)
        except FetchError as exc:
            fid = "securitytxt-tls-error" if exc.tls else "securitytxt-fetch-failed"
            ctx.add("fetch", fid, Severity.ERROR, f"{current}: {exc}")
            return None
        if resp.status not in (301, 302, 303, 307, 308):
            return current, resp
        if not resp.location:
            ctx.add(
                "fetch", "securitytxt-fetch-failed", Severity.ERROR, f"{current}: HTTP {resp.status} without Location"
            )
            return None
        nxt = urllib.parse.urljoin(current, resp.location.strip())
        if urllib.parse.urlsplit(nxt).scheme.lower() != "https":
            ctx.add(
                "fetch",
                "securitytxt-insecure-redirect",
                Severity.ERROR,
                f"{current} redirects to {nxt}, which is not https",
            )
            return None
        if not _within(_host(nxt), origin):
            ctx.add(
                "fetch",
                "securitytxt-redirect-offsite",
                Severity.WARN,
                f"{current} redirects to another site ({_host(nxt)}); make sure you control it",
            )
            origin = _host(nxt)
        current = nxt
    ctx.add(
        "fetch", "securitytxt-too-many-redirects", Severity.ERROR, f"More than {MAX_REDIRECTS} redirects from {url}"
    )
    return None


def _mime(resp: HttpResponse) -> str:
    return resp.content_type.partition(";")[0].strip().lower()


def _looks_like_html(body: bytes) -> bool:
    head = body[:512].lstrip().lower()
    return head.startswith((b"<!doctype html", b"<html", b"<head", b"<?xml"))


def _check_response(ctx: Context, url: str, resp: HttpResponse) -> bool:
    """Checks status, type and size. Returns True when the body should be parsed."""
    mime, _, params = resp.content_type.partition(";")
    mime = mime.strip().lower()
    if resp.status != 200:
        ctx.add("fetch", "securitytxt-fetch-failed", Severity.ERROR, f"{url}: HTTP {resp.status}")
        return False
    if len(resp.body) > MAX_BYTES:
        ctx.add("fetch", "securitytxt-too-large", Severity.ERROR, f"{url}: larger than {MAX_BYTES // 1024} KiB")
        return False
    if mime != "text/plain":
        shown = mime or "no Content-Type"
        ctx.add(
            "fetch", "securitytxt-wrong-content-type", Severity.ERROR, f"{url}: served as {shown}, must be text/plain"
        )
        return not _looks_like_html(resp.body)
    charset = ""
    for p in params.split(";"):
        key, _, value = p.partition("=")
        if key.strip().lower() == "charset":
            charset = value.strip().strip('"').lower()
    if charset != "utf-8":
        found = f"charset={charset}" if charset else "no charset"
        ctx.add(
            "fetch",
            "securitytxt-no-charset",
            Severity.WARN,
            f"{url}: Content-Type has {found}; use text/plain; charset=utf-8",
        )
    return True


def _is_missing(resp: HttpResponse) -> bool:
    if resp.status in (404, 410):
        return True
    # Many sites answer every path with their HTML start page.
    return resp.status == 200 and _looks_like_html(resp.body)


def check_url(target: Target, fetcher: Fetcher, opts: Options) -> TargetResult:
    assert target.url
    ctx = Context(target.name)
    result = TargetResult(target.name)
    got = _get(ctx, target.url, fetcher)
    if got and _is_missing(got[1]):
        found = None
        if urllib.parse.urlsplit(target.url).path == WELL_KNOWN:
            legacy_ctx = Context(target.name)
            legacy_url = target.url[: -len(WELL_KNOWN)] + LEGACY
            legacy = _get(legacy_ctx, legacy_url, fetcher)
            # The legacy path is only a guess, so it counts only when it serves text/plain.
            if legacy and legacy[1].status == 200 and _mime(legacy[1]) == "text/plain":
                found = legacy
                ctx.add(
                    "fetch",
                    "securitytxt-legacy-location",
                    Severity.WARN,
                    f"Found only at {legacy_url}; serve it at {target.url}",
                )
                ctx.findings += legacy_ctx.findings
        if not found:
            why = "an HTML page" if got[1].status == 200 else f"HTTP {got[1].status}"
            ctx.add("fetch", "securitytxt-not-found", Severity.ERROR, f"No security.txt at {target.url} ({why})")
        got = found
    if got:
        final_url, resp = got
        result.source = final_url
        if _check_response(ctx, final_url, resp):
            check_content(ctx, resp.body, opts, source_url=final_url)
    result.findings = ctx.findings
    return result


def check_file(target: Target, opts: Options, canonical_url: str | None = None) -> TargetResult:
    assert target.path
    ctx = Context(target.name)
    with open(target.path, "rb") as fh:
        raw = fh.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        ctx.add("fetch", "securitytxt-too-large", Severity.ERROR, f"{target.path}: larger than {MAX_BYTES // 1024} KiB")
    else:
        check_content(ctx, raw, opts, source_url=canonical_url)
    return TargetResult(target.name, target.path, ctx.findings)


def check_target(target: Target, fetcher: Fetcher, opts: Options) -> TargetResult:
    try:
        return check_file(target, opts) if target.path else check_url(target, fetcher, opts)
    except Exception as exc:  # noqa: BLE001 - one broken target must not hide the rest
        ctx = Context(target.name)
        ctx.add("engine", "check-internal-error", Severity.ERROR, f"check crashed: {type(exc).__name__}: {exc}")
        return TargetResult(target.name, findings=ctx.findings)


@dataclass
class Report:
    results: list[TargetResult]
    fail_on: FailOn

    @property
    def findings(self) -> list[Finding]:
        return [f for r in self.results for f in r.findings]

    @property
    def failing(self) -> list[Finding]:
        return [f for f in self.findings if self.fail_on.matches(f)]

    @property
    def failed(self) -> bool:
        return bool(self.failing)

    @property
    def exit_code(self) -> int:
        return EXIT_FAILED if self.failed else EXIT_OK

    def counts(self) -> dict[str, int]:
        counts = {s.value: 0 for s in Severity}
        for f in self.findings:
            counts[f.severity.value] += 1
        return counts

    def to_dict(self) -> dict[str, object]:
        return {
            "tool": "security-txt-check",
            "version": __version__,
            "fail_on": self.fail_on.describe(),
            "failed": self.failed,
            "exit_code": self.exit_code,
            "counts": self.counts(),
            "targets": [
                {"target": r.target, "source": r.source, "findings": [f.to_dict() for f in r.findings]}
                for r in self.results
            ],
        }


def run(
    targets: list[Target],
    opts: Options | None = None,
    fail_on: FailOn | None = None,
    fetcher: Fetcher | None = None,
) -> Report:
    opts = opts or Options()
    results = [check_target(t, fetcher or fetch, opts) for t in targets]
    return Report(results, fail_on or FailOn())
