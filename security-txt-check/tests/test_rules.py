from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from security_txt_check.rules import Context, parse_fields, parse_rfc3339

from .conftest import VALID, check, ids


def test_valid_file_only_notes_missing_signature() -> None:
    ctx = check(VALID, source_url="https://example.com/.well-known/security.txt")
    assert ids(ctx) == ["securitytxt-not-signed"]


def test_crlf_bom_and_comments() -> None:
    text = "﻿# comment\r\n\r\n" + VALID.replace("\n", "\r\n")
    assert ids(check(text)) == ["securitytxt-not-signed"]


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("2026-12-31T23:59:59Z", datetime(2026, 12, 31, 23, 59, 59, tzinfo=timezone.utc)),
        ("2026-12-31t23:59:59z", datetime(2026, 12, 31, 23, 59, 59, tzinfo=timezone.utc)),
        ("2027-01-01T01:00:00+02:00", datetime(2026, 12, 31, 23, 0, tzinfo=timezone.utc)),
        ("2026-12-31T23:59:59.5-01:30", datetime(2027, 1, 1, 1, 29, 59, 500000, tzinfo=timezone.utc)),
        ("2026-12-31T23:59:60Z", datetime(2026, 12, 31, 23, 59, 59, tzinfo=timezone.utc)),
    ],
)
def test_rfc3339_valid(value: str, expected: datetime) -> None:
    assert parse_rfc3339(value) == expected


@pytest.mark.parametrize(
    "value",
    [
        "2026-12-31",
        "2026-12-31 23:59:59Z",
        "2026-12-31T23:59:59",
        "Thu, 31 Dec 2026 23:59:59 GMT",
        "2026-02-30T00:00:00Z",
    ],
)
def test_rfc3339_invalid(value: str) -> None:
    assert parse_rfc3339(value) is None


def _with_expires(value: str) -> str:
    return f"Contact: mailto:security@example.com\nExpires: {value}\n"


@pytest.mark.parametrize(
    ("expires", "fid", "fragment"),
    [
        ("2026-05-31T00:00:00Z", "securitytxt-expired", "1 day ago"),
        ("2026-06-01T00:00:00Z", "securitytxt-expired", "today"),
        ("2026-06-10T00:00:00Z", "securitytxt-expires-soon", "in 9 days"),
        ("2026-06-01T12:00:00Z", "securitytxt-expires-soon", "within a day"),
        ("2027-06-10T00:00:00Z", "securitytxt-expires-too-far", "374 days away"),
        ("31-12-2026", "securitytxt-expires-invalid", "not an RFC 3339"),
    ],
)
def test_expires(expires: str, fid: str, fragment: str) -> None:
    ctx = check(_with_expires(expires))
    found = [f for f in ctx.findings if f.check == "expires"]
    assert [f.id for f in found] == [fid]
    assert fragment in found[0].message


def test_expires_window_is_configurable() -> None:
    soon = (datetime(2026, 6, 1, tzinfo=timezone.utc) + timedelta(days=45)).strftime("%Y-%m-%dT%H:%M:%SZ")
    assert "securitytxt-expires-soon" not in ids(check(_with_expires(soon)))
    assert "securitytxt-expires-soon" in ids(check(_with_expires(soon), expires_warn_days=60))


def test_expires_missing_and_multiple() -> None:
    assert "securitytxt-expires-missing" in ids(check("Contact: mailto:a@example.com\n"))
    ctx = check(_with_expires("2026-12-01T00:00:00Z") + "Expires: 2026-12-02T00:00:00Z\n")
    assert "securitytxt-expires-multiple" in ids(ctx)


def test_contact_missing() -> None:
    assert "securitytxt-contact-missing" in ids(check("Expires: 2026-12-01T00:00:00Z\n"))


@pytest.mark.parametrize(
    ("line", "fid", "fragment"),
    [
        ("Contact: security@example.com", "securitytxt-invalid-uri", "mailto:"),
        ("Contact: http://example.com/security", "securitytxt-insecure-uri", "https://"),
        ("Contact: ftp://example.com/", "securitytxt-invalid-uri", "ftp:"),
        ("Contact: mailto:", "securitytxt-invalid-uri", "no address"),
        ("Policy: https:///nohost", "securitytxt-invalid-uri", "no host"),
        ("Encryption: mailto:keys@example.com", "securitytxt-invalid-uri", "openpgp4fpr:"),
        ("Hiring: https://example.com/jobs with space", "securitytxt-invalid-uri", "not a URI"),
    ],
)
def test_uri_fields(line: str, fid: str, fragment: str) -> None:
    ctx = check(_with_expires("2026-12-01T00:00:00Z") + line + "\n")
    hits = [f for f in ctx.findings if f.id == fid]
    assert hits, ids(ctx)
    assert fragment in hits[0].message


def test_other_contact_schemes_and_encryption_forms() -> None:
    text = _with_expires("2026-12-01T00:00:00Z") + (
        "Contact: tel:+45-12345678\n"
        "Encryption: openpgp4fpr:5F2DE5521C63A801AB59CCB603D49DE44B29100F\n"
        "Encryption: dns:5d2d37ab76d47d36._openpgpkey.example.com?type=OPENPGPKEY\n"
        "CSAF: https://example.com/.well-known/csaf/provider-metadata.json\n"
        "contact: MAILTO:other@example.com\n"
    )
    assert ids(check(text)) == ["securitytxt-not-signed"]


def test_unknown_field_with_spelling_hint() -> None:
    ctx = check(_with_expires("2026-12-01T00:00:00Z") + "Acknowledgements: https://example.com/thanks\nX-Foo: bar\n")
    msgs = [f.message for f in ctx.findings if f.id == "securitytxt-unknown-field"]
    assert len(msgs) == 2
    assert "did you mean Acknowledgments?" in msgs[0]


def test_preferred_languages() -> None:
    base = _with_expires("2026-12-01T00:00:00Z")
    assert "securitytxt-invalid-language" in ids(check(base + "Preferred-Languages: en, english please\n"))
    assert "securitytxt-field-repeated" in ids(check(base + "Preferred-Languages: en\nPreferred-Languages: da\n"))
    assert ids(check(base + "Preferred-Languages: en, zh-Hant-TW, de-CH-1996\n")) == ["securitytxt-not-signed"]


def test_canonical() -> None:
    url = "https://example.com/.well-known/security.txt"
    assert "securitytxt-canonical-mismatch" not in ids(check(VALID, source_url=url))
    assert "securitytxt-canonical-mismatch" not in ids(
        check(VALID, source_url="https://EXAMPLE.com/.well-known/security.txt")
    )
    assert "securitytxt-canonical-mismatch" in ids(
        check(VALID, source_url="https://www.example.com/.well-known/security.txt")
    )
    # Without a source URL (local file) there is nothing to compare.
    assert "securitytxt-canonical-mismatch" not in ids(check(VALID))


def test_syntax_errors_are_capped() -> None:
    ctx = Context("t")
    fields = parse_fields(ctx, "\n".join(["garbage line"] * 8 + ["Empty:", "Contact: mailto:a@b.example"]))
    errs = [f for f in ctx.findings if f.id == "securitytxt-syntax-error"]
    assert len(errs) == 6
    assert "4 more" in errs[-1].message
    assert [f.name for f in fields] == ["Contact"]


def test_invalid_utf8_is_reported_and_rest_checked() -> None:
    ctx = check(b"Contact: mailto:a@example.com\nExpires: 2026-12-01T00:00:00Z\n# caf\xe9\n")
    assert ids(ctx)[0] == "securitytxt-invalid-encoding"
    assert "securitytxt-contact-missing" not in ids(ctx)


def test_control_characters_and_length_are_sanitised() -> None:
    ctx = check("Contact: mailto:a@example.com\nExpires: \x1b[31m" + "x" * 400 + "\n")
    msg = next(
        f.message for f in ctx.findings if f.id == "securitytxt-syntax-error" or f.id == "securitytxt-expires-invalid"
    )
    assert "\x1b" not in msg
    assert len(msg) <= 300
