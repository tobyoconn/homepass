"""Immutable credential-vault persistence models."""

from __future__ import annotations

from base64 import b64decode, b64encode
from binascii import Error as Base64Error
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Final, Self, TypedDict
from uuid import UUID

from .identifiers import StagedSecretHandle, VaultCredentialId

AES_GCM_ALGORITHM: Final = "AES-256-GCM"
ENVELOPE_SCHEMA_VERSION: Final = 1
ROOT_KEY_VERSION: Final = 1
AES_GCM_KEY_BYTES: Final = 32
AES_GCM_NONCE_BYTES: Final = 12
AES_GCM_TAG_BYTES: Final = 16


class VaultStatus(StrEnum):
    """Lifecycle status of a credential vault."""

    UNINITIALIZED = "uninitialized"
    UNLOCKED = "unlocked"
    UNAVAILABLE = "unavailable"
    CORRUPT = "corrupt"


class AccessMethod(StrEnum):
    """Supported non-secret Access Method identifiers."""

    PIN = "pin"


class EncryptedSecretEnvelopeData(TypedDict):
    """Exact ADR 0002 JSON-compatible encrypted envelope."""

    algorithm: str
    authentication_data: str
    ciphertext: str
    credential_id: str
    key_version: int
    nonce: str
    schema_version: int


class StagedSecretData(TypedDict):
    """Encrypted staged-secret record stored only inside Secure Vault."""

    credential_id: str
    envelope: EncryptedSecretEnvelopeData
    expected_revision: int


class VaultPromotionReceiptData(TypedDict):
    """Non-secret proof that an opaque staged handle was promoted."""

    credential_id: str
    revision: int


class CredentialMetadataData(TypedDict):
    """JSON-compatible representation of non-secret credential metadata."""

    credential_id: str
    person_id: str
    access_method: str
    enabled: bool
    created_at: str
    updated_at: str


def _required(data: Mapping[str, object], field_name: str, model_name: str) -> object:
    """Return a required serialized field without echoing its value."""
    try:
        return data[field_name]
    except KeyError as err:
        raise ValueError(f"Missing required {model_name} field: {field_name}") from err


def _parse_datetime(value: object, field_name: str, model_name: str) -> datetime:
    """Parse a serialized datetime without echoing malformed input."""
    if not isinstance(value, str):
        raise TypeError(f"{model_name} {field_name} must be an ISO 8601 string")
    try:
        return datetime.fromisoformat(value)
    except ValueError as err:
        raise ValueError(f"{model_name} {field_name} must be a valid ISO 8601 datetime") from err


def _normalize_datetime(value: datetime, field_name: str, model_name: str) -> datetime:
    """Validate a datetime and normalize it to UTC."""
    if not isinstance(value, datetime):
        raise TypeError(f"{model_name} {field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{model_name} {field_name} must be timezone-aware")
    return value.astimezone(UTC)


def _positive_int(value: object, field_name: str, model_name: str) -> int:
    """Validate a positive integer without accepting booleans."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{model_name} {field_name} must be an integer")
    if value < 1:
        raise ValueError(f"{model_name} {field_name} must be positive")
    return value


def _binary(value: object, field_name: str) -> bytes:
    """Validate a non-empty immutable binary field."""
    if not isinstance(value, bytes):
        raise TypeError(f"EncryptedSecretEnvelope {field_name} must be bytes")
    if not value:
        raise ValueError(f"EncryptedSecretEnvelope {field_name} must not be empty")
    return value


def _decode_binary(value: object, field_name: str) -> bytes:
    """Decode strict Base64 without echoing malformed input."""
    if not isinstance(value, str):
        raise TypeError(f"EncryptedSecretEnvelope {field_name} must be a Base64 string")
    try:
        decoded = b64decode(value, validate=True)
    except (Base64Error, ValueError) as err:
        raise ValueError(f"EncryptedSecretEnvelope {field_name} must be valid Base64") from err
    return _binary(decoded, field_name)


def _parse_access_method(value: object) -> AccessMethod:
    """Parse a supported Access Method without echoing malformed input."""
    if not isinstance(value, str):
        raise TypeError("CredentialMetadata access_method must be a string")
    try:
        return AccessMethod(value)
    except ValueError as err:
        raise ValueError("CredentialMetadata access_method is unsupported") from err


@dataclass(frozen=True, slots=True, repr=False)
class EncryptedSecretEnvelope:
    """Exact versioned AES-256-GCM envelope defined by ADR 0002."""

    credential_id: VaultCredentialId
    ciphertext: bytes = field(repr=False)
    nonce: bytes = field(repr=False)
    authentication_data: bytes = field(repr=False)
    key_version: int = ROOT_KEY_VERSION
    schema_version: int = ENVELOPE_SCHEMA_VERSION
    algorithm: str = AES_GCM_ALGORITHM

    def __post_init__(self) -> None:
        """Validate the encrypted envelope without inspecting plaintext."""
        if not isinstance(self.credential_id, VaultCredentialId):
            raise TypeError("EncryptedSecretEnvelope credential_id must be a VaultCredentialId")
        _binary(self.ciphertext, "ciphertext")
        nonce = _binary(self.nonce, "nonce")
        tag = _binary(self.authentication_data, "authentication_data")
        if len(nonce) != AES_GCM_NONCE_BYTES:
            raise ValueError("EncryptedSecretEnvelope nonce must be exactly 12 bytes")
        if len(tag) != AES_GCM_TAG_BYTES:
            raise ValueError("EncryptedSecretEnvelope authentication_data must be 16 bytes")
        _positive_int(self.key_version, "key_version", "EncryptedSecretEnvelope")
        _positive_int(self.schema_version, "schema_version", "EncryptedSecretEnvelope")
        if self.algorithm != AES_GCM_ALGORITHM:
            raise ValueError("EncryptedSecretEnvelope algorithm is unsupported")

    def __repr__(self) -> str:
        """Return metadata while redacting all encrypted binary fields."""
        return (
            f"{type(self).__name__}(credential_id={self.credential_id!r}, "
            "ciphertext=<redacted>, nonce=<redacted>, authentication_data=<redacted>, "
            f"key_version={self.key_version!r}, schema_version={self.schema_version!r}, "
            f"algorithm={self.algorithm!r})"
        )

    def to_dict(self) -> EncryptedSecretEnvelopeData:
        """Serialize using the exact accepted ADR field set."""
        return {
            "algorithm": self.algorithm,
            "authentication_data": b64encode(self.authentication_data).decode("ascii"),
            "ciphertext": b64encode(self.ciphertext).decode("ascii"),
            "credential_id": str(self.credential_id),
            "key_version": self.key_version,
            "nonce": b64encode(self.nonce).decode("ascii"),
            "schema_version": self.schema_version,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> Self:
        """Deserialize and strictly validate an encrypted envelope."""
        expected_fields = set(EncryptedSecretEnvelopeData.__required_keys__)
        if set(data) != expected_fields:
            raise ValueError("EncryptedSecretEnvelope fields are invalid")
        model_name = "EncryptedSecretEnvelope"
        credential_id = _required(data, "credential_id", model_name)
        if not isinstance(credential_id, str):
            raise TypeError("EncryptedSecretEnvelope credential_id must be a UUID string")
        algorithm = _required(data, "algorithm", model_name)
        if not isinstance(algorithm, str):
            raise TypeError("EncryptedSecretEnvelope algorithm must be a string")
        return cls(
            credential_id=VaultCredentialId.from_string(credential_id),
            ciphertext=_decode_binary(_required(data, "ciphertext", model_name), "ciphertext"),
            nonce=_decode_binary(_required(data, "nonce", model_name), "nonce"),
            authentication_data=_decode_binary(
                _required(data, "authentication_data", model_name), "authentication_data"
            ),
            key_version=_positive_int(
                _required(data, "key_version", model_name), "key_version", model_name
            ),
            schema_version=_positive_int(
                _required(data, "schema_version", model_name), "schema_version", model_name
            ),
            algorithm=algorithm,
        )


@dataclass(frozen=True, slots=True, repr=False)
class StagedSecret:
    """One encrypted replacement candidate tied to authoritative state."""

    handle: StagedSecretHandle
    credential_id: VaultCredentialId
    expected_revision: int
    envelope: EncryptedSecretEnvelope = field(repr=False)

    def __post_init__(self) -> None:
        """Validate staged metadata without exposing encrypted material."""
        if not isinstance(self.handle, StagedSecretHandle):
            raise TypeError("StagedSecret handle must be a StagedSecretHandle")
        if not isinstance(self.credential_id, VaultCredentialId):
            raise TypeError("StagedSecret credential_id must be a VaultCredentialId")
        _positive_int(self.expected_revision, "expected_revision", "StagedSecret")
        if not isinstance(self.envelope, EncryptedSecretEnvelope):
            raise TypeError("StagedSecret envelope must be an EncryptedSecretEnvelope")
        if self.envelope.credential_id.value != self.handle.value:
            raise ValueError("StagedSecret envelope identity does not match its handle")

    def __repr__(self) -> str:
        """Return only safe staging metadata."""
        return (
            f"{type(self).__name__}(handle={self.handle!r}, "
            f"credential_id={self.credential_id!r}, "
            f"expected_revision={self.expected_revision!r}, envelope=<redacted>)"
        )

    def to_dict(self) -> StagedSecretData:
        """Serialize the encrypted staged record for private Vault storage."""
        return {
            "credential_id": str(self.credential_id),
            "envelope": self.envelope.to_dict(),
            "expected_revision": self.expected_revision,
        }

    @classmethod
    def from_dict(cls, handle: StagedSecretHandle, data: Mapping[str, object]) -> Self:
        """Deserialize and strictly validate an encrypted staged record."""
        if set(data) != set(StagedSecretData.__required_keys__):
            raise ValueError("StagedSecret fields are invalid")
        credential_id = _required(data, "credential_id", "StagedSecret")
        envelope = _required(data, "envelope", "StagedSecret")
        if not isinstance(credential_id, str):
            raise TypeError("StagedSecret credential_id must be a UUID string")
        if not isinstance(envelope, Mapping):
            raise TypeError("StagedSecret envelope must be a mapping")
        return cls(
            handle=handle,
            credential_id=VaultCredentialId.from_string(credential_id),
            expected_revision=_positive_int(
                _required(data, "expected_revision", "StagedSecret"),
                "expected_revision",
                "StagedSecret",
            ),
            envelope=EncryptedSecretEnvelope.from_dict(envelope),
        )


@dataclass(frozen=True, slots=True)
class VaultPromotionReceipt:
    """Safe idempotency receipt for a completed Vault promotion."""

    handle: StagedSecretHandle
    credential_id: VaultCredentialId
    revision: int

    def __post_init__(self) -> None:
        """Validate only opaque identifiers and a positive revision."""
        if not isinstance(self.handle, StagedSecretHandle):
            raise TypeError("VaultPromotionReceipt handle must be a StagedSecretHandle")
        if not isinstance(self.credential_id, VaultCredentialId):
            raise TypeError("VaultPromotionReceipt credential_id must be a VaultCredentialId")
        _positive_int(self.revision, "revision", "VaultPromotionReceipt")

    def to_dict(self) -> VaultPromotionReceiptData:
        """Serialize non-secret promotion evidence."""
        return {"credential_id": str(self.credential_id), "revision": self.revision}

    @classmethod
    def from_dict(cls, handle: StagedSecretHandle, data: Mapping[str, object]) -> Self:
        """Deserialize and validate non-secret promotion evidence."""
        if set(data) != set(VaultPromotionReceiptData.__required_keys__):
            raise ValueError("VaultPromotionReceipt fields are invalid")
        credential_id = _required(data, "credential_id", "VaultPromotionReceipt")
        if not isinstance(credential_id, str):
            raise TypeError("VaultPromotionReceipt credential_id must be a UUID string")
        return cls(
            handle=handle,
            credential_id=VaultCredentialId.from_string(credential_id),
            revision=_positive_int(
                _required(data, "revision", "VaultPromotionReceipt"),
                "revision",
                "VaultPromotionReceipt",
            ),
        )


def _utcnow() -> datetime:
    """Return the current UTC time."""
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class CredentialMetadata:
    """Non-secret relationship metadata for a future credential."""

    credential_id: VaultCredentialId
    person_id: UUID
    access_method: AccessMethod = AccessMethod.PIN
    enabled: bool = True
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)

    def __post_init__(self) -> None:
        """Validate and normalize credential metadata."""
        if not isinstance(self.credential_id, VaultCredentialId):
            raise TypeError("CredentialMetadata credential_id must be a VaultCredentialId")
        if not isinstance(self.person_id, UUID):
            raise TypeError("CredentialMetadata person_id must be a UUID")
        if not isinstance(self.access_method, AccessMethod):
            raise TypeError("CredentialMetadata access_method must be an AccessMethod")
        if not isinstance(self.enabled, bool):
            raise TypeError("CredentialMetadata enabled must be a boolean")
        created_at = _normalize_datetime(self.created_at, "created_at", "CredentialMetadata")
        updated_at = _normalize_datetime(self.updated_at, "updated_at", "CredentialMetadata")
        if updated_at < created_at:
            raise ValueError("CredentialMetadata updated_at must not be earlier than created_at")
        object.__setattr__(self, "created_at", created_at)
        object.__setattr__(self, "updated_at", updated_at)

    def to_dict(self) -> CredentialMetadataData:
        """Serialize credential metadata to JSON-compatible data."""
        return {
            "credential_id": str(self.credential_id),
            "person_id": str(self.person_id),
            "access_method": self.access_method.value,
            "enabled": self.enabled,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> Self:
        """Deserialize and validate non-secret credential metadata."""
        model_name = "CredentialMetadata"
        credential_id = _required(data, "credential_id", model_name)
        person_id = _required(data, "person_id", model_name)
        if not isinstance(credential_id, str):
            raise TypeError("CredentialMetadata credential_id must be a UUID string")
        if not isinstance(person_id, str):
            raise TypeError("CredentialMetadata person_id must be a UUID string")
        try:
            parsed_person_id = UUID(person_id)
        except ValueError as err:
            raise ValueError("CredentialMetadata person_id must be a valid UUID") from err
        return cls(
            credential_id=VaultCredentialId.from_string(credential_id),
            person_id=parsed_person_id,
            access_method=_parse_access_method(_required(data, "access_method", model_name)),
            enabled=_required_bool(_required(data, "enabled", model_name)),
            created_at=_parse_datetime(
                _required(data, "created_at", model_name), "created_at", model_name
            ),
            updated_at=_parse_datetime(
                _required(data, "updated_at", model_name), "updated_at", model_name
            ),
        )


def _required_bool(value: object) -> bool:
    """Validate a serialized boolean."""
    if not isinstance(value, bool):
        raise TypeError("CredentialMetadata enabled must be a boolean")
    return value
