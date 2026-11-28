from __future__ import annotations

import os
import shutil
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pytest

from security_txt_check.fetch import FetchError, HttpResponse
from security_txt_check.rules import Context, Options, check_content

NOW = datetime(2026, 6, 1, tzinfo=timezone.utc)

VALID = """\
# Our security policy
Contact: mailto:security@example.com
Contact: https://example.com/security
Expires: 2026-12-31T23:59:59Z
Encryption: https://example.com/pgp-key.txt
Preferred-Languages: en, da
Canonical: https://example.com/.well-known/security.txt
Policy: https://example.com/disclosure
"""


def opts(**kw: object) -> Options:
    kw.setdefault("now", NOW)
    return Options(**kw)  # type: ignore[arg-type]


def check(text: str | bytes, source_url: str | None = None, **kw: object) -> Context:
    ctx = Context("example.com")
    raw = text.encode() if isinstance(text, str) else text
    check_content(ctx, raw, opts(**kw), source_url=source_url)
    return ctx


def ids(ctx: Context) -> list[str]:
    return [f.id for f in ctx.findings]


def text_response(
    body: str | bytes, status: int = 200, content_type: str = "text/plain; charset=utf-8"
) -> HttpResponse:
    return HttpResponse(status, content_type, body.encode() if isinstance(body, str) else body)


def redirect(location: str, status: int = 301) -> HttpResponse:
    return HttpResponse(status, "text/html", b"", location)


class FakeFetcher:
    """URL -> response. Unknown URLs are 404."""

    def __init__(self) -> None:
        self.responses: dict[str, HttpResponse | FetchError] = {}
        self.calls: list[str] = []

    def __call__(self, url: str) -> HttpResponse:
        self.calls.append(url)
        resp = self.responses.get(url, HttpResponse(404, "text/plain", b"not found"))
        if isinstance(resp, FetchError):
            raise resp
        return resp


@pytest.fixture
def fetcher() -> FakeFetcher:
    return FakeFetcher()


@dataclass
class Gpg:
    home: Path
    key_path: Path
    other_key_path: Path

    def sign(self, text: str, digest: str = "SHA256") -> str:
        res = subprocess.run(
            [
                "gpg",
                "--batch",
                "--homedir",
                str(self.home),
                "--pinentry-mode",
                "loopback",
                "--passphrase",
                "",
                "--local-user",
                "signer@example.com",
                "--digest-algo",
                digest,
                "--clearsign",
            ],
            input=text.encode(),
            capture_output=True,
            check=True,
        )
        return res.stdout.decode()


def _gen_key(home: Path, uid: str) -> None:
    subprocess.run(
        [
            "gpg",
            "--batch",
            "--homedir",
            str(home),
            "--pinentry-mode",
            "loopback",
            "--passphrase",
            "",
            "--quick-gen-key",
            uid,
            "ed25519",
            "sign",
            "never",
        ],
        capture_output=True,
        check=True,
    )


@pytest.fixture(scope="session")
def gpg(tmp_path_factory: pytest.TempPathFactory) -> Gpg:
    if not shutil.which("gpg"):
        pytest.skip("gpg is not installed")
    home = tmp_path_factory.mktemp("gnupg")
    os.chmod(home, 0o700)
    _gen_key(home, "signer@example.com")
    _gen_key(home, "other@example.com")
    paths = []
    for uid in ("signer@example.com", "other@example.com"):
        out = subprocess.run(
            ["gpg", "--batch", "--homedir", str(home), "--armor", "--export", uid],
            capture_output=True,
            check=True,
        ).stdout
        path = home / f"{uid}.asc"
        path.write_bytes(out)
        paths.append(path)
    return Gpg(home, paths[0], paths[1])


MakeCheck = Callable[..., Context]
