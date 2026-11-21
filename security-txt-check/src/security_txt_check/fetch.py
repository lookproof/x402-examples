"""One strict HTTPS GET, without following redirects.

The certificate and host name are validated and the response size is capped.
Redirects are returned to the caller, which decides whether to follow them.
``HTTPS_PROXY`` / ``NO_PROXY`` are honoured so the tool works on self-hosted
runners behind a proxy.
"""

from __future__ import annotations

import base64
import http.client
import ssl
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass

from . import __version__

MAX_BYTES = 64 * 1024
USER_AGENT = f"security-txt-check/{__version__} (+https://lookproof.dev)"


@dataclass
class HttpResponse:
    status: int
    content_type: str
    body: bytes
    location: str | None = None


class FetchError(Exception):
    def __init__(self, message: str, tls: bool = False) -> None:
        super().__init__(message)
        self.tls = tls


Fetcher = Callable[[str], HttpResponse]


def _proxy_for(host: str) -> tuple[str, int, dict[str, str]] | None:
    proxy = urllib.request.getproxies().get("https")
    if not proxy or urllib.request.proxy_bypass(host):
        return None
    parsed = urllib.parse.urlsplit(proxy if "://" in proxy else "http://" + proxy)
    if not parsed.hostname:
        return None
    headers: dict[str, str] = {}
    if parsed.username:
        raw = f"{urllib.parse.unquote(parsed.username)}:{urllib.parse.unquote(parsed.password or '')}"
        headers["Proxy-Authorization"] = "Basic " + base64.b64encode(raw.encode()).decode()
    return parsed.hostname, parsed.port or 8080, headers


def fetch(url: str, timeout: float = 10.0) -> HttpResponse:
    parts = urllib.parse.urlsplit(url)
    if parts.scheme != "https" or not parts.hostname:
        raise FetchError(f"not an https URL: {url}")
    host, port = parts.hostname, parts.port or 443
    path = parts.path or "/"
    if parts.query:
        path += "?" + parts.query
    context = ssl.create_default_context()
    proxy = _proxy_for(host)
    if proxy:
        conn = http.client.HTTPSConnection(proxy[0], proxy[1], timeout=timeout, context=context)
        conn.set_tunnel(host, port, headers=proxy[2])
    else:
        conn = http.client.HTTPSConnection(host, port, timeout=timeout, context=context)
    try:
        conn.request("GET", path, headers={"User-Agent": USER_AGENT, "Accept": "text/plain"})
        resp = conn.getresponse()
        body = resp.read(MAX_BYTES + 1)
        return HttpResponse(
            status=resp.status,
            content_type=resp.getheader("Content-Type", "") or "",
            body=body,
            location=resp.getheader("Location"),
        )
    except ssl.SSLCertVerificationError as exc:
        detail = getattr(exc, "verify_message", None) or exc
        raise FetchError(f"TLS certificate validation failed: {detail}", tls=True) from exc
    except ssl.SSLError as exc:
        raise FetchError(f"TLS error: {getattr(exc, 'reason', None) or exc}", tls=True) from exc
    except TimeoutError as exc:
        raise FetchError("connection timed out") from exc
    except (OSError, http.client.HTTPException) as exc:
        raise FetchError(f"connection failed: {exc}") from exc
    finally:
        conn.close()
