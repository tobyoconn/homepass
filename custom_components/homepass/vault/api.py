"""Production Standard Mode credential-vault API."""

from __future__ import annotations

import asyncio
import secrets
from collections.abc import Callable

from homeassistant.core import HomeAssistant

from .encryption import VaultEncryption
from .errors import (
    VaultAuthenticationError,
    VaultCorruptDataError,
    VaultNotInitializedError,
    VaultPromotionError,
    VaultUnavailableError,
    VaultUnsupportedKeyVersionError,
    VaultUnsupportedSchemaVersionError,
)
from .identifiers import StagedSecretHandle, VaultCredentialId
from .models import AES_GCM_KEY_BYTES, StagedSecret, VaultPromotionReceipt, VaultStatus
from .repository import EncryptedEnvelopeRepository, RootKeyRepository


def _trace_stage(trace: Callable[[str], None] | None, stage: str) -> None:
    """Run diagnostics without allowing them to affect credential retrieval."""
    if trace is not None:
        try:
            trace(stage)
        except Exception:
            return


class CredentialVault:
    """Coordinate encryption and encrypted persistence behind a plaintext API."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize Standard Mode dependencies without loading key material."""
        self._key_repository = RootKeyRepository(hass)
        self._envelope_repository = EncryptedEnvelopeRepository(hass)
        self._encryption: VaultEncryption | None = None
        self._status = VaultStatus.UNINITIALIZED
        self._lock = asyncio.Lock()

    @property
    def status(self) -> VaultStatus:
        """Return the current vault lifecycle status."""
        return self._status

    def __repr__(self) -> str:
        """Return lifecycle state without any key or encrypted material."""
        return f"{type(self).__name__}(status={self._status.value!r})"

    async def initialize(self) -> None:
        """Load or safely create the accepted Standard Mode root key."""
        async with self._lock:
            try:
                envelopes = await self._envelope_repository.list_all()
                key = await self._key_repository.load()
                if key is None:
                    if envelopes:
                        self._status = VaultStatus.UNAVAILABLE
                        raise VaultUnavailableError
                    key = secrets.token_bytes(AES_GCM_KEY_BYTES)
                    if len(key) != AES_GCM_KEY_BYTES:
                        self._status = VaultStatus.UNAVAILABLE
                        raise VaultUnavailableError
                    await self._key_repository.store(key)
                self._encryption = VaultEncryption(key)
                self._status = VaultStatus.UNLOCKED
            except (VaultUnsupportedKeyVersionError, VaultUnavailableError):
                self._status = VaultStatus.UNAVAILABLE
                raise
            except (VaultCorruptDataError, VaultUnsupportedSchemaVersionError):
                self._status = VaultStatus.CORRUPT
                raise

    async def store(self, plaintext: str) -> VaultCredentialId:
        """Encrypt and persist one credential supplied only in memory."""
        async with self._lock:
            encryption = self._require_encryption()
            credential_id = VaultCredentialId.new()
            envelope = encryption.encrypt(credential_id, plaintext)
            await self._envelope_repository.store(envelope)
            return credential_id

    async def retrieve(
        self,
        credential_id: VaultCredentialId,
        *,
        trace: Callable[[str], None] | None = None,
    ) -> str:
        """Authenticate and return one plaintext credential in memory."""
        async with self._lock:
            _trace_stage(trace, "vault_lock_acquired")
            encryption = self._require_encryption()
            _trace_stage(trace, "vault_envelope_lookup_started")
            envelope = await self._envelope_repository.retrieve(credential_id)
            _trace_stage(trace, "vault_authoritative_lookup_completed")
            try:
                plaintext = encryption.decrypt(envelope)
            except VaultAuthenticationError:
                self._status = VaultStatus.CORRUPT
                raise
            _trace_stage(trace, "vault_decryption_completed")
            return plaintext

    async def delete(self, credential_id: VaultCredentialId) -> None:
        """Delete one encrypted credential."""
        async with self._lock:
            self._require_encryption()
            await self._envelope_repository.delete(credential_id)

    async def exists(self, credential_id: VaultCredentialId) -> bool:
        """Return whether one encrypted credential exists."""
        async with self._lock:
            self._require_encryption()
            return await self._envelope_repository.exists(credential_id)

    async def stage(
        self,
        credential_id: VaultCredentialId,
        plaintext: str,
    ) -> StagedSecretHandle:
        """Encrypt and atomically stage a replacement candidate."""
        async with self._lock:
            encryption = self._require_encryption()
            expected_revision = await self._envelope_repository.revision(credential_id)
            handle = StagedSecretHandle.new()
            envelope = encryption.encrypt(VaultCredentialId(handle.value), plaintext)
            await self._envelope_repository.stage(
                StagedSecret(
                    handle=handle,
                    credential_id=credential_id,
                    expected_revision=expected_revision,
                    envelope=envelope,
                )
            )
            return handle

    async def retrieve_staged(self, handle: StagedSecretHandle) -> str:
        """Authenticate and return a staged plaintext only in process memory."""
        async with self._lock:
            encryption = self._require_encryption()
            staged = await self._envelope_repository.retrieve_staged(handle)
            try:
                return encryption.decrypt(staged.envelope)
            except VaultAuthenticationError:
                self._status = VaultStatus.CORRUPT
                raise

    async def promote(self, handle: StagedSecretHandle) -> VaultPromotionReceipt:
        """Atomically replace the authoritative credential and consume its stage."""
        async with self._lock:
            encryption = self._require_encryption()
            receipt = await self._envelope_repository.promotion_receipt(handle)
            if receipt is not None:
                return receipt
            staged = await self._envelope_repository.retrieve_staged(handle)
            try:
                plaintext = encryption.decrypt(staged.envelope)
                promoted = encryption.encrypt(staged.credential_id, plaintext)
                return await self._envelope_repository.promote(handle, promoted)
            except VaultAuthenticationError:
                self._status = VaultStatus.CORRUPT
                raise
            except VaultUnavailableError as err:
                raise VaultPromotionError from err

    async def discard(self, handle: StagedSecretHandle) -> None:
        """Idempotently discard a staged candidate without changing authority."""
        async with self._lock:
            self._require_encryption()
            await self._envelope_repository.discard(handle)

    async def revision(self, credential_id: VaultCredentialId) -> int:
        """Return a non-secret optimistic-concurrency revision."""
        async with self._lock:
            self._require_encryption()
            return await self._envelope_repository.revision(credential_id)

    async def promotion_receipt(self, handle: StagedSecretHandle) -> VaultPromotionReceipt | None:
        """Return non-secret evidence that a staged handle was promoted."""
        async with self._lock:
            self._require_encryption()
            return await self._envelope_repository.promotion_receipt(handle)

    def _require_encryption(self) -> VaultEncryption:
        """Return the initialized codec or fail closed."""
        if self._status is VaultStatus.UNAVAILABLE:
            raise VaultUnavailableError
        if self._encryption is None or self._status is not VaultStatus.UNLOCKED:
            raise VaultNotInitializedError
        return self._encryption
