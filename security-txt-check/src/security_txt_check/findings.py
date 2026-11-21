"""Finding model and the registry of every finding id this tool can emit."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

LOOKPROOF_FINDINGS = "https://lookproof.dev/findings/"
RFC9116 = "https://www.rfc-editor.org/rfc/rfc9116"


class Severity(str, Enum):
    ERROR = "error"
    WARN = "warn"
    INFO = "info"

    @property
    def rank(self) -> int:
        return {"info": 0, "warn": 1, "error": 2}[self.value]


def _rfc(section: str) -> str:
    return f"{RFC9116}#section-{section}"


def _lookproof(slug: str) -> str:
    return LOOKPROOF_FINDINGS + slug


# Finding id -> page that explains it. Lookproof pages are used where one
# exists (tests/test_links.py checks them against the live sitemap); the rest
# point at the section of RFC 9116 that the finding is about.
REGISTRY: dict[str, str] = {
    # Retrieval (RFC 9116 section 3)
    "securitytxt-not-found": _rfc("3"),
    "securitytxt-legacy-location": _rfc("3"),
    "securitytxt-fetch-failed": _lookproof("https-unavailable"),
    "securitytxt-tls-error": _lookproof("tls-untrusted"),
    "securitytxt-insecure-redirect": _rfc("3"),
    "securitytxt-redirect-offsite": _lookproof("redirect-offsite"),
    "securitytxt-too-many-redirects": _lookproof("redirect-limit"),
    "securitytxt-wrong-content-type": _rfc("3"),
    "securitytxt-no-charset": _rfc("3"),
    "securitytxt-too-large": _rfc("4"),
    # File format (sections 2 and 4)
    "securitytxt-invalid-encoding": _rfc("4"),
    "securitytxt-syntax-error": _rfc("4"),
    "securitytxt-unknown-field": _rfc("2.4"),
    "securitytxt-invalid-uri": _rfc("2.5"),
    "securitytxt-insecure-uri": _rfc("2.5"),
    "securitytxt-field-repeated": _rfc("2.5"),
    # Fields
    "securitytxt-contact-missing": _rfc("2.5.3"),
    "securitytxt-expires-missing": _rfc("2.5.5"),
    "securitytxt-expires-multiple": _rfc("2.5.5"),
    "securitytxt-expires-invalid": _rfc("2.5.5"),
    "securitytxt-expired": _rfc("2.5.5"),
    "securitytxt-expires-soon": _rfc("2.5.5"),
    "securitytxt-expires-too-far": _rfc("2.5.5"),
    "securitytxt-invalid-language": _rfc("2.5.8"),
    "securitytxt-canonical-mismatch": _rfc("2.5.2"),
    # Digital signature (section 2.3)
    "securitytxt-not-signed": _rfc("2.3"),
    "securitytxt-signed-no-canonical": _rfc("2.3"),
    "securitytxt-signature-malformed": _rfc("2.3"),
    "securitytxt-unsigned-content": _rfc("2.3"),
    "securitytxt-signature-weak-hash": _rfc("2.3"),
    "securitytxt-signature-invalid": _rfc("2.3"),
    "securitytxt-signature-key-expired": _rfc("2.3"),
    "securitytxt-signature-not-verified": _rfc("2.3"),
    "securitytxt-signature-check-failed": _rfc("2.3"),
    # Engine
    "check-internal-error": _lookproof("check-internal-error"),
}


@dataclass(frozen=True)
class Finding:
    id: str
    severity: Severity
    check: str
    message: str
    target: str

    def __post_init__(self) -> None:
        if self.id not in REGISTRY:
            raise ValueError(f"unregistered finding id: {self.id}")

    @property
    def url(self) -> str:
        return REGISTRY[self.id]

    def to_dict(self) -> dict[str, str]:
        return {
            "id": self.id,
            "severity": self.severity.value,
            "check": self.check,
            "target": self.target,
            "message": self.message,
            "url": self.url,
        }
