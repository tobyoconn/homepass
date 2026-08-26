"""Non-secret access synchronization metadata."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Self, TypedDict
from uuid import UUID

from ..vault.identifiers import VaultCredentialId
from .synchronization import SynchronizationStatus


class AccessDriver(StrEnum):
    """Driver identifiers persisted with access metadata."""

    ZWAVE_JS = "zwave_js"
    NUKI = "nuki"
    HOMEPASS_KEYPAD = "homepass_keypad"


class AccessMetadataData(TypedDict):
    """JSON-compatible non-secret access metadata."""

    person_id: str
    access_point_id: str
    driver: str
    lock_entity_id: str
    slot: int
    synchronization_status: str
    vault_credential_id: str | None
    credential_revision: int
    created_at: str
    updated_at: str


def _utcnow() -> datetime:
    """Return the current UTC time."""
    return datetime.now(UTC)


def _required(data: Mapping[str, object], field_name: str) -> object:
    """Return a required serialized field."""
    try:
        return data[field_name]
    except KeyError as err:
        raise ValueError(f"Missing required AccessMetadata field: {field_name}") from err


def _parse_uuid(value: object, field_name: str) -> UUID:
    """Parse a UUID without echoing malformed input."""
    if not isinstance(value, str):
        raise TypeError(f"AccessMetadata {field_name} must be a UUID string")
    try:
        return UUID(value)
    except ValueError as err:
        raise ValueError(f"AccessMetadata {field_name} must be a valid UUID") from err


def _parse_datetime(value: object, field_name: str) -> datetime:
    """Parse a serialized datetime."""
    if not isinstance(value, str):
        raise TypeError(f"AccessMetadata {field_name} must be an ISO 8601 string")
    try:
        return datetime.fromisoformat(value)
    except ValueError as err:
        raise ValueError(f"AccessMetadata {field_name} must be a valid ISO 8601 datetime") from err


def _normalize_datetime(value: datetime, field_name: str) -> datetime:
    """Validate a datetime and normalize it to UTC."""
    if not isinstance(value, datetime):
        raise TypeError(f"AccessMetadata {field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"AccessMetadata {field_name} must be timezone-aware")
    return value.astimezone(UTC)


def _parse_enum[EnumT: StrEnum](
    enum_type: type[EnumT],
    value: object,
    field_name: str,
) -> EnumT:
    """Parse a string enum without echoing malformed input."""
    if not isinstance(value, str):
        raise TypeError(f"AccessMetadata {field_name} must be a string")
    try:
        return enum_type(value)
    except ValueError as err:
        raise ValueError(f"AccessMetadata {field_name} is unsupported") from err


def _positive_slot(value: object) -> int:
    """Validate a positive non-boolean lock slot."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError("AccessMetadata slot must be an integer")
    if value < 1:
        raise ValueError("AccessMetadata slot must be positive")
    return value


def _positive_revision(value: object) -> int:
    """Validate a positive non-boolean credential revision."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError("AccessMetadata credential_revision must be an integer")
    if value < 1:
        raise ValueError("AccessMetadata credential_revision must be positive")
    return value


@dataclass(frozen=True, slots=True)
class AccessMetadata:
    """Persisted non-secret relationship between a Person and physical access."""

    person_id: UUID
    access_point_id: UUID
    driver: AccessDriver
    lock_entity_id: str
    slot: int
    synchronization_status: SynchronizationStatus
    vault_credential_id: VaultCredentialId | None = None
    credential_revision: int = 1
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)

    def __post_init__(self) -> None:
        """Validate and normalize access metadata."""
        if not isinstance(self.person_id, UUID):
            raise TypeError("AccessMetadata person_id must be a UUID")
        if not isinstance(self.access_point_id, UUID):
            raise TypeError("AccessMetadata access_point_id must be a UUID")
        if not isinstance(self.driver, AccessDriver):
            raise TypeError("AccessMetadata driver must be an AccessDriver")
        if not isinstance(self.lock_entity_id, str):
            raise TypeError("AccessMetadata lock_entity_id must be a string")
        lock_entity_id = self.lock_entity_id.strip()
        if self.driver is AccessDriver.ZWAVE_JS:
            valid_target = lock_entity_id.startswith("lock.") and len(lock_entity_id) > len("lock.")
        else:
            valid_target = "." in lock_entity_id and all(lock_entity_id.split(".", 1))
        if not valid_target:
            raise ValueError("AccessMetadata target entity ID is invalid")
        _positive_slot(self.slot)
        if not isinstance(self.synchronization_status, SynchronizationStatus):
            raise TypeError("AccessMetadata synchronization_status must be a SynchronizationStatus")
        if self.vault_credential_id is not None and not isinstance(
            self.vault_credential_id, VaultCredentialId
        ):
            raise TypeError("AccessMetadata vault_credential_id must be a VaultCredentialId")
        _positive_revision(self.credential_revision)
        created_at = _normalize_datetime(self.created_at, "created_at")
        updated_at = _normalize_datetime(self.updated_at, "updated_at")
        if updated_at < created_at:
            raise ValueError("AccessMetadata updated_at must not be earlier than created_at")
        object.__setattr__(self, "lock_entity_id", lock_entity_id)
        object.__setattr__(self, "created_at", created_at)
        object.__setattr__(self, "updated_at", updated_at)

    def to_dict(self) -> AccessMetadataData:
        """Serialize access metadata without credential material."""
        return {
            "person_id": str(self.person_id),
            "access_point_id": str(self.access_point_id),
            "driver": self.driver.value,
            "lock_entity_id": self.lock_entity_id,
            "slot": self.slot,
            "synchronization_status": self.synchronization_status.value,
            "vault_credential_id": (
                str(self.vault_credential_id) if self.vault_credential_id is not None else None
            ),
            "credential_revision": self.credential_revision,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> Self:
        """Deserialize and validate access metadata."""
        return cls(
            person_id=_parse_uuid(_required(data, "person_id"), "person_id"),
            access_point_id=_parse_uuid(_required(data, "access_point_id"), "access_point_id"),
            driver=_parse_enum(AccessDriver, _required(data, "driver"), "driver"),
            lock_entity_id=_required_string(_required(data, "lock_entity_id")),
            slot=_positive_slot(_required(data, "slot")),
            synchronization_status=_parse_enum(
                SynchronizationStatus,
                _required(data, "synchronization_status"),
                "synchronization_status",
            ),
            vault_credential_id=_optional_vault_credential_id(data.get("vault_credential_id")),
            credential_revision=_positive_revision(data.get("credential_revision", 1)),
            created_at=_parse_datetime(_required(data, "created_at"), "created_at"),
            updated_at=_parse_datetime(_required(data, "updated_at"), "updated_at"),
        )


def _required_string(value: object) -> str:
    """Validate a serialized lock entity ID string."""
    if not isinstance(value, str):
        raise TypeError("AccessMetadata lock_entity_id must be a string")
    return value


def _optional_vault_credential_id(value: object) -> VaultCredentialId | None:
    """Parse an optional vault identifier for legacy access records."""
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError("AccessMetadata vault_credential_id must be a UUID string")
    return VaultCredentialId.from_string(value)
