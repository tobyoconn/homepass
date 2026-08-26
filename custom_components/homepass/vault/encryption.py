"""AES-256-GCM encryption boundary for HomePASS credential secrets."""

from __future__ import annotations

import secrets

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from .errors import (
    VaultAuthenticationError,
    VaultCorruptDataError,
    VaultUnavailableError,
    VaultUnsupportedKeyVersionError,
    VaultUnsupportedSchemaVersionError,
)
from .identifiers import VaultCredentialId
from .models import (
    AES_GCM_KEY_BYTES,
    AES_GCM_NONCE_BYTES,
    AES_GCM_TAG_BYTES,
    ENVELOPE_SCHEMA_VERSION,
    ROOT_KEY_VERSION,
    EncryptedSecretEnvelope,
)


def authenticated_data(
    credential_id: VaultCredentialId,
    key_version: int,
    schema_version: int,
) -> bytes:
    """Construct the exact canonical ADR 0002 authenticated metadata."""
    return (
        f'{{"credential_id":"{credential_id}","key_version":{key_version},'
        f'"schema_version":{schema_version}}}'
    ).encode()


class VaultEncryption:
    """Encrypt and authenticate credentials without performing storage."""

    __slots__ = ("_aesgcm", "_key_version")

    def __init__(self, key: bytes, key_version: int = ROOT_KEY_VERSION) -> None:
        """Initialize the AES-256-GCM codec with an exact-length key."""
        if not isinstance(key, bytes) or len(key) != AES_GCM_KEY_BYTES:
            raise VaultUnavailableError
        if key_version != ROOT_KEY_VERSION:
            raise VaultUnsupportedKeyVersionError
        self._aesgcm = AESGCM(key)
        self._key_version = key_version

    def __repr__(self) -> str:
        """Return no key or cryptographic state."""
        return f"{type(self).__name__}(key=<redacted>, key_version={self._key_version})"

    def encrypt(self, credential_id: VaultCredentialId, plaintext: str) -> EncryptedSecretEnvelope:
        """Encrypt one in-memory credential using a unique 96-bit nonce."""
        if not isinstance(credential_id, VaultCredentialId):
            raise TypeError("credential_id must be a VaultCredentialId")
        if not isinstance(plaintext, str) or not plaintext:
            raise VaultCorruptDataError
        nonce = secrets.token_bytes(AES_GCM_NONCE_BYTES)
        if len(nonce) != AES_GCM_NONCE_BYTES:
            raise VaultUnavailableError
        aad = authenticated_data(credential_id, self._key_version, ENVELOPE_SCHEMA_VERSION)
        combined = self._aesgcm.encrypt(nonce, plaintext.encode(), aad)
        ciphertext = combined[:-AES_GCM_TAG_BYTES]
        tag = combined[-AES_GCM_TAG_BYTES:]
        return EncryptedSecretEnvelope(
            credential_id=credential_id,
            ciphertext=ciphertext,
            nonce=nonce,
            authentication_data=tag,
            key_version=self._key_version,
            schema_version=ENVELOPE_SCHEMA_VERSION,
        )

    def decrypt(self, envelope: EncryptedSecretEnvelope) -> str:
        """Authenticate and decrypt one envelope entirely in memory."""
        if envelope.schema_version != ENVELOPE_SCHEMA_VERSION:
            raise VaultUnsupportedSchemaVersionError
        if envelope.key_version != self._key_version:
            raise VaultUnsupportedKeyVersionError
        if len(envelope.nonce) != AES_GCM_NONCE_BYTES:
            raise VaultCorruptDataError
        if len(envelope.authentication_data) != AES_GCM_TAG_BYTES or not envelope.ciphertext:
            raise VaultCorruptDataError
        aad = authenticated_data(
            envelope.credential_id,
            envelope.key_version,
            envelope.schema_version,
        )
        try:
            plaintext = self._aesgcm.decrypt(
                envelope.nonce,
                envelope.ciphertext + envelope.authentication_data,
                aad,
            )
        except InvalidTag as err:
            raise VaultAuthenticationError from err
        try:
            return plaintext.decode()
        except UnicodeDecodeError as err:
            raise VaultCorruptDataError from err
