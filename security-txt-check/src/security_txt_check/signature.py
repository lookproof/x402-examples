"""OpenPGP cleartext signatures (RFC 9116 section 2.3, RFC 4880 section 7).

:func:`split_cleartext` checks the structure without any crypto: armor lines,
dash escaping, the base64 and CRC24 of the signature block and the hash
algorithm in the signature packet. :func:`gpg_verify` checks the signature
cryptographically with ``gpg`` against a public key you supply, in a throwaway
keyring, so your own keyring is never read or changed.
"""

from __future__ import annotations

import base64
import binascii
import os
import shutil
import subprocess
import tempfile
from collections.abc import Callable
from dataclasses import dataclass, field

BEGIN_SIGNED = "-----BEGIN PGP SIGNED MESSAGE-----"
BEGIN_SIGNATURE = "-----BEGIN PGP SIGNATURE-----"
END_SIGNATURE = "-----END PGP SIGNATURE-----"

# OpenPGP hash algorithm ids (RFC 9580 section 9.5).
HASH_NAMES = {
    1: "MD5",
    2: "SHA1",
    3: "RIPEMD160",
    8: "SHA256",
    9: "SHA384",
    10: "SHA512",
    11: "SHA224",
    12: "SHA3-256",
    14: "SHA3-512",
}
WEAK_HASHES = {"MD5", "SHA1", "RIPEMD160"}


class SignatureFormatError(ValueError):
    pass


@dataclass
class Cleartext:
    text: str
    """The signed text with dash escaping removed."""
    text_start_line: int
    """1-based line number in the file where the signed text starts."""
    hash_headers: list[str] = field(default_factory=list)
    packet_hash: str | None = None
    leading: bool = False
    """Non-blank content before the signed message."""
    trailing: bool = False
    """Non-blank content after the signature."""


def is_signed(text: str) -> bool:
    return any(line.rstrip("\r") == BEGIN_SIGNED for line in text.split("\n"))


def crc24(data: bytes) -> int:
    crc = 0xB704CE
    for byte in data:
        crc ^= byte << 16
        for _ in range(8):
            crc <<= 1
            if crc & 0x1000000:
                crc ^= 0x1864CFB
    return crc & 0xFFFFFF


def _packet_body(data: bytes) -> tuple[int, bytes]:
    """Return (tag, body) of the first OpenPGP packet."""
    if not data or not data[0] & 0x80:
        raise SignatureFormatError("signature block does not start with an OpenPGP packet")
    first = data[0]
    if first & 0x40:  # new format
        tag = first & 0x3F
        if len(data) < 2:
            raise SignatureFormatError("truncated OpenPGP packet")
        o = data[1]
        if o < 192:
            length, start = o, 2
        elif o < 224:
            if len(data) < 3:
                raise SignatureFormatError("truncated OpenPGP packet")
            length, start = ((o - 192) << 8) + data[2] + 192, 3
        elif o == 255:
            if len(data) < 6:
                raise SignatureFormatError("truncated OpenPGP packet")
            length, start = int.from_bytes(data[2:6], "big"), 6
        else:
            raise SignatureFormatError("partial-length signature packets are not allowed")
    else:  # old format
        tag = (first >> 2) & 0x0F
        ltype = first & 0x03
        if ltype == 3:
            raise SignatureFormatError("indeterminate-length signature packets are not allowed")
        size = (1, 2, 4)[ltype]
        if len(data) < 1 + size:
            raise SignatureFormatError("truncated OpenPGP packet")
        length, start = int.from_bytes(data[1 : 1 + size], "big"), 1 + size
    body = data[start : start + length]
    if len(body) < length:
        raise SignatureFormatError("truncated OpenPGP packet")
    return tag, body


def signature_hash(packet: bytes) -> str:
    """Name of the hash algorithm used by the first signature packet."""
    tag, body = _packet_body(packet)
    if tag != 2:
        raise SignatureFormatError(f"signature block holds an OpenPGP packet of type {tag}, not a signature")
    if not body:
        raise SignatureFormatError("empty signature packet")
    version = body[0]
    if version in (4, 5, 6):
        if len(body) < 4:
            raise SignatureFormatError("truncated signature packet")
        algo = body[3]
    elif version in (2, 3):
        if len(body) < 17:
            raise SignatureFormatError("truncated signature packet")
        algo = body[16]
    else:
        raise SignatureFormatError(f"unknown signature packet version {version}")
    return HASH_NAMES.get(algo, f"algorithm {algo}")


def _decode_armor(lines: list[str]) -> bytes:
    i = 0
    while i < len(lines) and lines[i].strip():
        if ":" not in lines[i]:
            raise SignatureFormatError(f"invalid armor header in signature block: {lines[i][:60]!r}")
        i += 1
    if i == len(lines):
        raise SignatureFormatError("signature block has no blank line after its armor headers")
    payload = [ln.strip() for ln in lines[i + 1 :] if ln.strip()]
    checksum = None
    if payload and payload[-1].startswith("=") and len(payload[-1]) == 5:
        checksum = payload.pop()[1:]
    if not payload:
        raise SignatureFormatError("signature block is empty")
    try:
        data = base64.b64decode("".join(payload), validate=True)
    except (binascii.Error, ValueError) as exc:
        raise SignatureFormatError("signature block is not valid base64") from exc
    if checksum is not None:
        try:
            expected = int.from_bytes(base64.b64decode(checksum, validate=True), "big")
        except (binascii.Error, ValueError) as exc:
            raise SignatureFormatError("armor checksum is not valid base64") from exc
        if crc24(data) != expected:
            raise SignatureFormatError("armor checksum (CRC24) does not match the signature data")
    return data


def split_cleartext(text: str) -> Cleartext:
    lines = [ln.rstrip("\r") for ln in text.split("\n")]
    try:
        begin = lines.index(BEGIN_SIGNED)
    except ValueError as exc:
        raise SignatureFormatError("no -----BEGIN PGP SIGNED MESSAGE----- line") from exc
    leading = any(ln.strip() for ln in lines[:begin])

    i = begin + 1
    hashes: list[str] = []
    while i < len(lines) and lines[i] != "":
        key, sep, value = lines[i].partition(":")
        if not sep:
            raise SignatureFormatError(f"invalid armor header after BEGIN PGP SIGNED MESSAGE: {lines[i][:60]!r}")
        if key.strip().lower() == "hash":
            hashes += [h.strip().upper() for h in value.split(",") if h.strip()]
        i += 1
    if i == len(lines):
        raise SignatureFormatError("no blank line after the armor headers")
    i += 1
    text_start = i

    body: list[str] = []
    while i < len(lines) and lines[i] != BEGIN_SIGNATURE:
        line = lines[i]
        if line.startswith("- "):
            line = line[2:]
        elif line.startswith("-"):
            raise SignatureFormatError(f"line {i + 1} starts with '-' but is not dash-escaped")
        body.append(line)
        i += 1
    if i == len(lines):
        raise SignatureFormatError("no -----BEGIN PGP SIGNATURE----- line")
    sig_start = i + 1
    try:
        end = lines.index(END_SIGNATURE, sig_start)
    except ValueError as exc:
        raise SignatureFormatError("no -----END PGP SIGNATURE----- line") from exc
    packet = _decode_armor(lines[sig_start:end])
    trailing = any(ln.strip() for ln in lines[end + 1 :])
    return Cleartext(
        text="\n".join(body),
        text_start_line=text_start + 1,
        hash_headers=hashes,
        packet_hash=signature_hash(packet),
        leading=leading,
        trailing=trailing,
    )


@dataclass
class VerifyResult:
    status: str
    """``good``, ``bad``, ``expired-key``, ``revoked-key`` or ``error``."""
    detail: str = ""


Verifier = Callable[[bytes, str], VerifyResult]


def _status(lines: list[str], keyword: str) -> list[str] | None:
    for line in lines:
        parts = line.split()
        if len(parts) >= 2 and parts[0] == "[GNUPG:]" and parts[1] == keyword:
            return parts[2:]
    return None


def gpg_verify(signed: bytes, key_path: str, gpg: str | None = None, timeout: float = 30.0) -> VerifyResult:
    """Verify a cleartext-signed file against the public key(s) in ``key_path``."""
    binary = gpg or shutil.which("gpg") or shutil.which("gpg2")
    if not binary:
        return VerifyResult("error", "gpg is not installed, so the signature could not be verified")
    if not os.path.isfile(key_path):
        return VerifyResult("error", f"signing key file not found: {key_path}")
    with tempfile.TemporaryDirectory(prefix="security-txt-check-") as home:
        os.chmod(home, 0o700)
        base = [binary, "--batch", "--no-tty", "--no-options", "--homedir", home]
        try:
            imported = subprocess.run(  # noqa: S603 - fixed argv, no shell
                [*base, "--status-fd", "1", "--import", key_path],
                capture_output=True,
                timeout=timeout,
                check=False,
            )
            if b"IMPORT_OK" not in imported.stdout:
                err = imported.stderr.decode("utf-8", "replace").strip().splitlines()
                return VerifyResult("error", "could not import the signing key: " + (err[-1] if err else "no key"))
            msg = os.path.join(home, "security.txt")
            with open(msg, "wb") as fh:
                fh.write(signed)
            res = subprocess.run(  # noqa: S603 - fixed argv, no shell
                [*base, "--status-fd", "1", "--verify", msg],
                capture_output=True,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return VerifyResult("error", "gpg timed out")
        except OSError as exc:
            return VerifyResult("error", f"could not run gpg: {exc}")
    out = res.stdout.decode("utf-8", "replace").splitlines()
    if (args := _status(out, "BADSIG")) is not None:
        return VerifyResult("bad", "the signature does not match the file (BADSIG)")
    if _status(out, "NO_PUBKEY") is not None or _status(out, "ERRSIG") is not None:
        return VerifyResult("bad", "the file is not signed by the given key")
    if (args := _status(out, "REVKEYSIG")) is not None:
        return VerifyResult("revoked-key", f"signed by revoked key {args[0] if args else ''}".strip())
    if (args := _status(out, "EXPKEYSIG")) is not None:
        return VerifyResult("expired-key", f"signed by expired key {args[0] if args else ''}".strip())
    if _status(out, "GOODSIG") is not None and (args := _status(out, "VALIDSIG")) is not None:
        return VerifyResult("good", f"good signature from key {args[0] if args else ''}".strip())
    if _status(out, "EXPSIG") is not None:
        return VerifyResult("bad", "the signature itself has expired")
    return VerifyResult("bad", "gpg did not report a good signature")
