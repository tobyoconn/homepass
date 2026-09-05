"""NTAG 424 DNA Secure Dynamic Messaging verification.

Implements the encrypted-PICC, zero-length-MAC profile from NXP AN12196. The
NDEF URL is ``.../t/{public_id}?e={32 hex}&c={16 hex}``.
"""

from __future__ import annotations

import hmac
from dataclasses import dataclass

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.cmac import CMAC


class SunVerificationError(ValueError):
    """Raised when an NTAG 424 DNA SUN message cannot be trusted."""


@dataclass(frozen=True, slots=True)
class SunMessage:
    uid_hex: str
    counter: int


def _aes_cmac(key: bytes, value: bytes) -> bytes:
    cmac = CMAC(algorithms.AES(key))
    cmac.update(value)
    return cmac.finalize()


def _truncated_cmac(key: bytes, value: bytes) -> bytes:
    return _aes_cmac(key, value)[1::2]


def verify_encrypted_picc_sun(
    *,
    encrypted_picc_hex: str,
    mac_hex: str,
    meta_read_key: bytes,
    file_read_key: bytes,
    expected_uid_hex: str,
) -> SunMessage:
    """Verify and decode one tag tap using NXP's encrypted-PICC profile."""
    if len(meta_read_key) != 16 or len(file_read_key) != 16:
        raise SunVerificationError("NTAG 424 keys must be AES-128 keys")
    try:
        encrypted_picc = bytes.fromhex(encrypted_picc_hex)
        supplied_mac = bytes.fromhex(mac_hex)
    except ValueError as err:
        raise SunVerificationError("SUN values must be hexadecimal") from err
    if len(encrypted_picc) != 16 or len(supplied_mac) != 8:
        raise SunVerificationError("SUN values have invalid lengths")

    decryptor = Cipher(algorithms.AES(meta_read_key), modes.CBC(bytes(16))).decryptor()
    picc_data = decryptor.update(encrypted_picc) + decryptor.finalize()
    picc_data_tag = picc_data[0]
    if not (picc_data_tag & 0x80) or not (picc_data_tag & 0x40) or (picc_data_tag & 0x0F) != 7:
        raise SunVerificationError("Unsupported NTAG 424 PICC mirror profile")
    uid = picc_data[1:8]
    counter_bytes = picc_data[8:11]
    uid_hex = uid.hex().upper()
    if not hmac.compare_digest(uid_hex, expected_uid_hex.upper()):
        raise SunVerificationError("SUN tag identity does not match")

    sv2 = b"\x3c\xc3\x00\x01\x00\x80" + uid + counter_bytes
    sv2 += bytes(16 - len(sv2))
    session_mac_key = _aes_cmac(file_read_key, sv2)
    if not hmac.compare_digest(_truncated_cmac(session_mac_key, b""), supplied_mac):
        raise SunVerificationError("SUN authentication failed")
    return SunMessage(uid_hex, int.from_bytes(counter_bytes, "little"))


__all__ = ["SunMessage", "SunVerificationError", "verify_encrypted_picc_sun"]
