"""Canonical immutable HomePASS activity events."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from types import MappingProxyType
from typing import Self, TypedDict
from uuid import UUID

type ActivityAttributeValue = str | int | float | bool

_MAX_TEXT_LENGTH = 100


class ActivityCategory(StrEnum):
    """Stable activity categories."""

    DOOR = "door"
    ACCESS = "access"
    SECURITY = "security"
    CONNECTIVITY = "connectivity"
    ADMINISTRATION = "administration"
    SYNCHRONIZATION = "synchronization"
    MAINTENANCE = "maintenance"


class ActivitySeverity(StrEnum):
    """Stable operational importance independent of UI colour."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class ActivityEventType(StrEnum):
    """Canonical homeowner-relevant factual activity types."""

    DOOR_OPENED = "door_opened"
    DOOR_CLOSED = "door_closed"
    DOOR_LOCKED = "door_locked"
    DOOR_UNLOCKED = "door_unlocked"
    LATCH_RELEASED = "latch_released"
    DOOR_LEFT_OPEN = "door_left_open"
    PIN_FAILED = "pin_failed"
    LOCK_JAMMED = "lock_jammed"
    TAMPER_DETECTED = "tamper_detected"
    DOOR_OFFLINE = "door_offline"
    DOOR_ONLINE = "door_online"
    PERSON_ADDED = "person_added"
    PERSON_UPDATED = "person_updated"
    PERSON_ENABLED = "person_enabled"
    PERSON_DISABLED = "person_disabled"
    PERSON_REMOVED = "person_removed"
    DOOR_ADDED = "door_added"
    DOOR_UPDATED = "door_updated"
    DOOR_ENABLED = "door_enabled"
    DOOR_DISABLED = "door_disabled"
    DOOR_REMOVED = "door_removed"
    ACCESS_GRANTED = "access_granted"
    ACCESS_REVOKED = "access_revoked"
    ACCESS_EXPIRES_SOON = "access_expires_soon"
    ACCESS_EXPIRED = "access_expired"
    SCHEDULE_CREATED = "schedule_created"
    SCHEDULE_UPDATED = "schedule_updated"
    SCHEDULE_REMOVED = "schedule_removed"
    SCHEDULE_CHANGED = "schedule_changed"
    CREDENTIAL_ADDED = "credential_added"
    CREDENTIAL_UPDATED = "credential_updated"
    CREDENTIAL_REMOVED = "credential_removed"
    CREDENTIAL_VERIFICATION_FAILED = "credential_verification_failed"
    CREDENTIAL_VERIFICATION_PENDING = "credential_verification_pending"
    SYNCHRONIZATION_COMPLETED = "synchronization_completed"
    SYNCHRONIZATION_ATTENTION_REQUIRED = "synchronization_attention_required"
    SYNCHRONIZATION_RECOVERED = "synchronization_recovered"
    CONFIGURATION_CHANGED = "configuration_changed"
    CONFIGURATION_ATTENTION_REQUIRED = "configuration_attention_required"
    BATTERY_LOW = "battery_low"
    BATTERY_CRITICAL = "battery_critical"


class ActivityActorType(StrEnum):
    """Truthful actor attribution supported by available evidence."""

    PERSON = "person"
    CREDENTIAL = "credential"
    MANUAL = "manual"
    REMOTE = "remote"
    SYSTEM = "system"
    UNKNOWN = "unknown"


class ActivitySource(StrEnum):
    """Stable source boundary that observed or produced a fact."""

    HOME_PASS = "homepass"
    HOME_ASSISTANT = "home_assistant"
    EXTERNAL = "external"
    UNKNOWN = "unknown"


class ActivityAccessMethod(StrEnum):
    """Sanitized access method when supported by evidence."""

    KEYPAD = "keypad"
    FINGERPRINT = "fingerprint"
    MANUAL = "manual"
    REMOTE = "remote"
    UNKNOWN = "unknown"


class ActivityOutcome(StrEnum):
    """Stable factual outcome where an event has one."""

    SUCCEEDED = "succeeded"
    FAILED = "failed"
    UNKNOWN = "unknown"


class LockEventOrigin(StrEnum):
    """Truthful initiation source for one confirmed lock state transition."""

    HOMEPASS_MANUAL = "homepass_manual"
    HOMEPASS_AUTOMATIC = "homepass_automatic"
    HOMEPASS_KEYPAD = "homepass_keypad"
    NFC_PASSKEY = "nfc_passkey"
    PHYSICAL_AT_DOOR = "physical_at_door"
    UNKNOWN = "unknown"


class ActivityNavigationKind(StrEnum):
    """Approved HomePASS navigation targets."""

    DOOR = "door"
    PERSON = "person"
    ACTIVITY = "activity"


@dataclass(frozen=True, slots=True)
class ActivityEventDefinition:
    """Canonical category, severity, and safe attributes for one event type."""

    category: ActivityCategory
    default_severity: ActivitySeverity
    attribute_types: Mapping[str, type[str] | type[int] | type[float] | type[bool]]


_NO_ATTRIBUTES: Mapping[str, type[str] | type[int] | type[float] | type[bool]] = MappingProxyType(
    {}
)
_LOCK_ATTRIBUTES: Mapping[str, type[str] | type[int] | type[float] | type[bool]] = MappingProxyType(
    {"lock_origin": str}
)
_BATTERY_ATTRIBUTES: Mapping[str, type[str] | type[int] | type[float] | type[bool]] = (
    MappingProxyType({"battery_percentage": int})
)

ACTIVITY_EVENT_DEFINITIONS: Mapping[ActivityEventType, ActivityEventDefinition] = MappingProxyType(
    {
        ActivityEventType.DOOR_OPENED: ActivityEventDefinition(
            ActivityCategory.DOOR, ActivitySeverity.INFO, _NO_ATTRIBUTES
        ),
        ActivityEventType.DOOR_CLOSED: ActivityEventDefinition(
            ActivityCategory.DOOR, ActivitySeverity.INFO, _NO_ATTRIBUTES
        ),
        ActivityEventType.DOOR_LOCKED: ActivityEventDefinition(
            ActivityCategory.DOOR, ActivitySeverity.INFO, _LOCK_ATTRIBUTES
        ),
        ActivityEventType.LATCH_RELEASED: ActivityEventDefinition(
            ActivityCategory.DOOR, ActivitySeverity.INFO, _LOCK_ATTRIBUTES
        ),
        ActivityEventType.DOOR_UNLOCKED: ActivityEventDefinition(
            ActivityCategory.DOOR, ActivitySeverity.INFO, _LOCK_ATTRIBUTES
        ),
        ActivityEventType.DOOR_LEFT_OPEN: ActivityEventDefinition(
            ActivityCategory.DOOR, ActivitySeverity.WARNING, _NO_ATTRIBUTES
        ),
        ActivityEventType.PIN_FAILED: ActivityEventDefinition(
            ActivityCategory.SECURITY,
            ActivitySeverity.WARNING,
            MappingProxyType({"attempt_count": int}),
        ),
        ActivityEventType.LOCK_JAMMED: ActivityEventDefinition(
            ActivityCategory.SECURITY, ActivitySeverity.CRITICAL, _NO_ATTRIBUTES
        ),
        ActivityEventType.TAMPER_DETECTED: ActivityEventDefinition(
            ActivityCategory.SECURITY, ActivitySeverity.CRITICAL, _NO_ATTRIBUTES
        ),
        ActivityEventType.DOOR_OFFLINE: ActivityEventDefinition(
            ActivityCategory.CONNECTIVITY, ActivitySeverity.WARNING, _NO_ATTRIBUTES
        ),
        ActivityEventType.DOOR_ONLINE: ActivityEventDefinition(
            ActivityCategory.CONNECTIVITY, ActivitySeverity.INFO, _NO_ATTRIBUTES
        ),
        ActivityEventType.PERSON_ADDED: ActivityEventDefinition(
            ActivityCategory.ADMINISTRATION, ActivitySeverity.INFO, _NO_ATTRIBUTES
        ),
        ActivityEventType.PERSON_UPDATED: ActivityEventDefinition(
            ActivityCategory.ADMINISTRATION, ActivitySeverity.INFO, _NO_ATTRIBUTES
        ),
        ActivityEventType.PERSON_ENABLED: ActivityEventDefinition(
            ActivityCategory.ADMINISTRATION, ActivitySeverity.INFO, _NO_ATTRIBUTES
        ),
        ActivityEventType.PERSON_DISABLED: ActivityEventDefinition(
            ActivityCategory.ADMINISTRATION, ActivitySeverity.WARNING, _NO_ATTRIBUTES
        ),
        ActivityEventType.PERSON_REMOVED: ActivityEventDefinition(
            ActivityCategory.ADMINISTRATION, ActivitySeverity.INFO, _NO_ATTRIBUTES
        ),
        ActivityEventType.DOOR_ADDED: ActivityEventDefinition(
            ActivityCategory.ADMINISTRATION, ActivitySeverity.INFO, _NO_ATTRIBUTES
        ),
        ActivityEventType.DOOR_UPDATED: ActivityEventDefinition(
            ActivityCategory.ADMINISTRATION, ActivitySeverity.INFO, _NO_ATTRIBUTES
        ),
        ActivityEventType.DOOR_ENABLED: ActivityEventDefinition(
            ActivityCategory.ADMINISTRATION, ActivitySeverity.INFO, _NO_ATTRIBUTES
        ),
        ActivityEventType.DOOR_DISABLED: ActivityEventDefinition(
            ActivityCategory.ADMINISTRATION, ActivitySeverity.WARNING, _NO_ATTRIBUTES
        ),
        ActivityEventType.DOOR_REMOVED: ActivityEventDefinition(
            ActivityCategory.ADMINISTRATION, ActivitySeverity.INFO, _NO_ATTRIBUTES
        ),
        ActivityEventType.ACCESS_GRANTED: ActivityEventDefinition(
            ActivityCategory.ACCESS, ActivitySeverity.INFO, _NO_ATTRIBUTES
        ),
        ActivityEventType.ACCESS_REVOKED: ActivityEventDefinition(
            ActivityCategory.ACCESS, ActivitySeverity.INFO, _NO_ATTRIBUTES
        ),
        ActivityEventType.ACCESS_EXPIRES_SOON: ActivityEventDefinition(
            ActivityCategory.ACCESS, ActivitySeverity.WARNING, _NO_ATTRIBUTES
        ),
        ActivityEventType.ACCESS_EXPIRED: ActivityEventDefinition(
            ActivityCategory.ACCESS, ActivitySeverity.INFO, _NO_ATTRIBUTES
        ),
        ActivityEventType.SCHEDULE_CREATED: ActivityEventDefinition(
            ActivityCategory.ADMINISTRATION,
            ActivitySeverity.INFO,
            MappingProxyType({"schedule_name": str}),
        ),
        ActivityEventType.SCHEDULE_UPDATED: ActivityEventDefinition(
            ActivityCategory.ADMINISTRATION,
            ActivitySeverity.INFO,
            MappingProxyType({"schedule_name": str}),
        ),
        ActivityEventType.SCHEDULE_REMOVED: ActivityEventDefinition(
            ActivityCategory.ADMINISTRATION,
            ActivitySeverity.INFO,
            MappingProxyType({"schedule_name": str}),
        ),
        ActivityEventType.SCHEDULE_CHANGED: ActivityEventDefinition(
            ActivityCategory.ADMINISTRATION,
            ActivitySeverity.INFO,
            MappingProxyType({"schedule_name": str}),
        ),
        ActivityEventType.CREDENTIAL_ADDED: ActivityEventDefinition(
            ActivityCategory.ADMINISTRATION, ActivitySeverity.INFO, _NO_ATTRIBUTES
        ),
        ActivityEventType.CREDENTIAL_UPDATED: ActivityEventDefinition(
            ActivityCategory.ADMINISTRATION, ActivitySeverity.INFO, _NO_ATTRIBUTES
        ),
        ActivityEventType.CREDENTIAL_REMOVED: ActivityEventDefinition(
            ActivityCategory.ADMINISTRATION, ActivitySeverity.INFO, _NO_ATTRIBUTES
        ),
        ActivityEventType.CREDENTIAL_VERIFICATION_FAILED: ActivityEventDefinition(
            ActivityCategory.SYNCHRONIZATION, ActivitySeverity.WARNING, _NO_ATTRIBUTES
        ),
        ActivityEventType.CREDENTIAL_VERIFICATION_PENDING: ActivityEventDefinition(
            ActivityCategory.SYNCHRONIZATION, ActivitySeverity.INFO, _NO_ATTRIBUTES
        ),
        ActivityEventType.SYNCHRONIZATION_COMPLETED: ActivityEventDefinition(
            ActivityCategory.SYNCHRONIZATION, ActivitySeverity.INFO, _NO_ATTRIBUTES
        ),
        ActivityEventType.SYNCHRONIZATION_ATTENTION_REQUIRED: ActivityEventDefinition(
            ActivityCategory.SYNCHRONIZATION, ActivitySeverity.WARNING, _NO_ATTRIBUTES
        ),
        ActivityEventType.SYNCHRONIZATION_RECOVERED: ActivityEventDefinition(
            ActivityCategory.SYNCHRONIZATION, ActivitySeverity.INFO, _NO_ATTRIBUTES
        ),
        ActivityEventType.CONFIGURATION_CHANGED: ActivityEventDefinition(
            ActivityCategory.ADMINISTRATION, ActivitySeverity.INFO, _NO_ATTRIBUTES
        ),
        ActivityEventType.CONFIGURATION_ATTENTION_REQUIRED: ActivityEventDefinition(
            ActivityCategory.ADMINISTRATION, ActivitySeverity.WARNING, _NO_ATTRIBUTES
        ),
        ActivityEventType.BATTERY_LOW: ActivityEventDefinition(
            ActivityCategory.MAINTENANCE, ActivitySeverity.WARNING, _BATTERY_ATTRIBUTES
        ),
        ActivityEventType.BATTERY_CRITICAL: ActivityEventDefinition(
            ActivityCategory.MAINTENANCE, ActivitySeverity.CRITICAL, _BATTERY_ATTRIBUTES
        ),
    }
)

_DOOR_REQUIRED = {
    ActivityEventType.DOOR_OPENED,
    ActivityEventType.DOOR_CLOSED,
    ActivityEventType.DOOR_LOCKED,
    ActivityEventType.DOOR_UNLOCKED,
    ActivityEventType.LATCH_RELEASED,
    ActivityEventType.DOOR_LEFT_OPEN,
    ActivityEventType.PIN_FAILED,
    ActivityEventType.LOCK_JAMMED,
    ActivityEventType.TAMPER_DETECTED,
    ActivityEventType.DOOR_OFFLINE,
    ActivityEventType.DOOR_ONLINE,
    ActivityEventType.DOOR_ADDED,
    ActivityEventType.DOOR_UPDATED,
    ActivityEventType.DOOR_ENABLED,
    ActivityEventType.DOOR_DISABLED,
    ActivityEventType.DOOR_REMOVED,
    ActivityEventType.ACCESS_GRANTED,
    ActivityEventType.ACCESS_REVOKED,
    ActivityEventType.ACCESS_EXPIRES_SOON,
    ActivityEventType.ACCESS_EXPIRED,
    ActivityEventType.SYNCHRONIZATION_COMPLETED,
    ActivityEventType.SYNCHRONIZATION_ATTENTION_REQUIRED,
    ActivityEventType.SYNCHRONIZATION_RECOVERED,
    ActivityEventType.CREDENTIAL_VERIFICATION_FAILED,
    ActivityEventType.CREDENTIAL_VERIFICATION_PENDING,
    ActivityEventType.BATTERY_LOW,
    ActivityEventType.BATTERY_CRITICAL,
}
_PERSON_REQUIRED = {
    ActivityEventType.PERSON_ADDED,
    ActivityEventType.PERSON_UPDATED,
    ActivityEventType.PERSON_ENABLED,
    ActivityEventType.PERSON_DISABLED,
    ActivityEventType.PERSON_REMOVED,
    ActivityEventType.ACCESS_GRANTED,
    ActivityEventType.ACCESS_REVOKED,
    ActivityEventType.ACCESS_EXPIRES_SOON,
    ActivityEventType.ACCESS_EXPIRED,
    ActivityEventType.SCHEDULE_CHANGED,
    ActivityEventType.CREDENTIAL_ADDED,
    ActivityEventType.CREDENTIAL_UPDATED,
    ActivityEventType.CREDENTIAL_REMOVED,
    ActivityEventType.CREDENTIAL_VERIFICATION_FAILED,
}


class ActivityNavigationData(TypedDict):
    """JSON-compatible typed navigation reference."""

    kind: str
    target_id: str


@dataclass(frozen=True, slots=True)
class ActivityNavigationReference:
    """A typed durable HomePASS navigation target, never a raw route."""

    kind: ActivityNavigationKind
    target_id: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.kind, ActivityNavigationKind):
            raise TypeError("Activity navigation kind is invalid")
        if not isinstance(self.target_id, UUID):
            raise TypeError("Activity navigation target_id must be a UUID")

    def to_dict(self) -> ActivityNavigationData:
        return {"kind": self.kind.value, "target_id": str(self.target_id)}

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> Self:
        if set(data) != {"kind", "target_id"}:
            raise ValueError("Activity navigation reference contains unexpected fields")
        kind = data["kind"]
        target_id = data["target_id"]
        if not isinstance(kind, str) or not isinstance(target_id, str):
            raise TypeError("Activity navigation fields must be strings")
        return cls(ActivityNavigationKind(kind), UUID(target_id))


class ActivityEventData(TypedDict):
    """Deterministic JSON-compatible Activity Event record."""

    event_id: str
    occurred_at: str
    recorded_at: str
    event_type: str
    category: str
    severity: str
    source: str
    door_id: str | None
    person_id: str | None
    actor_type: str
    actor_id: str | None
    access_method: str | None
    outcome: str | None
    attributes: dict[str, ActivityAttributeValue]
    navigation: list[ActivityNavigationData]
    correlation_id: str | None
    deduplication_key: str | None
    door_name: str | None
    person_name: str | None
    actor_name: str | None


_ACTIVITY_EVENT_FIELDS = set(ActivityEventData.__annotations__)


def _normalize_timestamp(value: datetime, field_name: str) -> datetime:
    if not isinstance(value, datetime):
        raise TypeError(f"Activity {field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"Activity {field_name} must be timezone-aware")
    return value.astimezone(UTC)


def _clean_text(value: str | None, field_name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError(f"Activity {field_name} must be a string")
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"Activity {field_name} must not be empty")
    if len(cleaned) > _MAX_TEXT_LENGTH or any(ord(character) < 32 for character in cleaned):
        raise ValueError(f"Activity {field_name} is not safe display text")
    return cleaned


def _optional_uuid(value: object, field_name: str) -> UUID | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError(f"Activity {field_name} must be a UUID string")
    return UUID(value)


def _optional_text(value: object, field_name: str) -> str | None:
    if value is not None and not isinstance(value, str):
        raise TypeError(f"Activity {field_name} must be a string")
    return _clean_text(value, field_name)


def _optional_enum[EnumT: StrEnum](
    value: object, enum_type: type[EnumT], field_name: str
) -> EnumT | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError(f"Activity {field_name} must be a string")
    return enum_type(value)


@dataclass(frozen=True, slots=True)
class ActivityEvent:
    """One immutable, canonical, homeowner-relevant factual event."""

    event_id: UUID
    occurred_at: datetime
    recorded_at: datetime
    event_type: ActivityEventType
    category: ActivityCategory
    severity: ActivitySeverity
    source: ActivitySource
    actor_type: ActivityActorType
    door_id: UUID | None = None
    person_id: UUID | None = None
    actor_id: UUID | None = None
    access_method: ActivityAccessMethod | None = None
    outcome: ActivityOutcome | None = None
    attributes: Mapping[str, ActivityAttributeValue] = MappingProxyType({})
    navigation: tuple[ActivityNavigationReference, ...] = ()
    correlation_id: UUID | None = None
    deduplication_key: UUID | None = None
    door_name: str | None = None
    person_name: str | None = None
    actor_name: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.event_id, UUID):
            raise TypeError("Activity event_id must be a UUID")
        object.__setattr__(
            self, "occurred_at", _normalize_timestamp(self.occurred_at, "occurred_at")
        )
        object.__setattr__(
            self, "recorded_at", _normalize_timestamp(self.recorded_at, "recorded_at")
        )
        if not isinstance(self.event_type, ActivityEventType):
            raise TypeError("Activity event_type is invalid")
        if not isinstance(self.category, ActivityCategory):
            raise TypeError("Activity category is invalid")
        if not isinstance(self.severity, ActivitySeverity):
            raise TypeError("Activity severity is invalid")
        if not isinstance(self.source, ActivitySource):
            raise TypeError("Activity source is invalid")
        if not isinstance(self.actor_type, ActivityActorType):
            raise TypeError("Activity actor_type is invalid")
        definition = ACTIVITY_EVENT_DEFINITIONS[self.event_type]
        if (
            self.category is not definition.category
            or self.severity is not definition.default_severity
        ):
            raise ValueError("Activity category and severity must match the canonical event type")

        for field_name in (
            "door_id",
            "person_id",
            "actor_id",
            "correlation_id",
            "deduplication_key",
        ):
            value = getattr(self, field_name)
            if value is not None and not isinstance(value, UUID):
                raise TypeError(f"Activity {field_name} must be a UUID")
        if self.access_method is not None and not isinstance(
            self.access_method, ActivityAccessMethod
        ):
            raise TypeError("Activity access_method is invalid")
        if self.outcome is not None and not isinstance(self.outcome, ActivityOutcome):
            raise TypeError("Activity outcome is invalid")

        door_name = _clean_text(self.door_name, "door_name")
        person_name = _clean_text(self.person_name, "person_name")
        actor_name = _clean_text(self.actor_name, "actor_name")
        object.__setattr__(self, "door_name", door_name)
        object.__setattr__(self, "person_name", person_name)
        object.__setattr__(self, "actor_name", actor_name)
        if (self.door_id is None) != (door_name is None):
            raise ValueError("Activity Door identity and name snapshot must be supplied together")
        if (self.person_id is None) != (person_name is None):
            raise ValueError("Activity Person identity and name snapshot must be supplied together")
        if self.event_type in _DOOR_REQUIRED and self.door_id is None:
            raise ValueError("Activity event type requires a Door")
        if self.event_type in _PERSON_REQUIRED and self.person_id is None:
            raise ValueError("Activity event type requires a Person")

        if self.actor_type is ActivityActorType.PERSON:
            if self.actor_id is None or actor_name is None:
                raise ValueError("Person activity actor requires identity and name evidence")
        elif actor_name is not None:
            raise ValueError("Only a Person actor may carry an actor name")
        elif self.actor_type is not ActivityActorType.CREDENTIAL and self.actor_id is not None:
            raise ValueError("Activity actor identity is not supported for this actor type")
        if self.actor_type is ActivityActorType.CREDENTIAL and self.access_method is None:
            raise ValueError("Credential activity actor requires a supported access method")
        if self.actor_type is ActivityActorType.MANUAL and self.access_method not in {
            None,
            ActivityAccessMethod.MANUAL,
        }:
            raise ValueError("Manual activity actor has a contradictory access method")
        if self.actor_type is ActivityActorType.REMOTE and self.access_method not in {
            None,
            ActivityAccessMethod.REMOTE,
        }:
            raise ValueError("Remote activity actor has a contradictory access method")
        if self.actor_type is ActivityActorType.SYSTEM and self.source in {
            ActivitySource.EXTERNAL,
            ActivitySource.UNKNOWN,
        }:
            raise ValueError("System actor requires a known system source")

        if not isinstance(self.attributes, Mapping):
            raise TypeError("Activity attributes must be a mapping")
        cleaned_attributes: dict[str, ActivityAttributeValue] = {}
        for key, value in self.attributes.items():
            expected_type = definition.attribute_types.get(key)
            if expected_type is None:
                raise ValueError(f"Activity attribute is not allowed for {self.event_type.value}")
            if type(value) is not expected_type:
                raise TypeError(f"Activity attribute {key} has an invalid type")
            if isinstance(value, str):
                cleaned = _clean_text(value, f"attribute {key}")
                if cleaned is None:
                    raise ValueError(f"Activity attribute {key} must not be empty")
                value = cleaned
            elif isinstance(value, float) and not math.isfinite(value):
                raise ValueError(f"Activity attribute {key} must be finite")
            elif isinstance(value, int) and value < 0:
                raise ValueError(f"Activity attribute {key} must not be negative")
            cleaned_attributes[key] = value
        object.__setattr__(
            self, "attributes", MappingProxyType(dict(sorted(cleaned_attributes.items())))
        )
        lock_origin = cleaned_attributes.get("lock_origin")
        if lock_origin is not None:
            if not isinstance(lock_origin, str):
                raise TypeError("Activity lock origin must be a string")
            LockEventOrigin(lock_origin)

        if not isinstance(self.navigation, tuple) or not all(
            isinstance(reference, ActivityNavigationReference) for reference in self.navigation
        ):
            raise TypeError("Activity navigation must be typed references")
        if len({(reference.kind, reference.target_id) for reference in self.navigation}) != len(
            self.navigation
        ):
            raise ValueError("Activity navigation references must be unique")

    def same_fact_as(self, other: ActivityEvent) -> bool:
        """Compare canonical facts while ignoring recording identity and acceptance time."""
        own: dict[str, object] = dict(self.to_dict())
        candidate: dict[str, object] = dict(other.to_dict())
        for field_name in ("event_id", "recorded_at", "deduplication_key"):
            own.pop(field_name)
            candidate.pop(field_name)
        return own == candidate

    @property
    def lock_origin(self) -> LockEventOrigin | None:
        """Return the validated lock origin, or None for legacy and non-lock events."""
        value = self.attributes.get("lock_origin")
        return LockEventOrigin(value) if isinstance(value, str) else None

    def to_dict(self) -> ActivityEventData:
        """Serialize deterministically without rendered homeowner prose."""
        return {
            "event_id": str(self.event_id),
            "occurred_at": self.occurred_at.isoformat(),
            "recorded_at": self.recorded_at.isoformat(),
            "event_type": self.event_type.value,
            "category": self.category.value,
            "severity": self.severity.value,
            "source": self.source.value,
            "door_id": None if self.door_id is None else str(self.door_id),
            "person_id": None if self.person_id is None else str(self.person_id),
            "actor_type": self.actor_type.value,
            "actor_id": None if self.actor_id is None else str(self.actor_id),
            "access_method": None if self.access_method is None else self.access_method.value,
            "outcome": None if self.outcome is None else self.outcome.value,
            "attributes": dict(self.attributes),
            "navigation": [reference.to_dict() for reference in self.navigation],
            "correlation_id": None if self.correlation_id is None else str(self.correlation_id),
            "deduplication_key": (
                None if self.deduplication_key is None else str(self.deduplication_key)
            ),
            "door_name": self.door_name,
            "person_name": self.person_name,
            "actor_name": self.actor_name,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> Self:
        """Deserialize and strictly validate one stored Activity Event."""
        if set(data) != _ACTIVITY_EVENT_FIELDS:
            raise ValueError("Activity event contains unexpected or missing fields")

        def string(field_name: str) -> str:
            value = data[field_name]
            if not isinstance(value, str):
                raise TypeError(f"Activity {field_name} must be a string")
            return value

        raw_attributes = data["attributes"]
        raw_navigation = data["navigation"]
        if not isinstance(raw_attributes, dict) or not isinstance(raw_navigation, list):
            raise TypeError("Activity attributes and navigation have invalid shapes")
        if not all(isinstance(item, dict) for item in raw_navigation):
            raise TypeError("Activity navigation entries must be objects")
        return cls(
            event_id=UUID(string("event_id")),
            occurred_at=datetime.fromisoformat(string("occurred_at")),
            recorded_at=datetime.fromisoformat(string("recorded_at")),
            event_type=ActivityEventType(string("event_type")),
            category=ActivityCategory(string("category")),
            severity=ActivitySeverity(string("severity")),
            source=ActivitySource(string("source")),
            door_id=_optional_uuid(data["door_id"], "door_id"),
            person_id=_optional_uuid(data["person_id"], "person_id"),
            actor_type=ActivityActorType(string("actor_type")),
            actor_id=_optional_uuid(data["actor_id"], "actor_id"),
            access_method=_optional_enum(
                data["access_method"], ActivityAccessMethod, "access_method"
            ),
            outcome=_optional_enum(data["outcome"], ActivityOutcome, "outcome"),
            attributes=raw_attributes,
            navigation=tuple(
                ActivityNavigationReference.from_dict(item) for item in raw_navigation
            ),
            correlation_id=_optional_uuid(data["correlation_id"], "correlation_id"),
            deduplication_key=_optional_uuid(data["deduplication_key"], "deduplication_key"),
            door_name=_optional_text(data["door_name"], "door_name"),
            person_name=_optional_text(data["person_name"], "person_name"),
            actor_name=_optional_text(data["actor_name"], "actor_name"),
        )


def activity_event_definition(event_type: ActivityEventType) -> ActivityEventDefinition:
    """Return the canonical immutable definition for an event type."""
    if not isinstance(event_type, ActivityEventType):
        raise TypeError("Activity event type is invalid")
    return ACTIVITY_EVENT_DEFINITIONS[event_type]


__all__ = [
    "ACTIVITY_EVENT_DEFINITIONS",
    "ActivityAccessMethod",
    "ActivityActorType",
    "ActivityAttributeValue",
    "ActivityCategory",
    "ActivityEvent",
    "ActivityEventData",
    "ActivityEventDefinition",
    "ActivityEventType",
    "ActivityNavigationKind",
    "ActivityNavigationReference",
    "ActivityOutcome",
    "ActivitySeverity",
    "ActivitySource",
    "LockEventOrigin",
    "activity_event_definition",
]
