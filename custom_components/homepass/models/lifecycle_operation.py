"""Durable non-secret lifecycle operation journal."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Self, TypedDict
from uuid import UUID, uuid4

type LifecyclePayloadValue = (
    str | int | float | bool | None | list[LifecyclePayloadValue] | dict[str, LifecyclePayloadValue]
)


class LifecycleOperationStatus(StrEnum):
    """Generic lifecycle execution states."""

    PENDING = "pending"
    RUNNING = "running"
    WAITING_RETRY = "waiting_retry"
    FAILED = "failed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class LifecycleOperationData(TypedDict):
    """JSON-compatible lifecycle operation record."""

    operation_id: str
    operation_type: str
    status: str
    created_at: str
    updated_at: str
    payload: dict[str, LifecyclePayloadValue]
    current_step: int
    retry_count: int


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _aware_utc(value: datetime, field_name: str) -> datetime:
    if not isinstance(value, datetime):
        raise TypeError(f"LifecycleOperation {field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"LifecycleOperation {field_name} must be timezone-aware")
    return value.astimezone(UTC)


def _non_negative(value: object, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"LifecycleOperation {field_name} must be an integer")
    if value < 0:
        raise ValueError(f"LifecycleOperation {field_name} must not be negative")
    return value


def _json_value(value: object) -> bool:
    if value is None or isinstance(value, str | bool | int):
        return True
    if isinstance(value, float):
        return value == value and value not in (float("inf"), float("-inf"))
    if isinstance(value, list):
        return all(_json_value(item) for item in value)
    if isinstance(value, dict):
        return all(isinstance(key, str) and _json_value(item) for key, item in value.items())
    return False


@dataclass(frozen=True, slots=True)
class LifecycleOperation:
    """Persisted progress for one restart-safe multi-step operation."""

    operation_type: str
    payload: Mapping[str, LifecyclePayloadValue]
    operation_id: UUID = field(default_factory=uuid4)
    status: LifecycleOperationStatus = LifecycleOperationStatus.PENDING
    current_step: int = 0
    retry_count: int = 0
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)

    def __post_init__(self) -> None:
        if not isinstance(self.operation_id, UUID):
            raise TypeError("LifecycleOperation operation_id must be a UUID")
        if not isinstance(self.operation_type, str):
            raise TypeError("LifecycleOperation operation_type must be a string")
        operation_type = self.operation_type.strip()
        if not operation_type:
            raise ValueError("LifecycleOperation operation_type is required")
        if not isinstance(self.status, LifecycleOperationStatus):
            raise TypeError("LifecycleOperation status must be a LifecycleOperationStatus")
        if not isinstance(self.payload, Mapping):
            raise TypeError("LifecycleOperation payload must be a mapping")
        payload = dict(self.payload)
        if not _json_value(payload):
            raise ValueError("LifecycleOperation payload must contain only JSON values")
        current_step = _non_negative(self.current_step, "current_step")
        retry_count = _non_negative(self.retry_count, "retry_count")
        created_at = _aware_utc(self.created_at, "created_at")
        updated_at = _aware_utc(self.updated_at, "updated_at")
        if updated_at < created_at:
            raise ValueError("LifecycleOperation updated_at must not precede created_at")
        object.__setattr__(self, "operation_type", operation_type)
        object.__setattr__(self, "payload", deepcopy(payload))
        object.__setattr__(self, "current_step", current_step)
        object.__setattr__(self, "retry_count", retry_count)
        object.__setattr__(self, "created_at", created_at)
        object.__setattr__(self, "updated_at", updated_at)

    def to_dict(self) -> LifecycleOperationData:
        return {
            "operation_id": str(self.operation_id),
            "operation_type": self.operation_type,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "payload": deepcopy(dict(self.payload)),
            "current_step": self.current_step,
            "retry_count": self.retry_count,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> Self:
        try:
            operation_id = UUID(str(data["operation_id"]))
            operation_type = data["operation_type"]
            raw_status = data["status"]
            if not isinstance(raw_status, str):
                raise TypeError
            status = LifecycleOperationStatus(raw_status)
            created_at = datetime.fromisoformat(str(data["created_at"]))
            updated_at = datetime.fromisoformat(str(data["updated_at"]))
            payload = data["payload"]
            current_step = data["current_step"]
            retry_count = data["retry_count"]
        except (KeyError, TypeError, ValueError) as err:
            raise ValueError("Invalid serialized LifecycleOperation") from err
        if not isinstance(operation_type, str) or not isinstance(payload, Mapping):
            raise TypeError("Invalid serialized LifecycleOperation fields")
        return cls(
            operation_id=operation_id,
            operation_type=operation_type,
            status=status,
            created_at=created_at,
            updated_at=updated_at,
            payload=dict(payload),
            current_step=_non_negative(current_step, "current_step"),
            retry_count=_non_negative(retry_count, "retry_count"),
        )
