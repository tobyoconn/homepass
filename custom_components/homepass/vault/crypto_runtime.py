"""In-memory AES-GCM runtime compatibility probe.

This module performs an in-memory check with fixed non-secret data. It does not persist
keys, encrypted data, or plaintext and does not authorize production credential storage.
"""

from __future__ import annotations

import secrets
from collections.abc import Callable
from dataclasses import dataclass
from importlib import import_module
from types import ModuleType
from typing import Protocol, cast


class _AESGCM(Protocol):
    """Describe the AESGCM API used by the compatibility probe."""

    def __init__(self, key: bytes) -> None: ...

    def encrypt(self, nonce: bytes, data: bytes, associated_data: bytes | None) -> bytes:
        """Encrypt and authenticate data."""
        ...

    def decrypt(self, nonce: bytes, data: bytes, associated_data: bytes | None) -> bytes:
        """Authenticate and decrypt data."""
        ...


type ModuleLoader = Callable[[str], ModuleType]


@dataclass(frozen=True, slots=True)
class CryptoRuntimeResult:
    """Contain only non-secret AES-GCM compatibility results."""

    cryptography_version: str | None
    aesgcm_available: bool
    round_trip_succeeded: bool
    tamper_rejected: bool
    error_type: str | None = None
    error_message: str | None = None

    def to_dict(self) -> dict[str, bool | str | None]:
        """Return the PIN-safe diagnostic action response."""
        return {
            "cryptography_version": self.cryptography_version,
            "aesgcm_available": self.aesgcm_available,
            "round_trip_succeeded": self.round_trip_succeeded,
            "tamper_rejected": self.tamper_rejected,
            "error_type": self.error_type,
            "error_message": self.error_message,
        }


def _safe_error(error: Exception, *, dependency_unavailable: bool) -> CryptoRuntimeResult:
    """Create a fixed-message result without exposing exception details."""
    return CryptoRuntimeResult(
        cryptography_version=None,
        aesgcm_available=not dependency_unavailable,
        round_trip_succeeded=False,
        tamper_rejected=False,
        error_type=type(error).__name__,
        error_message=(
            "AESGCM runtime dependency is unavailable."
            if dependency_unavailable
            else "AESGCM runtime compatibility check failed."
        ),
    )


def run_crypto_runtime_check(
    module_loader: ModuleLoader = import_module,
) -> CryptoRuntimeResult:
    """Exercise AES-256-GCM entirely in memory with fixed non-secret data."""
    try:
        cryptography_module = module_loader("cryptography")
        aead_module = module_loader("cryptography.hazmat.primitives.ciphers.aead")
        aesgcm_type = cast(type[_AESGCM], aead_module.AESGCM)
        version = cast(str | None, getattr(cryptography_module, "__version__", None))
    except (AttributeError, ImportError) as error:
        return _safe_error(error, dependency_unavailable=True)

    try:
        key = secrets.token_bytes(32)
        nonce = secrets.token_bytes(12)
        plaintext = b"HomePASS AESGCM compatibility check"
        aad = b"homepass-vault-runtime-check-v1"
        aesgcm = aesgcm_type(key)
        encrypted = aesgcm.encrypt(nonce, plaintext, aad)
        round_trip_succeeded = aesgcm.decrypt(nonce, encrypted, aad) == plaintext

        modified = bytearray(encrypted)
        modified[-1] ^= 1
        try:
            aesgcm.decrypt(nonce, bytes(modified), aad)
        except Exception:  # Authentication rejection is the capability under test.
            tamper_rejected = True
        else:
            tamper_rejected = False
    except Exception as error:
        result = _safe_error(error, dependency_unavailable=False)
        return CryptoRuntimeResult(
            cryptography_version=version,
            aesgcm_available=result.aesgcm_available,
            round_trip_succeeded=result.round_trip_succeeded,
            tamper_rejected=result.tamper_rejected,
            error_type=result.error_type,
            error_message=result.error_message,
        )

    return CryptoRuntimeResult(
        cryptography_version=version,
        aesgcm_available=True,
        round_trip_succeeded=round_trip_succeeded,
        tamper_rejected=tamper_rejected,
    )
