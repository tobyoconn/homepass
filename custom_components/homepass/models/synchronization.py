"""Canonical HomePASS synchronization status domain model."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Self, TypedDict
from uuid import UUID


class SynchronizationStatus(StrEnum):
    """Stable states answering whether HomePASS and one lock are synchronized."""

    SYNCHRONIZED = "synchronized"
    SYNCHRONIZING = "synchronizing"
    PENDING = "pending"
    RETRY_REQUIRED = "retry_required"
    MANUAL_ATTENTION_REQUIRED = "manual_attention_required"
    UNKNOWN = "unknown"


_STATUS_PRECEDENCE = {
    SynchronizationStatus.SYNCHRONIZED: 0,
    SynchronizationStatus.UNKNOWN: 1,
    SynchronizationStatus.PENDING: 2,
    SynchronizationStatus.SYNCHRONIZING: 3,
    SynchronizationStatus.RETRY_REQUIRED: 4,
    SynchronizationStatus.MANUAL_ATTENTION_REQUIRED: 5,
}


def aggregate_synchronization_status(
    evidence: Iterable[SynchronizationStatus],
) -> SynchronizationStatus:
    """Return the most conservative canonical state supported by current evidence."""
    states = tuple(evidence)
    if not states:
        return SynchronizationStatus.UNKNOWN
    if any(not isinstance(state, SynchronizationStatus) for state in states):
        raise TypeError("Synchronization evidence must contain SynchronizationStatus values")
    return max(states, key=_STATUS_PRECEDENCE.__getitem__)


class AccessPointSynchronizationData(TypedDict):
    """JSON-compatible synchronization status for one managed Access Point."""

    access_point_id: str
    status: str
    last_evaluated_at: str


def _aware_utc(value: datetime, field_name: str) -> datetime:
    """Validate and normalize one timestamp."""
    if not isinstance(value, datetime):
        raise TypeError(f"AccessPointSynchronization {field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"AccessPointSynchronization {field_name} must be timezone-aware")
    return value.astimezone(UTC)


@dataclass(frozen=True, slots=True)
class AccessPointSynchronization:
    """Durable canonical synchronization status for one managed Access Point."""

    access_point_id: UUID
    status: SynchronizationStatus
    last_evaluated_at: datetime

    def __post_init__(self) -> None:
        """Validate identity, status, and timestamp."""
        if not isinstance(self.access_point_id, UUID):
            raise TypeError("AccessPointSynchronization access_point_id must be a UUID")
        if not isinstance(self.status, SynchronizationStatus):
            raise TypeError("AccessPointSynchronization status must be a SynchronizationStatus")
        object.__setattr__(
            self,
            "last_evaluated_at",
            _aware_utc(self.last_evaluated_at, "last_evaluated_at"),
        )

    def to_dict(self) -> AccessPointSynchronizationData:
        """Serialize the durable status without presentation text."""
        return {
            "access_point_id": str(self.access_point_id),
            "status": self.status.value,
            "last_evaluated_at": self.last_evaluated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> Self:
        """Deserialize one validated status record."""
        try:
            raw_access_point_id = data["access_point_id"]
            raw_status = data["status"]
            raw_timestamp = data["last_evaluated_at"]
        except KeyError as err:
            raise ValueError("Invalid serialized AccessPointSynchronization") from err
        if not isinstance(raw_access_point_id, str):
            raise TypeError("AccessPointSynchronization access_point_id must be a UUID string")
        if not isinstance(raw_status, str):
            raise TypeError("AccessPointSynchronization status must be a string")
        if not isinstance(raw_timestamp, str):
            raise TypeError(
                "AccessPointSynchronization last_evaluated_at must be an ISO 8601 string"
            )
        try:
            return cls(
                access_point_id=UUID(raw_access_point_id),
                status=SynchronizationStatus(raw_status),
                last_evaluated_at=datetime.fromisoformat(raw_timestamp),
            )
        except ValueError as err:
            raise ValueError("Invalid serialized AccessPointSynchronization") from err


__all__ = [
    "AccessPointSynchronization",
    "AccessPointSynchronizationData",
    "SynchronizationStatus",
    "aggregate_synchronization_status",
]
