from __future__ import annotations

import json

import pytest

from security_txt_check import engine
from security_txt_check.engine import (
    FailOn,
    Target,
    UsageError,
    parse_fail_on,
    parse_list,
    parse_target,
    run,
)
from security_txt_check.fetch import MAX_BYTES, FetchError, HttpResponse
from security_txt_check.findings import LOOKPROOF_FINDINGS, REGISTRY, RFC9116, Finding, Severity
from security_txt_check.report import LOOKPROOF_LINE, to_json, to_markdown, to_text

from .conftest import VALID, FakeFetcher, opts, redirect, text_response

WK = "https://example.com/.well-known/security.txt"


def _run(fetcher: FakeFetcher, target: str = "example.com", **kw: object):
    report = run([parse_target(target)], opts(**kw), fetcher=fetcher)
    return report, [f.id for f in report.results[0].findings]


def test_ok(fetcher: FakeFetcher) -> None:
    fetcher.responses[WK] = text_response(VALID)
    report, found = _run(fetcher)
    assert found == ["securitytxt-not-signed"]
    assert report.results[0].source == WK
    assert report.exit_code == 0


def test_legacy_location(fetcher: FakeFetcher) -> None:
    fetcher.responses["https://example.com/security.txt"] = text_response(VALID)
    _, found = _run(fetcher)
    assert found[0] == "securitytxt-legacy-location"
    assert "securitytxt-canonical-mismatch" in found


@pytest.mark.parametrize(
    "missing",
    [
        HttpResponse(404, "text/html", b"<html>nope</html>"),
        HttpResponse(410, "text/plain", b""),
        HttpResponse(200, "text/html; charset=utf-8", b"\n  <!DOCTYPE html><html><body>app</body></html>"),
    ],
)
def test_not_found(fetcher: FakeFetcher, missing: HttpResponse) -> None:
    fetcher.responses[WK] = missing
    fetcher.responses["https://example.com/security.txt"] = missing
    report, found = _run(fetcher)
    assert found == ["securitytxt-not-found"]
    assert report.exit_code == 1


def test_legacy_location_must_be_text(fetcher: FakeFetcher) -> None:
    fetcher.responses["https://example.com/security.txt"] = text_response(
        '{"_id": "security.txt"}', content_type="application/json"
    )
    _, found = _run(fetcher)
    assert found == ["securitytxt-not-found"]


def test_explicit_url_has_no_legacy_fallback(fetcher: FakeFetcher) -> None:
    _, found = _run(fetcher, "https://example.com/custom/security.txt")
    assert found == ["securitytxt-not-found"]
    assert fetcher.calls == ["https://example.com/custom/security.txt"]


def test_redirects(fetcher: FakeFetcher) -> None:
    fetcher.responses[WK] = redirect("https://www.example.com/.well-known/security.txt")
    fetcher.responses["https://www.example.com/.well-known/security.txt"] = redirect("/sec.txt", 302)
    fetcher.responses["https://www.example.com/sec.txt"] = text_response(VALID)
    report, found = _run(fetcher)
    assert "securitytxt-redirect-offsite" not in found
    assert report.results[0].source == "https://www.example.com/sec.txt"
    assert "securitytxt-canonical-mismatch" in found


def test_redirect_offsite_and_insecure(fetcher: FakeFetcher) -> None:
    fetcher.responses[WK] = redirect("https://security.example.net/example.txt")
    fetcher.responses["https://security.example.net/example.txt"] = redirect("http://security.example.net/x")
    _, found = _run(fetcher)
    assert found == ["securitytxt-redirect-offsite", "securitytxt-insecure-redirect"]


def test_redirect_loop_and_missing_location(fetcher: FakeFetcher) -> None:
    fetcher.responses[WK] = redirect(WK)
    _, found = _run(fetcher)
    assert found == ["securitytxt-too-many-redirects"]
    fetcher.responses[WK] = HttpResponse(302, "text/html", b"")
    _, found = _run(fetcher)
    assert found == ["securitytxt-fetch-failed"]


@pytest.mark.parametrize(
    ("resp", "expected"),
    [
        (text_response(VALID, content_type="text/plain"), "securitytxt-no-charset"),
        (text_response(VALID, content_type="text/plain; charset=ISO-8859-1"), "securitytxt-no-charset"),
        (text_response(VALID, content_type="application/octet-stream"), "securitytxt-wrong-content-type"),
        (text_response(VALID, content_type=""), "securitytxt-wrong-content-type"),
        (text_response("x" * (MAX_BYTES + 1)), "securitytxt-too-large"),
        (text_response("err", status=500), "securitytxt-fetch-failed"),
    ],
)
def test_response_checks(fetcher: FakeFetcher, resp: HttpResponse, expected: str) -> None:
    fetcher.responses[WK] = resp
    _, found = _run(fetcher)
    assert found[0] == expected


def test_wrong_type_still_parses_text(fetcher: FakeFetcher) -> None:
    fetcher.responses[WK] = text_response(VALID, content_type="application/octet-stream")
    _, found = _run(fetcher)
    assert found == ["securitytxt-wrong-content-type", "securitytxt-not-signed"]


def test_charset_quoted_is_fine(fetcher: FakeFetcher) -> None:
    fetcher.responses[WK] = text_response(VALID, content_type='text/plain; charset="UTF-8"')
    _, found = _run(fetcher)
    assert found == ["securitytxt-not-signed"]


def test_fetch_errors(fetcher: FakeFetcher) -> None:
    fetcher.responses[WK] = FetchError("TLS certificate validation failed: expired", tls=True)
    _, found = _run(fetcher)
    assert found == ["securitytxt-tls-error"]
    fetcher.responses[WK] = FetchError("connection timed out")
    _, found = _run(fetcher)
    assert found == ["securitytxt-fetch-failed"]


def test_internal_error_is_contained(fetcher: FakeFetcher, monkeypatch) -> None:
    def boom(*a: object, **k: object) -> None:
        raise KeyError("x")

    monkeypatch.setattr(engine, "check_content", boom)
    fetcher.responses[WK] = text_response(VALID)
    report = run([parse_target("example.com"), parse_target("example.org")], opts(), fetcher=fetcher)
    assert [f.id for f in report.results[0].findings] == ["check-internal-error"]
    assert [f.id for f in report.results[1].findings] == ["securitytxt-not-found"]


def test_local_file(tmp_path) -> None:
    path = tmp_path / "security.txt"
    path.write_text(VALID)
    report = run([Target(str(path), path=str(path))], opts())
    assert [f.id for f in report.findings] == ["securitytxt-not-signed"]
    path.write_bytes(b"x" * (MAX_BYTES + 1))
    report = run([Target(str(path), path=str(path))], opts())
    assert [f.id for f in report.findings] == ["securitytxt-too-large"]


def test_parse_target() -> None:
    assert parse_target("Example.COM.").url == WK
    assert parse_target("bücher.example").url == "https://xn--bcher-kva.example/.well-known/security.txt"
    assert parse_target("https://example.com/x.txt").url == "https://example.com/x.txt"
    for bad in ("http://example.com/", "https://", "localhost", "a@b.example", "a..b", "x" * 64 + ".com"):
        with pytest.raises(UsageError):
            parse_target(bad)


def test_parse_fail_on_and_list() -> None:
    assert parse_fail_on("") == FailOn()
    assert parse_fail_on("none").threshold is None
    f = parse_fail_on("warn, error, securitytxt-not-signed")
    assert f.threshold == Severity.WARN
    assert f.ids == {"securitytxt-not-signed"}
    assert f.describe() == "warn,securitytxt-not-signed"
    assert parse_fail_on("securitytxt-expires-soon").describe() == "securitytxt-expires-soon"
    with pytest.raises(UsageError):
        parse_fail_on("bogus")
    assert parse_list(["a.com, b.com", "a.com\nc.com d.com"]) == ["a.com", "b.com", "c.com", "d.com"]


def test_fail_on_ids_match_regardless_of_severity(fetcher: FakeFetcher) -> None:
    fetcher.responses[WK] = text_response(VALID)
    report = run([parse_target("example.com")], opts(), parse_fail_on("securitytxt-not-signed"), fetcher)
    assert report.failed


def test_reports(fetcher: FakeFetcher) -> None:
    fetcher.responses[WK] = text_response(VALID.replace("mailto:security@example.com", "security@example.com"))
    report = run([parse_target("example.com"), parse_target("example.org")], opts(), fetcher=fetcher)
    text = to_text(report)
    assert "securitytxt-invalid-uri *" in text
    assert "FAILED (fail-on: error): 2 errors" in text
    md = to_markdown(report)
    assert "**error** | [`securitytxt-invalid-uri`]" in md
    assert md.rstrip().endswith(LOOKPROOF_LINE)
    assert LOOKPROOF_LINE not in to_markdown(report, footer=False)
    data = json.loads(to_json(report))
    assert data["tool"] == "security-txt-check"
    assert data["targets"][0]["source"] == WK
    assert data["counts"] == {"error": 2, "warn": 0, "info": 1}


def test_markdown_neutralises_content() -> None:
    from security_txt_check.engine import Report, TargetResult

    f = Finding("securitytxt-syntax-error", Severity.ERROR, "format", "[x](https://evil) @here <b>|", "t")
    md = to_markdown(Report([TargetResult("t", findings=[f])], FailOn()))
    assert "\\[x\\](https:&#47;&#47;evil) &#64;here &lt;b&gt;\\|" in md


def test_registry_urls() -> None:
    for fid, url in REGISTRY.items():
        assert url.startswith((LOOKPROOF_FINDINGS, RFC9116 + "#section-")), fid
    with pytest.raises(ValueError, match="unregistered"):
        Finding("nope", Severity.INFO, "x", "y", "z")


def test_sample_file_is_valid() -> None:
    from pathlib import Path

    path = str(Path(__file__).parent / "data" / "security.txt")
    report = run([Target(path, path=path)], opts())
    assert [f.id for f in report.findings] == ["securitytxt-not-signed"]
