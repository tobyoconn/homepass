"""Durable homeowner-facing synchronization history events."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Self, TypedDict
from uuid import UUID


class SynchronizationHistoryEventType(StrEnum):
    """Stable synchronization event categories."""

    PROVISIONING_STARTED = "provisioning_started"
    PROVISIONING_COMPLETED = "provisioning_completed"
    PROVISIONING_FAILED = "provisioning_failed"
    CREDENTIAL_REPLACEMENT_STARTED = "credential_replacement_started"
    CREDENTIAL_REPLACEMENT_COMPLETED = "credential_replacement_completed"
    CREDENTIAL_REPLACEMENT_FAILED = "credential_replacement_failed"
    VERIFICATION_SUCCEEDED = "verification_succeeded"
    VERIFICATION_PENDING = "verification_pending"
    VERIFICATION_FAILED = "verification_failed"
    RECOVERY_STARTED = "recovery_started"
    RECOVERY_COMPLETED = "recovery_completed"
    RECOVERY_FAILED = "recovery_failed"
    RETRY_REQUIRED = "retry_required"
    MANUAL_ATTENTION_REQUIRED = "manual_attention_required"
    SYNCHRONIZATION_RESTORED = "synchronization_restored"


class SynchronizationHistorySeverity(StrEnum):
    """Stable severity carried by one history event."""

    SUCCESS = "success"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class SynchronizationHistoryEventData(TypedDict):
    """JSON-compatible synchronization history record."""

    event_id: str
    person_id: str
    access_point_id: str
    occurred_at: str
    event_type: str
    severity: str
    title: str
    description: str


@dataclass(frozen=True, slots=True)
class SynchronizationHistoryEvent:
    """One immutable event for a Person-to-Door relationship."""

    event_id: UUID
    person_id: UUID
    access_point_id: UUID
    occurred_at: datetime
    event_type: SynchronizationHistoryEventType
    severity: SynchronizationHistorySeverity
    title: str
    description: str

    def __post_init__(self) -> None:
        for name in ("event_id", "person_id", "access_point_id"):
            if not isinstance(getattr(self, name), UUID):
                raise TypeError(f"Synchronization history {name} must be a UUID")
        if not isinstance(self.occurred_at, datetime):
            raise TypeError("Synchronization history timestamp must be a datetime")
        if self.occurred_at.tzinfo is None or self.occurred_at.utcoffset() is None:
            raise ValueError("Synchronization history timestamp must be timezone-aware")
        object.__setattr__(self, "occurred_at", self.occurred_at.astimezone(UTC))
        if not isinstance(self.event_type, SynchronizationHistoryEventType):
            raise TypeError("Synchronization history event type is invalid")
        if not isinstance(self.severity, SynchronizationHistorySeverity):
            raise TypeError("Synchronization history severity is invalid")
        if not isinstance(self.title, str) or not self.title.strip():
            raise ValueError("Synchronization history title must not be empty")
        if not isinstance(self.description, str) or not self.description.strip():
            raise ValueError("Synchronization history description must not be empty")

    def to_dict(self) -> SynchronizationHistoryEventData:
        """Serialize the durable event."""
        return {
            "event_id": str(self.event_id),
            "person_id": str(self.person_id),
            "access_point_id": str(self.access_point_id),
            "occurred_at": self.occurred_at.isoformat(),
            "event_type": self.event_type.value,
            "severity": self.severity.value,
            "title": self.title,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> Self:
        """Deserialize and validate one event."""
        try:
            values = (
                data["event_id"],
                data["person_id"],
                data["access_point_id"],
                data["occurred_at"],
                data["event_type"],
                data["severity"],
                data["title"],
                data["description"],
            )
        except KeyError as err:
            raise ValueError("Invalid serialized synchronization history event") from err

        def string(value: object) -> str:
            if not isinstance(value, str):
                raise TypeError("Synchronization history fields must be strings")
            return value

        (
            event_id,
            person_id,
            access_point_id,
            occurred_at,
            event_type,
            severity,
            title,
            description,
        ) = (string(value) for value in values)
        try:
            return cls(
                UUID(event_id),
                UUID(person_id),
                UUID(access_point_id),
                datetime.fromisoformat(occurred_at),
                SynchronizationHistoryEventType(event_type),
                SynchronizationHistorySeverity(severity),
                title,
                description,
            )
        except ValueError as err:
            raise ValueError("Invalid serialized synchronization history event") from err


__all__ = [
    "SynchronizationHistoryEvent",
    "SynchronizationHistoryEventData",
    "SynchronizationHistoryEventType",
    "SynchronizationHistorySeverity",
]
