"""The HTTPS adapter, with the network replaced by fakes."""

from __future__ import annotations

import http.client
import ssl
from typing import ClassVar

import pytest

from security_txt_check.fetch import MAX_BYTES, FetchError, fetch


class FakeResponse:
    status = 200

    def __init__(self, body: bytes, headers: dict[str, str]) -> None:
        self.body = body
        self.headers = headers

    def read(self, n: int) -> bytes:
        return self.body[:n]

    def getheader(self, name: str, default: str | None = None) -> str | None:
        return self.headers.get(name, default)


class FakeConn:
    instances: ClassVar[list[FakeConn]] = []
    error: ClassVar[BaseException | None] = None

    def __init__(self, host: str, port: int, timeout: float, context: ssl.SSLContext) -> None:
        self.host, self.port, self.timeout = host, port, timeout
        self.tunnel: tuple[str, int, dict[str, str]] | None = None
        self.requests: list[tuple[str, str, dict[str, str]]] = []
        self.closed = False
        FakeConn.instances.append(self)

    def set_tunnel(self, host: str, port: int, headers: dict[str, str]) -> None:
        self.tunnel = (host, port, headers)

    def request(self, method: str, path: str, headers: dict[str, str]) -> None:
        if FakeConn.error:
            raise FakeConn.error
        self.requests.append((method, path, headers))

    def getresponse(self) -> FakeResponse:
        return FakeResponse(b"x" * (MAX_BYTES + 10), {"Content-Type": "text/plain"})

    def close(self) -> None:
        self.closed = True


@pytest.fixture(autouse=True)
def fake_conn(monkeypatch):
    FakeConn.instances = []
    FakeConn.error = None
    monkeypatch.setattr(http.client, "HTTPSConnection", FakeConn)
    for var in ("https_proxy", "HTTPS_PROXY", "no_proxy", "NO_PROXY"):
        monkeypatch.delenv(var, raising=False)


def test_direct_request_caps_body() -> None:
    resp = fetch("https://example.com:8443/.well-known/security.txt?x=1", timeout=3)
    conn = FakeConn.instances[0]
    assert (conn.host, conn.port, conn.timeout) == ("example.com", 8443, 3)
    assert conn.requests[0][1] == "/.well-known/security.txt?x=1"
    assert "security-txt-check" in conn.requests[0][2]["User-Agent"]
    assert len(resp.body) == MAX_BYTES + 1
    assert conn.closed


def test_proxy_with_credentials(monkeypatch) -> None:
    monkeypatch.setenv("HTTPS_PROXY", "http://user:p%40ss@proxy.local:3128")
    fetch("https://example.com/.well-known/security.txt")
    conn = FakeConn.instances[0]
    assert (conn.host, conn.port) == ("proxy.local", 3128)
    assert conn.tunnel is not None
    assert conn.tunnel[:2] == ("example.com", 443)
    assert conn.tunnel[2]["Proxy-Authorization"] == "Basic dXNlcjpwQHNz"


def test_no_proxy(monkeypatch) -> None:
    monkeypatch.setenv("HTTPS_PROXY", "proxy.local:3128")
    monkeypatch.setenv("NO_PROXY", "example.com")
    fetch("https://example.com/")
    assert FakeConn.instances[0].tunnel is None


def test_rejects_non_https() -> None:
    with pytest.raises(FetchError, match="not an https URL"):
        fetch("http://example.com/")


@pytest.mark.parametrize(
    ("error", "message", "tls"),
    [
        (ssl.SSLCertVerificationError("bad cert"), "certificate validation failed", True),
        (ssl.SSLError("handshake"), "TLS error", True),
        (TimeoutError(), "timed out", False),
        (ConnectionRefusedError("refused"), "connection failed", False),
    ],
)
def test_errors(error: BaseException, message: str, tls: bool) -> None:
    FakeConn.error = error
    with pytest.raises(FetchError, match=message) as info:
        fetch("https://example.com/")
    assert info.value.tls is tls
