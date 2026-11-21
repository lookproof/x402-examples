from __future__ import annotations

import json
from pathlib import Path

import pytest

import security_txt_check.cli as cli
from security_txt_check import action, engine
from security_txt_check.github import ISSUE_MARKER, GitHubClient, GitHubError, sync_issue
from security_txt_check.report import LOOKPROOF_LINE

from .conftest import VALID, FakeFetcher, text_response

WK = "https://example.com/.well-known/security.txt"
EXPIRED = VALID.replace("2026-12-31T23:59:59Z", "2020-01-01T00:00:00Z")


@pytest.fixture
def site(monkeypatch, fetcher: FakeFetcher) -> FakeFetcher:
    """Route the default fetcher to the fake and serve a valid file at example.com."""
    fetcher.responses[WK] = text_response(VALID)
    monkeypatch.setattr(engine, "fetch", fetcher)
    monkeypatch.setattr(cli, "fetch", lambda url, timeout=10.0: fetcher(url))
    return fetcher


# CLI


def test_cli_json_pass(site, capsys) -> None:
    code = cli.main(["example.com", "--json"])
    out = json.loads(capsys.readouterr().out)
    assert code == 0
    assert out["failed"] is False
    assert out["targets"][0]["source"] == WK


def test_cli_text_fail_and_file(site, tmp_path, capsys) -> None:
    path = tmp_path / "security.txt"
    path.write_text(EXPIRED)
    code = cli.main(["--file", str(path), "--expires-warn-days", "10"])
    out = capsys.readouterr().out
    assert code == 1
    assert "securitytxt-expired *" in out


def test_cli_fail_on_ids(site) -> None:
    assert cli.main(["example.com", "--fail-on", "error,securitytxt-not-signed"]) == 1
    assert cli.main(["example.com", "--fail-on", "none"]) == 0


def test_cli_usage_errors(site, tmp_path, capsys) -> None:
    assert cli.main([]) == 2
    assert cli.main(["not a domain"]) == 2
    assert cli.main(["http://example.com/.well-known/security.txt"]) == 2
    assert cli.main(["example.com", "--fail-on", "bogus"]) == 2
    assert cli.main(["--file", str(tmp_path / "missing.txt")]) == 2
    assert cli.main(["example.com", "--signing-key", str(tmp_path / "missing.asc")]) == 2
    assert cli.main(["example.com", "--expires-warn-days", "-1"]) == 2
    assert "bogus" in capsys.readouterr().err


# Action


def _env(tmp_path: Path, **extra: str) -> dict[str, str]:
    env = {
        "GITHUB_STEP_SUMMARY": str(tmp_path / "summary.md"),
        "GITHUB_OUTPUT": str(tmp_path / "output"),
        "SECURITY_TXT_CHECK_DOMAINS": "example.com",
        "SECURITY_TXT_CHECK_FAIL_ON": "error",
    }
    env.update(extra)
    return env


def _outputs(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    lines = path.read_text().splitlines()
    i = 0
    while i < len(lines):
        name, _, delim = lines[i].partition("<<")
        end = lines.index(delim, i + 1)
        out[name] = "\n".join(lines[i + 1 : end])
        i = end + 1
    return out


def test_action_pass(tmp_path, site, capsys) -> None:
    code = action.main(_env(tmp_path), fetcher=site)
    assert code == 0
    summary = (tmp_path / "summary.md").read_text()
    assert summary.strip().splitlines()[-1] == LOOKPROOF_LINE
    outputs = _outputs(tmp_path / "output")
    assert outputs["exit-code"] == "0"
    assert json.loads(outputs["json"])["targets"][0]["target"] == "example.com"
    assert "::error" not in capsys.readouterr().out


def test_action_files_and_annotations(tmp_path, site, capsys) -> None:
    path = tmp_path / "security.txt"
    path.write_text(EXPIRED)
    env = _env(tmp_path, SECURITY_TXT_CHECK_DOMAINS="", SECURITY_TXT_CHECK_FILES=str(path))
    code = action.main(env, fetcher=site)
    out = capsys.readouterr().out
    assert code == 1
    assert out.count("::error title=security-txt-check securitytxt-expired") == 1
    assert _outputs(tmp_path / "output")["exit-code"] == "1"
    assert site.calls == []


def test_action_signing_key_and_verifier(tmp_path, site) -> None:
    key = tmp_path / "key.asc"
    key.write_text("key")
    seen = []

    def verifier(raw, key_path):
        from security_txt_check.signature import VerifyResult

        seen.append(key_path)
        return VerifyResult("bad", "nope")

    from .test_signature import _signed

    site.responses[WK] = text_response(_signed(VALID))
    env = _env(tmp_path, SECURITY_TXT_CHECK_SIGNING_KEY=str(key))
    assert action.main(env, fetcher=site, verifier=verifier) == 1
    assert seen == [str(key)]


def test_action_usage_errors(tmp_path, site, capsys) -> None:
    assert action.main(_env(tmp_path, SECURITY_TXT_CHECK_DOMAINS=" "), fetcher=site) == 2
    assert action.main(_env(tmp_path, SECURITY_TXT_CHECK_FAIL_ON="nope"), fetcher=site) == 2
    assert action.main(_env(tmp_path, SECURITY_TXT_CHECK_EXPIRES_WARN_DAYS="soon"), fetcher=site) == 2
    assert action.main(_env(tmp_path, SECURITY_TXT_CHECK_SIGNING_KEY="/nope.asc"), fetcher=site) == 2
    assert "::error title=security-txt-check::" in capsys.readouterr().out


class FakeGitHub(GitHubClient):
    def __init__(self, issues: list[dict[str, object]] | None = None) -> None:
        super().__init__("token", "lookproof/test")
        self.issues = issues or []
        self.calls: list[tuple[str, str, dict[str, object] | None]] = []

    def request(self, method, path, body=None):
        self.calls.append((method, path, body))
        if method == "GET":
            return self.issues if path.endswith("&page=1") else []
        if method == "POST" and path == "/issues":
            return {"number": 7}
        return {}


def test_action_creates_issue(tmp_path, site, capsys) -> None:
    site.responses[WK] = text_response(EXPIRED)
    gh = FakeGitHub()
    env = _env(tmp_path, SECURITY_TXT_CHECK_CREATE_ISSUE="true", GITHUB_RUN_ID="42")
    code = action.main(env, fetcher=site, client=gh)
    assert code == 1
    method, path, body = gh.calls[-1]
    assert (method, path) == ("POST", "/issues")
    assert body is not None
    assert body["title"] == action.DEFAULT_ISSUE_TITLE
    text = str(body["body"])
    assert ISSUE_MARKER in text
    assert "securitytxt-expired" in text
    assert "actions/runs/42" in text
    assert LOOKPROOF_LINE not in text
    assert "Opened issue #7" in capsys.readouterr().out


def test_action_issue_error_fails_step(tmp_path, site) -> None:
    env = _env(tmp_path, SECURITY_TXT_CHECK_CREATE_ISSUE="true", SECURITY_TXT_CHECK_GITHUB_TOKEN="")
    assert action.main(env, fetcher=site) == 1


def test_sync_issue_updates_existing() -> None:
    gh = FakeGitHub([{"number": 3, "title": "T"}, {"number": 4, "title": "T", "pull_request": {}}])
    assert sync_issue(gh, "T", True, "body") == "Updated issue #3"
    assert gh.calls[-1][0:2] == ("PATCH", "/issues/3")


def test_sync_issue_closes_when_green() -> None:
    gh = FakeGitHub([{"number": 3, "title": "T"}])
    assert sync_issue(gh, "T", False, "body") == "Closed issue #3"
    assert gh.calls[-2][0:2] == ("POST", "/issues/3/comments")
    method, path, body = gh.calls[-1]
    assert (method, path) == ("PATCH", "/issues/3")
    assert body is not None and body["state"] == "closed"


def test_sync_issue_noop_when_green_and_none_open() -> None:
    gh = FakeGitHub()
    assert sync_issue(gh, "T", False, "body") == "No open issue and nothing failing"
    assert [c[0] for c in gh.calls] == ["GET"]


def test_github_client_validation() -> None:
    with pytest.raises(GitHubError):
        GitHubClient("", "a/b")
    with pytest.raises(GitHubError):
        GitHubClient("t", "nope")
    with pytest.raises(GitHubError):
        GitHubClient("t", "a/b", "file:///etc/passwd")


def test_github_client_request(monkeypatch) -> None:
    import io
    import urllib.error
    import urllib.request

    captured = {}

    class Resp(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def fake_urlopen(req, timeout):
        captured["url"] = req.full_url
        captured["auth"] = req.get_header("Authorization")
        return Resp(b'{"number": 1}')

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    gh = GitHubClient("tok", "o/r", "https://ghe.example/api/v3/")
    assert gh.request("POST", "/issues", {"title": "x"}) == {"number": 1}
    assert captured["url"] == "https://ghe.example/api/v3/repos/o/r/issues"
    assert captured["auth"] == "Bearer tok"

    def http_error(req, timeout):
        raise urllib.error.HTTPError(req.full_url, 403, "Forbidden", {}, io.BytesIO(b"denied"))  # type: ignore[arg-type]

    monkeypatch.setattr(urllib.request, "urlopen", http_error)
    with pytest.raises(GitHubError, match="issues: write"):
        gh.request("GET", "/issues")

    def url_error(req, timeout):
        raise urllib.error.URLError("offline")

    monkeypatch.setattr(urllib.request, "urlopen", url_error)
    with pytest.raises(GitHubError, match="offline"):
        gh.request("GET", "/issues")
