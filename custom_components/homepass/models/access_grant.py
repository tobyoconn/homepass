"""Access Grant domain model."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Self, TypedDict
from uuid import UUID, uuid4

from .schedule import PERMANENT_SCHEDULE_ID
from .synchronization import SynchronizationStatus


class AccessGrantData(TypedDict):
    """JSON-compatible representation of an access grant."""

    access_grant_id: str
    person_id: str
    credential_id: str
    access_point_id: str
    schedule_id: str
    enabled: bool
    created_at: str
    updated_at: str
    synchronization_status: str


def _utcnow() -> datetime:
    """Return the current UTC time."""
    return datetime.now(UTC)


def _required(data: Mapping[str, object], field_name: str) -> object:
    """Return a required serialized field."""
    try:
        return data[field_name]
    except KeyError as err:
        raise ValueError(f"Missing required AccessGrant field: {field_name}") from err


def _parse_uuid(value: object, field_name: str) -> UUID:
    """Parse a serialized UUID."""
    if not isinstance(value, str):
        raise TypeError(f"AccessGrant {field_name} must be a UUID string")
    try:
        return UUID(value)
    except ValueError as err:
        raise ValueError(f"AccessGrant {field_name} must be a valid UUID") from err


def _parse_datetime(value: object, field_name: str) -> datetime:
    """Parse a serialized datetime."""
    if not isinstance(value, str):
        raise TypeError(f"AccessGrant {field_name} must be an ISO 8601 string")
    try:
        return datetime.fromisoformat(value)
    except ValueError as err:
        raise ValueError(f"AccessGrant {field_name} must be a valid ISO 8601 datetime") from err


def _require_bool(value: object, field_name: str) -> bool:
    """Validate a serialized boolean."""
    if not isinstance(value, bool):
        raise TypeError(f"AccessGrant {field_name} must be a boolean")
    return value


def _normalize_datetime(value: datetime, field_name: str) -> datetime:
    """Validate a datetime and normalize it to UTC."""
    if not isinstance(value, datetime):
        raise TypeError(f"AccessGrant {field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"AccessGrant {field_name} must be timezone-aware")
    return value.astimezone(UTC)


@dataclass(frozen=True, slots=True)
class AccessGrant:
    """An immutable grant connecting a person to an access point and credential."""

    person_id: UUID
    credential_id: UUID
    access_point_id: UUID
    access_grant_id: UUID = field(default_factory=uuid4)
    schedule_id: UUID = PERMANENT_SCHEDULE_ID
    enabled: bool = True
    synchronization_status: SynchronizationStatus = SynchronizationStatus.UNKNOWN
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)

    def __post_init__(self) -> None:
        """Validate and normalize the access grant."""
        for field_name in (
            "access_grant_id",
            "person_id",
            "credential_id",
            "access_point_id",
        ):
            if not isinstance(getattr(self, field_name), UUID):
                raise TypeError(f"AccessGrant {field_name} must be a UUID")
        if not isinstance(self.schedule_id, UUID):
            raise TypeError("AccessGrant schedule_id must be a UUID")
        if not isinstance(self.enabled, bool):
            raise TypeError("AccessGrant enabled must be a boolean")
        if not isinstance(self.synchronization_status, SynchronizationStatus):
            raise TypeError("AccessGrant synchronization_status must be a SynchronizationStatus")

        created_at = _normalize_datetime(self.created_at, "created_at")
        updated_at = _normalize_datetime(self.updated_at, "updated_at")
        if updated_at < created_at:
            raise ValueError("AccessGrant updated_at must not be earlier than created_at")

        object.__setattr__(self, "created_at", created_at)
        object.__setattr__(self, "updated_at", updated_at)

    def to_dict(self) -> AccessGrantData:
        """Serialize the access grant to JSON-compatible data."""
        return {
            "access_grant_id": str(self.access_grant_id),
            "person_id": str(self.person_id),
            "credential_id": str(self.credential_id),
            "access_point_id": str(self.access_point_id),
            "schedule_id": str(self.schedule_id),
            "enabled": self.enabled,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "synchronization_status": self.synchronization_status.value,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> Self:
        """Deserialize and validate an access grant."""
        return cls(
            access_grant_id=_parse_uuid(_required(data, "access_grant_id"), "access_grant_id"),
            person_id=_parse_uuid(_required(data, "person_id"), "person_id"),
            credential_id=_parse_uuid(_required(data, "credential_id"), "credential_id"),
            access_point_id=_parse_uuid(_required(data, "access_point_id"), "access_point_id"),
            schedule_id=_parse_uuid(_required(data, "schedule_id"), "schedule_id"),
            enabled=_require_bool(_required(data, "enabled"), "enabled"),
            created_at=_parse_datetime(_required(data, "created_at"), "created_at"),
            updated_at=_parse_datetime(_required(data, "updated_at"), "updated_at"),
            synchronization_status=_parse_synchronization_status(
                data.get("synchronization_status", SynchronizationStatus.UNKNOWN.value)
            ),
        )


def _parse_synchronization_status(value: object) -> SynchronizationStatus:
    """Parse a persisted synchronization state without reflecting invalid input."""
    if not isinstance(value, str):
        raise TypeError("AccessGrant synchronization_status must be a string")
    try:
        return SynchronizationStatus(value)
    except ValueError as err:
        raise ValueError("AccessGrant synchronization_status is unsupported") from err
