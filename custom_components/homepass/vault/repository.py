"""Home Assistant storage repositories for encrypted vault records."""

from __future__ import annotations

import asyncio
from base64 import b64decode, b64encode
from binascii import Error as Base64Error
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
from typing import TypedDict

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .errors import (
    VaultCorruptDataError,
    VaultCredentialNotFoundError,
    VaultDuplicateStageError,
    VaultInvalidStagedSecretHandleError,
    VaultStagedSecretMissingError,
    VaultStalePromotionError,
    VaultUnavailableError,
    VaultUnsupportedKeyVersionError,
    VaultUnsupportedSchemaVersionError,
)
from .identifiers import StagedSecretHandle, VaultCredentialId
from .models import (
    AES_GCM_ALGORITHM,
    AES_GCM_KEY_BYTES,
    ENVELOPE_SCHEMA_VERSION,
    ROOT_KEY_VERSION,
    EncryptedSecretEnvelope,
    EncryptedSecretEnvelopeData,
    StagedSecret,
    StagedSecretData,
    VaultPromotionReceipt,
    VaultPromotionReceiptData,
)

VAULT_STORE_VERSION = 1
VAULT_STORE_MINOR_VERSION = 0
VAULT_KEY_STORAGE_KEY = "homepass.vault_key"
VAULT_ENVELOPE_STORAGE_KEY = "homepass.vault_credentials"
VAULT_ENVELOPE_SCHEMA_VERSION = 3


class RootKeyStorageData(TypedDict):
    """Versioned Standard Mode root-key record."""

    schema_version: int
    key_version: int
    algorithm: str
    key: str


class LegacyEnvelopeStorageData(TypedDict):
    """Version-one collection containing only authoritative envelopes."""

    schema_version: int
    envelopes: dict[str, EncryptedSecretEnvelopeData]


class EnvelopeStorageData(TypedDict):
    """Versioned authoritative and staged encrypted credential collection."""

    schema_version: int
    envelopes: dict[str, EncryptedSecretEnvelopeData]
    revisions: dict[str, int]
    staged_secrets: dict[str, StagedSecretData]
    promotion_receipts: dict[str, VaultPromotionReceiptData]


@dataclass(slots=True)
class _EnvelopeState:
    """Validated private Vault snapshot used by atomic mutations."""

    envelopes: dict[VaultCredentialId, EncryptedSecretEnvelope]
    revisions: dict[VaultCredentialId, int]
    staged_secrets: dict[StagedSecretHandle, StagedSecret]
    promotion_receipts: dict[StagedSecretHandle, VaultPromotionReceipt]
    migrated: bool = False


class RootKeyRepository:
    """Persist only the Standard Mode root key in its private record."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the atomic root-key store."""
        self._store = Store[RootKeyStorageData](
            hass,
            VAULT_STORE_VERSION,
            VAULT_KEY_STORAGE_KEY,
            atomic_writes=True,
            minor_version=VAULT_STORE_MINOR_VERSION,
        )
        self._lock = asyncio.Lock()

    async def load(self) -> bytes | None:
        """Load and strictly validate the root key without exposing it."""
        async with self._lock:
            try:
                data = await self._store.async_load()
            except Exception as err:
                raise VaultUnavailableError from err
            if data is None:
                return None
            if not isinstance(data, Mapping):
                raise VaultUnavailableError
            if set(data) != {"schema_version", "key_version", "algorithm", "key"}:
                raise VaultUnavailableError
            if (
                isinstance(data["schema_version"], bool)
                or data["schema_version"] != ENVELOPE_SCHEMA_VERSION
            ):
                raise VaultUnsupportedSchemaVersionError
            if isinstance(data["key_version"], bool) or data["key_version"] != ROOT_KEY_VERSION:
                raise VaultUnsupportedKeyVersionError
            if data["algorithm"] != AES_GCM_ALGORITHM or not isinstance(data["key"], str):
                raise VaultUnavailableError
            try:
                key = b64decode(data["key"], validate=True)
            except (Base64Error, UnicodeEncodeError, ValueError) as err:
                raise VaultUnavailableError from err
            if len(key) != AES_GCM_KEY_BYTES:
                raise VaultUnavailableError
            return key

    async def store(self, key: bytes) -> None:
        """Atomically persist one exact-length Standard Mode root key."""
        if not isinstance(key, bytes) or len(key) != AES_GCM_KEY_BYTES:
            raise VaultUnavailableError
        data: RootKeyStorageData = {
            "schema_version": ENVELOPE_SCHEMA_VERSION,
            "key_version": ROOT_KEY_VERSION,
            "algorithm": AES_GCM_ALGORITHM,
            "key": b64encode(key).decode("ascii"),
        }
        async with self._lock:
            try:
                await self._store.async_save(data)
            except Exception as err:
                raise VaultUnavailableError from err


class EncryptedEnvelopeRepository:
    """Persist encrypted envelopes without performing cryptography."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the atomic encrypted-envelope store."""
        self._store = Store[EnvelopeStorageData](
            hass,
            VAULT_STORE_VERSION,
            VAULT_ENVELOPE_STORAGE_KEY,
            atomic_writes=True,
            minor_version=VAULT_STORE_MINOR_VERSION,
        )
        self._lock = asyncio.Lock()
        self._state: _EnvelopeState | None = None

    async def list_all(self) -> dict[VaultCredentialId, EncryptedSecretEnvelope]:
        """Load and strictly validate all encrypted envelopes."""
        async with self._lock:
            state = await self._load_unlocked()
            if state.migrated:
                await self._save_unlocked(state)
            return state.envelopes.copy()

    async def store(self, envelope: EncryptedSecretEnvelope) -> None:
        """Atomically persist an already-encrypted envelope."""
        if not isinstance(envelope, EncryptedSecretEnvelope):
            raise TypeError("envelope must be an EncryptedSecretEnvelope")
        async with self._lock:
            state = await self._load_unlocked()
            current_revision = state.revisions.get(envelope.credential_id, 0)
            state.envelopes[envelope.credential_id] = envelope
            state.revisions[envelope.credential_id] = current_revision + 1
            await self._save_unlocked(state)

    async def retrieve(self, credential_id: VaultCredentialId) -> EncryptedSecretEnvelope:
        """Return one encrypted envelope by typed identifier."""
        self._validate_identifier(credential_id)
        async with self._lock:
            state = await self._load_unlocked()
            try:
                return state.envelopes[credential_id]
            except KeyError as err:
                raise VaultCredentialNotFoundError from err

    async def delete(self, credential_id: VaultCredentialId) -> None:
        """Delete exactly one encrypted envelope."""
        self._validate_identifier(credential_id)
        async with self._lock:
            state = await self._load_unlocked()
            if credential_id not in state.envelopes:
                raise VaultCredentialNotFoundError
            del state.envelopes[credential_id]
            del state.revisions[credential_id]
            state.staged_secrets = {
                handle: staged
                for handle, staged in state.staged_secrets.items()
                if staged.credential_id != credential_id
            }
            await self._save_unlocked(state)

    async def exists(self, credential_id: VaultCredentialId) -> bool:
        """Return whether an encrypted envelope exists."""
        self._validate_identifier(credential_id)
        async with self._lock:
            return credential_id in (await self._load_unlocked()).envelopes

    async def stage(self, staged_secret: StagedSecret) -> None:
        """Atomically persist one encrypted candidate for an existing credential."""
        if not isinstance(staged_secret, StagedSecret):
            raise TypeError("staged_secret must be a StagedSecret")
        async with self._lock:
            state = await self._load_unlocked()
            if staged_secret.credential_id not in state.envelopes:
                raise VaultCredentialNotFoundError
            if any(
                staged.credential_id == staged_secret.credential_id
                for staged in state.staged_secrets.values()
            ):
                raise VaultDuplicateStageError
            if staged_secret.expected_revision != state.revisions[staged_secret.credential_id]:
                raise VaultStalePromotionError
            if staged_secret.handle in state.promotion_receipts:
                raise VaultDuplicateStageError
            state.staged_secrets[staged_secret.handle] = staged_secret
            await self._save_unlocked(state)

    async def retrieve_staged(self, handle: StagedSecretHandle) -> StagedSecret:
        """Return one encrypted staged candidate by opaque handle."""
        self._validate_handle(handle)
        async with self._lock:
            state = await self._load_unlocked()
            try:
                return state.staged_secrets[handle]
            except KeyError as err:
                raise VaultStagedSecretMissingError from err

    async def promote(
        self,
        handle: StagedSecretHandle,
        promoted_envelope: EncryptedSecretEnvelope,
    ) -> VaultPromotionReceipt:
        """Atomically replace an authoritative envelope and consume its stage."""
        self._validate_handle(handle)
        if not isinstance(promoted_envelope, EncryptedSecretEnvelope):
            raise TypeError("promoted_envelope must be an EncryptedSecretEnvelope")
        async with self._lock:
            state = await self._load_unlocked()
            existing_receipt = state.promotion_receipts.get(handle)
            if existing_receipt is not None:
                return existing_receipt
            try:
                staged = state.staged_secrets[handle]
            except KeyError as err:
                raise VaultStagedSecretMissingError from err
            current_revision = state.revisions.get(staged.credential_id)
            if (
                current_revision != staged.expected_revision
                or staged.credential_id not in state.envelopes
            ):
                raise VaultStalePromotionError
            if promoted_envelope.credential_id != staged.credential_id:
                raise VaultStalePromotionError
            state.envelopes[staged.credential_id] = promoted_envelope
            revision = staged.expected_revision + 1
            state.revisions[staged.credential_id] = revision
            del state.staged_secrets[handle]
            receipt = VaultPromotionReceipt(handle, staged.credential_id, revision)
            state.promotion_receipts[handle] = receipt
            await self._save_unlocked(state)
            return receipt

    async def promotion_receipt(self, handle: StagedSecretHandle) -> VaultPromotionReceipt | None:
        """Return non-secret evidence for an already-completed promotion."""
        self._validate_handle(handle)
        async with self._lock:
            return (await self._load_unlocked()).promotion_receipts.get(handle)

    async def discard(self, handle: StagedSecretHandle) -> None:
        """Atomically discard a staged candidate, if it still exists."""
        self._validate_handle(handle)
        async with self._lock:
            state = await self._load_unlocked()
            if handle not in state.staged_secrets:
                return
            del state.staged_secrets[handle]
            await self._save_unlocked(state)

    async def revision(self, credential_id: VaultCredentialId) -> int:
        """Return the safe optimistic-concurrency revision for one credential."""
        self._validate_identifier(credential_id)
        async with self._lock:
            state = await self._load_unlocked()
            try:
                return state.revisions[credential_id]
            except KeyError as err:
                raise VaultCredentialNotFoundError from err

    async def _load_unlocked(self) -> _EnvelopeState:
        """Load records while the repository lock is held."""
        if self._state is not None:
            return deepcopy(self._state)
        try:
            data = await self._store.async_load()
        except Exception as err:
            raise VaultUnavailableError from err
        if data is None:
            state = _EnvelopeState({}, {}, {}, {})
            self._state = deepcopy(state)
            return state
        if not isinstance(data, Mapping):
            raise VaultCorruptDataError
        schema_version = data.get("schema_version")
        if isinstance(schema_version, bool) or not isinstance(schema_version, int):
            raise VaultUnsupportedSchemaVersionError
        if schema_version == 1:
            if set(data) != set(LegacyEnvelopeStorageData.__required_keys__):
                raise VaultCorruptDataError
        elif schema_version == 2:
            if set(data) != {"schema_version", "envelopes", "revisions", "staged_secrets"}:
                raise VaultCorruptDataError
        elif schema_version == VAULT_ENVELOPE_SCHEMA_VERSION:
            if set(data) != set(EnvelopeStorageData.__required_keys__):
                raise VaultCorruptDataError
        else:
            raise VaultUnsupportedSchemaVersionError
        raw_envelopes = data["envelopes"]
        if not isinstance(raw_envelopes, Mapping):
            raise VaultCorruptDataError
        records: dict[VaultCredentialId, EncryptedSecretEnvelope] = {}
        try:
            for stored_id, raw_envelope in raw_envelopes.items():
                if not isinstance(stored_id, str) or not isinstance(raw_envelope, Mapping):
                    raise VaultCorruptDataError
                envelope = EncryptedSecretEnvelope.from_dict(raw_envelope)
                if str(envelope.credential_id) != stored_id:
                    raise VaultCorruptDataError
                if envelope.schema_version != ENVELOPE_SCHEMA_VERSION:
                    raise VaultUnsupportedSchemaVersionError
                if envelope.key_version != ROOT_KEY_VERSION:
                    raise VaultUnsupportedKeyVersionError
                records[envelope.credential_id] = envelope
        except (
            VaultCorruptDataError,
            VaultUnsupportedKeyVersionError,
            VaultUnsupportedSchemaVersionError,
        ):
            raise
        except Exception as err:
            raise VaultCorruptDataError from err

        if schema_version == 1:
            state = _EnvelopeState(
                records,
                {credential_id: 1 for credential_id in records},
                {},
                {},
                migrated=True,
            )
            self._state = deepcopy(state)
            return state

        raw_revisions = data["revisions"]
        raw_staged = data["staged_secrets"]
        raw_receipts = data.get("promotion_receipts", {})
        if not isinstance(raw_revisions, Mapping) or not isinstance(raw_staged, Mapping):
            raise VaultCorruptDataError
        if not isinstance(raw_receipts, Mapping):
            raise VaultCorruptDataError
        revisions: dict[VaultCredentialId, int] = {}
        staged_secrets: dict[StagedSecretHandle, StagedSecret] = {}
        promotion_receipts: dict[StagedSecretHandle, VaultPromotionReceipt] = {}
        try:
            for stored_id, revision in raw_revisions.items():
                if (
                    not isinstance(stored_id, str)
                    or isinstance(revision, bool)
                    or not isinstance(revision, int)
                    or revision < 1
                ):
                    raise VaultCorruptDataError
                revisions[VaultCredentialId.from_string(stored_id)] = revision
            if set(revisions) != set(records):
                raise VaultCorruptDataError
            staged_targets: set[VaultCredentialId] = set()
            for stored_handle, raw_staged_secret in raw_staged.items():
                if not isinstance(stored_handle, str) or not isinstance(raw_staged_secret, Mapping):
                    raise VaultCorruptDataError
                handle = StagedSecretHandle.from_string(stored_handle)
                staged = StagedSecret.from_dict(handle, raw_staged_secret)
                if staged.credential_id not in records or staged.credential_id in staged_targets:
                    raise VaultCorruptDataError
                if staged.expected_revision > revisions[staged.credential_id]:
                    raise VaultCorruptDataError
                staged_targets.add(staged.credential_id)
                staged_secrets[handle] = staged
            for stored_handle, raw_receipt in raw_receipts.items():
                if not isinstance(stored_handle, str) or not isinstance(raw_receipt, Mapping):
                    raise VaultCorruptDataError
                handle = StagedSecretHandle.from_string(stored_handle)
                if handle in staged_secrets:
                    raise VaultCorruptDataError
                receipt = VaultPromotionReceipt.from_dict(handle, raw_receipt)
                if (
                    receipt.credential_id not in records
                    or revisions[receipt.credential_id] < receipt.revision
                ):
                    raise VaultCorruptDataError
                promotion_receipts[handle] = receipt
        except VaultCorruptDataError:
            raise
        except Exception as err:
            raise VaultCorruptDataError from err
        state = _EnvelopeState(
            records,
            revisions,
            staged_secrets,
            promotion_receipts,
            migrated=schema_version == 2,
        )
        self._state = deepcopy(state)
        self._state.migrated = False
        return state

    async def _save_unlocked(
        self,
        state: _EnvelopeState,
    ) -> None:
        """Save records while the repository lock is held."""
        data: EnvelopeStorageData = {
            "schema_version": VAULT_ENVELOPE_SCHEMA_VERSION,
            "envelopes": {
                str(credential_id): envelope.to_dict()
                for credential_id, envelope in state.envelopes.items()
            },
            "revisions": {
                str(credential_id): revision for credential_id, revision in state.revisions.items()
            },
            "staged_secrets": {
                str(handle): staged.to_dict() for handle, staged in state.staged_secrets.items()
            },
            "promotion_receipts": {
                str(handle): receipt.to_dict()
                for handle, receipt in state.promotion_receipts.items()
            },
        }
        try:
            await self._store.async_save(data)
        except Exception as err:
            raise VaultUnavailableError from err
        self._state = deepcopy(state)
        self._state.migrated = False

    @staticmethod
    def _validate_identifier(credential_id: VaultCredentialId) -> None:
        """Require the strong vault identifier at every repository boundary."""
        if not isinstance(credential_id, VaultCredentialId):
            raise TypeError("credential_id must be a VaultCredentialId")

    @staticmethod
    def _validate_handle(handle: StagedSecretHandle) -> None:
        """Require an opaque staged-secret handle at repository boundaries."""
        if not isinstance(handle, StagedSecretHandle):
            raise VaultInvalidStagedSecretHandleError
