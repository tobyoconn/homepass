"""Access Point domain model."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Self, TypedDict
from uuid import UUID, uuid4


class AccessPointData(TypedDict):
    """JSON-compatible representation of an access point."""

    id: str
    display_name: str
    enabled: bool
    created_at: str
    updated_at: str
    open_enabled: bool
    entry_action: str


def _utcnow() -> datetime:
    """Return the current UTC time."""
    return datetime.now(UTC)


def _required(data: Mapping[str, object], field_name: str) -> object:
    """Return a required serialized field."""
    try:
        return data[field_name]
    except KeyError as err:
        raise ValueError(f"Missing required AccessPoint field: {field_name}") from err


def _parse_uuid(value: object) -> UUID:
    """Parse a serialized UUID."""
    if not isinstance(value, str):
        raise TypeError("AccessPoint id must be a UUID string")
    try:
        return UUID(value)
    except ValueError as err:
        raise ValueError("AccessPoint id must be a valid UUID") from err


def _parse_datetime(value: object, field_name: str) -> datetime:
    """Parse a serialized datetime."""
    if not isinstance(value, str):
        raise TypeError(f"AccessPoint {field_name} must be an ISO 8601 string")
    try:
        return datetime.fromisoformat(value)
    except ValueError as err:
        raise ValueError(f"AccessPoint {field_name} must be a valid ISO 8601 datetime") from err


def _require_string(value: object, field_name: str) -> str:
    """Validate a serialized string."""
    if not isinstance(value, str):
        raise TypeError(f"AccessPoint {field_name} must be a string")
    return value


def _require_bool(value: object, field_name: str) -> bool:
    """Validate a serialized boolean."""
    if not isinstance(value, bool):
        raise TypeError(f"AccessPoint {field_name} must be a boolean")
    return value


def _normalize_datetime(value: datetime, field_name: str) -> datetime:
    """Validate a datetime and normalize it to UTC."""
    if not isinstance(value, datetime):
        raise TypeError(f"AccessPoint {field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"AccessPoint {field_name} must be timezone-aware")
    return value.astimezone(UTC)


@dataclass(frozen=True, slots=True)
class AccessPoint:
    """An immutable place or entry boundary where access is controlled."""

    display_name: str
    id: UUID = field(default_factory=uuid4)
    enabled: bool = True
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)
    open_enabled: bool = False
    entry_action: str = "unlock"

    def __post_init__(self) -> None:
        """Validate and normalize the access point."""
        if not isinstance(self.id, UUID):
            raise TypeError("AccessPoint id must be a UUID")
        if not isinstance(self.display_name, str):
            raise TypeError("AccessPoint display_name must be a string")

        display_name = self.display_name.strip()
        if not display_name:
            raise ValueError("AccessPoint display_name must not be empty")
        if not isinstance(self.enabled, bool):
            raise TypeError("AccessPoint enabled must be a boolean")

        if not isinstance(self.open_enabled, bool):
            raise TypeError("Open permission must be a boolean")
        if self.entry_action not in {"unlock", "open"}:
            raise ValueError("Entry action must be unlock or open")
        if self.entry_action == "open" and not self.open_enabled:
            raise ValueError("Open Door must be enabled before using it for entry")

        created_at = _normalize_datetime(self.created_at, "created_at")
        updated_at = _normalize_datetime(self.updated_at, "updated_at")
        if updated_at < created_at:
            raise ValueError("AccessPoint updated_at must not be earlier than created_at")

        object.__setattr__(self, "display_name", display_name)
        object.__setattr__(self, "created_at", created_at)
        object.__setattr__(self, "updated_at", updated_at)

    def to_dict(self) -> AccessPointData:
        """Serialize the access point to JSON-compatible data."""
        return {
            "id": str(self.id),
            "display_name": self.display_name,
            "enabled": self.enabled,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "open_enabled": self.open_enabled,
            "entry_action": self.entry_action,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> Self:
        """Deserialize and validate an access point."""
        return cls(
            open_enabled=_require_bool(data.get("open_enabled", False), "open_enabled"),
            entry_action=_require_string(data.get("entry_action", "unlock"), "entry_action"),
            id=_parse_uuid(_required(data, "id")),
            display_name=_require_string(_required(data, "display_name"), "display_name"),
            enabled=_require_bool(_required(data, "enabled"), "enabled"),
            created_at=_parse_datetime(_required(data, "created_at"), "created_at"),
            updated_at=_parse_datetime(_required(data, "updated_at"), "updated_at"),
        )
