"""Person domain model."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Self, TypedDict
from uuid import UUID, uuid4

from .schedule import PERMANENT_SCHEDULE_ID

MAX_PERSON_DESCRIPTION_LENGTH = 160


class PersonData(TypedDict):
    """JSON-compatible representation of a person."""

    person_id: str
    schedule_id: str
    display_name: str
    description: str | None
    enabled: bool
    notes: str | None
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
        raise ValueError(f"Missing required Person field: {field_name}") from err


def _parse_uuid(value: object, field_name: str) -> UUID:
    """Parse a serialized UUID."""
    if not isinstance(value, str):
        raise TypeError(f"Person {field_name} must be a UUID string")
    try:
        return UUID(value)
    except ValueError as err:
        raise ValueError(f"Person {field_name} must be a valid UUID") from err


def _parse_datetime(value: object, field_name: str) -> datetime:
    """Parse a serialized datetime."""
    if not isinstance(value, str):
        raise TypeError(f"Person {field_name} must be an ISO 8601 string")
    try:
        return datetime.fromisoformat(value)
    except ValueError as err:
        raise ValueError(f"Person {field_name} must be a valid ISO 8601 datetime") from err


def _require_string(value: object, field_name: str) -> str:
    """Validate a serialized string."""
    if not isinstance(value, str):
        raise TypeError(f"Person {field_name} must be a string")
    return value


def _require_bool(value: object, field_name: str) -> bool:
    """Validate a serialized boolean."""
    if not isinstance(value, bool):
        raise TypeError(f"Person {field_name} must be a boolean")
    return value


def _optional_string(value: object, field_name: str) -> str | None:
    """Validate a serialized optional string."""
    if value is not None and not isinstance(value, str):
        raise TypeError(f"Person {field_name} must be a string or null")
    return value


def _normalize_datetime(value: datetime, field_name: str) -> datetime:
    """Validate a datetime and normalize it to UTC."""
    if not isinstance(value, datetime):
        raise TypeError(f"Person {field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"Person {field_name} must be timezone-aware")
    return value.astimezone(UTC)


@dataclass(frozen=True, slots=True)
class Person:
    """An immutable person managed by HomePASS."""

    display_name: str
    person_id: UUID = field(default_factory=uuid4)
    schedule_id: UUID = PERMANENT_SCHEDULE_ID
    enabled: bool = True
    description: str | None = None
    notes: str | None = None
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)

    def __post_init__(self) -> None:
        """Validate and normalize the person."""
        if not isinstance(self.person_id, UUID):
            raise TypeError("Person person_id must be a UUID")
        if not isinstance(self.schedule_id, UUID):
            raise TypeError("Person schedule_id must be a UUID")
        if not isinstance(self.display_name, str):
            raise TypeError("Person display_name must be a string")

        display_name = self.display_name.strip()
        if not display_name:
            raise ValueError("Person display_name must not be empty")
        if not isinstance(self.enabled, bool):
            raise TypeError("Person enabled must be a boolean")
        if self.description is not None and not isinstance(self.description, str):
            raise TypeError("Person description must be a string or None")
        description = None if self.description is None else self.description.strip()
        if description == "":
            description = None
        if description is not None and len(description) > MAX_PERSON_DESCRIPTION_LENGTH:
            raise ValueError(
                f"Person description must not exceed {MAX_PERSON_DESCRIPTION_LENGTH} characters"
            )
        if self.notes is not None and not isinstance(self.notes, str):
            raise TypeError("Person notes must be a string or None")

        created_at = _normalize_datetime(self.created_at, "created_at")
        updated_at = _normalize_datetime(self.updated_at, "updated_at")
        if updated_at < created_at:
            raise ValueError("Person updated_at must not be earlier than created_at")

        object.__setattr__(self, "display_name", display_name)
        object.__setattr__(self, "description", description)
        object.__setattr__(self, "created_at", created_at)
        object.__setattr__(self, "updated_at", updated_at)

    def to_dict(self) -> PersonData:
        """Serialize the person to JSON-compatible data."""
        return {
            "person_id": str(self.person_id),
            "schedule_id": str(self.schedule_id),
            "display_name": self.display_name,
            "description": self.description,
            "enabled": self.enabled,
            "notes": self.notes,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> Self:
        """Deserialize and validate a person."""
        return cls(
            person_id=_parse_uuid(_required(data, "person_id"), "person_id"),
            schedule_id=_parse_uuid(_required(data, "schedule_id"), "schedule_id"),
            display_name=_require_string(_required(data, "display_name"), "display_name"),
            description=_optional_string(data.get("description"), "description"),
            enabled=_require_bool(_required(data, "enabled"), "enabled"),
            notes=_optional_string(_required(data, "notes"), "notes"),
            created_at=_parse_datetime(_required(data, "created_at"), "created_at"),
            updated_at=_parse_datetime(_required(data, "updated_at"), "updated_at"),
        )
