from __future__ import annotations

import base64
import shutil

import pytest

from security_txt_check.signature import (
    SignatureFormatError,
    VerifyResult,
    crc24,
    gpg_verify,
    signature_hash,
    split_cleartext,
)

from .conftest import VALID, Gpg, check, ids


def test_crc24_known_values() -> None:
    assert crc24(b"") == 0xB704CE
    # Cross-checked against gpg's own armor output in test_gpg_armor_roundtrip.
    assert crc24(b"\x00") != crc24(b"\x01")


def _armor(packet: bytes, crc: int | None = None, headers: str = "") -> str:
    b64 = base64.b64encode(packet).decode()
    crc_line = "=" + base64.b64encode((crc if crc is not None else crc24(packet)).to_bytes(3, "big")).decode()
    return f"-----BEGIN PGP SIGNATURE-----\n{headers}\n{b64}\n{crc_line}\n-----END PGP SIGNATURE-----\n"


def _sig_packet(hash_algo: int = 8, version: int = 4) -> bytes:
    body = bytes([version, 0x01, 22, hash_algo]) + b"\x00" * 10
    return bytes([0xC2, len(body)]) + body  # new-format packet, tag 2


def _signed(body: str, packet: bytes | None = None, hash_header: str = "Hash: SHA256", **kw: object) -> str:
    return f"-----BEGIN PGP SIGNED MESSAGE-----\n{hash_header}\n\n{body}" + _armor(packet or _sig_packet(), **kw)  # type: ignore[arg-type]


def test_split_cleartext_structure() -> None:
    clear = split_cleartext(_signed("Contact: mailto:a@example.com\n- -leading dash\n"))
    assert clear.text == "Contact: mailto:a@example.com\n-leading dash"  # last line break belongs to the armor
    assert clear.hash_headers == ["SHA256"]
    assert clear.packet_hash == "SHA256"
    assert clear.text_start_line == 4
    assert not clear.leading and not clear.trailing


def test_signature_hash_formats() -> None:
    assert signature_hash(_sig_packet(2)) == "SHA1"
    assert signature_hash(_sig_packet(10, version=6)) == "SHA512"
    v3 = bytes([3, 5, 0x01]) + b"\x00" * 12 + bytes([1, 1]) + b"\x00" * 4
    assert signature_hash(bytes([0x88, len(v3)]) + v3) == "MD5"  # old format, tag 2, 1-byte length
    assert signature_hash(_sig_packet(99)) == "algorithm 99"
    long_body = bytes([4, 1, 22, 8]) + b"\x00" * 300
    n = len(long_body) - 192
    assert signature_hash(bytes([0xC2, (n >> 8) + 192, n & 0xFF]) + long_body) == "SHA256"
    assert signature_hash(bytes([0xC2, 255]) + len(long_body).to_bytes(4, "big") + long_body) == "SHA256"


@pytest.mark.parametrize(
    ("packet", "message"),
    [
        (b"\x00abc", "does not start with an OpenPGP packet"),
        (bytes([0xC6, 3, 1, 2, 3]), "type 6, not a signature"),
        (bytes([0xC2, 10, 4]), "truncated"),
        (bytes([0xC2, 230]), "partial-length"),
        (bytes([0x8B]), "indeterminate-length"),
        (bytes([0xC2, 2, 9, 9]), "unknown signature packet version"),
        (bytes([0xC2, 0]), "empty signature packet"),
    ],
)
def test_bad_packets(packet: bytes, message: str) -> None:
    with pytest.raises(SignatureFormatError, match=message):
        signature_hash(packet)


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("no signature here", "no -----BEGIN PGP SIGNED MESSAGE"),
        ("-----BEGIN PGP SIGNED MESSAGE-----\nHash: SHA256\nContact: x", "no blank line"),
        ("-----BEGIN PGP SIGNED MESSAGE-----\nbogus header\n\nx\n", "invalid armor header"),
        ("-----BEGIN PGP SIGNED MESSAGE-----\n\nContact: x\n", "no -----BEGIN PGP SIGNATURE"),
        ("-----BEGIN PGP SIGNED MESSAGE-----\n\n-oops\n-----BEGIN PGP SIGNATURE-----\n", "not dash-escaped"),
        ("-----BEGIN PGP SIGNED MESSAGE-----\n\nx\n-----BEGIN PGP SIGNATURE-----\n\nAAAA\n", "no -----END"),
    ],
)
def test_malformed_cleartext(text: str, message: str) -> None:
    with pytest.raises(SignatureFormatError, match=message):
        split_cleartext(text)


def test_bad_crc_and_base64() -> None:
    with pytest.raises(SignatureFormatError, match="CRC24"):
        split_cleartext(_signed("x\n", crc=123))
    bad = (
        "-----BEGIN PGP SIGNED MESSAGE-----\n\nx\n-----BEGIN PGP SIGNATURE-----\n\n!!!!\n-----END PGP SIGNATURE-----\n"
    )
    with pytest.raises(SignatureFormatError, match="base64"):
        split_cleartext(bad)
    no_blank = (
        "-----BEGIN PGP SIGNED MESSAGE-----\n\nx\n-----BEGIN PGP SIGNATURE-----\nAAAA\n-----END PGP SIGNATURE-----\n"
    )
    with pytest.raises(SignatureFormatError, match="armor header"):
        split_cleartext(no_blank)


def _ok_verifier(raw: bytes, key: str) -> VerifyResult:
    return VerifyResult("good", "ok")


def test_signed_file_checks_fields_in_signed_part() -> None:
    ctx = check(_signed(VALID), signing_key="key.asc", verifier=_ok_verifier)
    assert ids(ctx) == []


def test_signed_without_key_and_without_canonical() -> None:
    body = "Contact: mailto:a@example.com\nExpires: 2026-12-01T00:00:00Z\n"
    assert ids(check(_signed(body))) == ["securitytxt-signature-not-verified", "securitytxt-signed-no-canonical"]


def test_unsigned_content_and_weak_hash() -> None:
    signed = _signed(VALID, packet=_sig_packet(2), hash_header="Hash: SHA1")
    ctx = check("Contact: mailto:evil@example.net\n" + signed + "Contact: mailto:evil2@example.net\n")
    assert "securitytxt-unsigned-content" in ids(ctx)
    assert "securitytxt-signature-weak-hash" in ids(ctx)
    # Only the signed part counts: no syntax errors and no extra contacts were parsed.
    assert "securitytxt-syntax-error" not in ids(ctx)


def test_malformed_signature_still_checks_fields() -> None:
    text = "-----BEGIN PGP SIGNED MESSAGE-----\nHash: SHA256\n\n" + VALID + "-----BEGIN PGP SIGNATURE-----\n"
    ctx = check(text)
    assert ids(ctx) == ["securitytxt-signature-malformed"]
    assert "securitytxt-contact-missing" not in ids(ctx)


@pytest.mark.parametrize(
    ("status", "fid"),
    [
        ("bad", "securitytxt-signature-invalid"),
        ("revoked-key", "securitytxt-signature-invalid"),
        ("expired-key", "securitytxt-signature-key-expired"),
        ("error", "securitytxt-signature-check-failed"),
    ],
)
def test_verifier_results(status: str, fid: str) -> None:
    ctx = check(_signed(VALID), signing_key="k", verifier=lambda raw, key: VerifyResult(status, "detail"))
    assert ids(ctx) == [fid]


def test_verifier_crash_is_reported() -> None:
    def boom(raw: bytes, key: str) -> VerifyResult:
        raise RuntimeError("nope")

    ctx = check(_signed(VALID), signing_key="k", verifier=boom)
    assert ids(ctx) == ["securitytxt-signature-check-failed"]


# Real gpg


def test_gpg_armor_roundtrip(gpg: Gpg) -> None:
    clear = split_cleartext(gpg.sign(VALID))
    assert clear.text.rstrip("\n") == VALID.rstrip("\n")
    assert clear.packet_hash == "SHA256"


def test_gpg_good_signature(gpg: Gpg) -> None:
    signed = gpg.sign(VALID)
    assert gpg_verify(signed.encode(), str(gpg.key_path)).status == "good"
    ctx = check(signed, signing_key=str(gpg.key_path))
    assert ids(ctx) == []


def test_gpg_tampered_and_wrong_key(gpg: Gpg) -> None:
    signed = gpg.sign(VALID)
    tampered = signed.replace("security@example.com", "attacker@example.net")
    assert gpg_verify(tampered.encode(), str(gpg.key_path)).status == "bad"
    result = gpg_verify(signed.encode(), str(gpg.other_key_path))
    assert result.status == "bad"
    assert "not signed by the given key" in result.detail
    ctx = check(tampered, signing_key=str(gpg.key_path))
    assert ids(ctx) == ["securitytxt-signature-invalid"]


def test_gpg_sha1_digest_is_weak(gpg: Gpg) -> None:
    ctx = check(gpg.sign(VALID, digest="SHA1"), signing_key=str(gpg.key_path))
    assert "securitytxt-signature-weak-hash" in ids(ctx)


def test_gpg_errors(gpg: Gpg, tmp_path, monkeypatch) -> None:
    assert gpg_verify(b"x", str(tmp_path / "missing.asc")).status == "error"
    junk = tmp_path / "junk.asc"
    junk.write_text("not a key")
    res = gpg_verify(b"x", str(junk))
    assert res.status == "error"
    assert "could not import" in res.detail
    monkeypatch.setattr(shutil, "which", lambda name: None)
    res = gpg_verify(b"x", str(gpg.key_path))
    assert res.status == "error"
    assert "gpg is not installed" in res.detail
