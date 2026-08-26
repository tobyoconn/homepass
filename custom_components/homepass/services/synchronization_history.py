"""Recording and presentation boundary for synchronization history."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TypedDict
from uuid import UUID, uuid4

from ..models import (
    LifecycleOperation,
    LifecycleOperationStatus,
    SynchronizationHistoryEvent,
    SynchronizationHistoryEventType,
    SynchronizationHistorySeverity,
)
from ..repositories import SynchronizationHistoryRepository


class SynchronizationHistoryPresentationData(TypedDict):
    """Safe serialized history row."""

    title: str
    description: str
    severity: str
    timestamp: str


@dataclass(frozen=True, slots=True)
class SynchronizationHistoryPresentation:
    """One history event safe for direct homeowner presentation."""

    title: str
    description: str
    severity: SynchronizationHistorySeverity
    timestamp: datetime

    def to_dict(self) -> SynchronizationHistoryPresentationData:
        return {
            "title": self.title,
            "description": self.description,
            "severity": self.severity.value,
            "timestamp": self.timestamp.isoformat(),
        }


_EVENT_COPY: dict[
    SynchronizationHistoryEventType,
    tuple[SynchronizationHistorySeverity, str, str],
] = {
    SynchronizationHistoryEventType.PROVISIONING_STARTED: (
        SynchronizationHistorySeverity.INFO,
        "Adding access",
        "HomePASS started adding this access to the door.",
    ),
    SynchronizationHistoryEventType.PROVISIONING_COMPLETED: (
        SynchronizationHistorySeverity.SUCCESS,
        "Access added",
        "HomePASS added this access to the door.",
    ),
    SynchronizationHistoryEventType.PROVISIONING_FAILED: (
        SynchronizationHistorySeverity.ERROR,
        "Access could not be added",
        "HomePASS could not add this access to the door.",
    ),
    SynchronizationHistoryEventType.CREDENTIAL_REPLACEMENT_STARTED: (
        SynchronizationHistorySeverity.INFO,
        "Access code update started",
        "HomePASS started updating this access code.",
    ),
    SynchronizationHistoryEventType.CREDENTIAL_REPLACEMENT_COMPLETED: (
        SynchronizationHistorySeverity.SUCCESS,
        "Access code updated",
        "HomePASS updated this access code.",
    ),
    SynchronizationHistoryEventType.CREDENTIAL_REPLACEMENT_FAILED: (
        SynchronizationHistorySeverity.ERROR,
        "Access code update incomplete",
        "HomePASS could not complete this access code update.",
    ),
    SynchronizationHistoryEventType.VERIFICATION_SUCCEEDED: (
        SynchronizationHistorySeverity.SUCCESS,
        "Change confirmed",
        "HomePASS confirmed the change at the door.",
    ),
    SynchronizationHistoryEventType.VERIFICATION_PENDING: (
        SynchronizationHistorySeverity.WARNING,
        "PIN verification pending",
        "HomePASS programmed this PIN but has not yet confirmed it at the lock.",
    ),
    SynchronizationHistoryEventType.VERIFICATION_FAILED: (
        SynchronizationHistorySeverity.WARNING,
        "Change not confirmed",
        "HomePASS could not confirm the change at the door.",
    ),
    SynchronizationHistoryEventType.RECOVERY_STARTED: (
        SynchronizationHistorySeverity.INFO,
        "Recovery started",
        "HomePASS started recovering this access.",
    ),
    SynchronizationHistoryEventType.RECOVERY_COMPLETED: (
        SynchronizationHistorySeverity.SUCCESS,
        "Recovery completed",
        "HomePASS recovered this access.",
    ),
    SynchronizationHistoryEventType.RECOVERY_FAILED: (
        SynchronizationHistorySeverity.ERROR,
        "Recovery incomplete",
        "HomePASS could not complete recovery for this access.",
    ),
    SynchronizationHistoryEventType.RETRY_REQUIRED: (
        SynchronizationHistorySeverity.WARNING,
        "Try synchronization again",
        "HomePASS could not confirm the latest change. You can try again.",
    ),
    SynchronizationHistoryEventType.MANUAL_ATTENTION_REQUIRED: (
        SynchronizationHistorySeverity.ERROR,
        "Manual attention required",
        "HomePASS could not complete synchronization. Review this door before continuing.",
    ),
    SynchronizationHistoryEventType.SYNCHRONIZATION_RESTORED: (
        SynchronizationHistorySeverity.SUCCESS,
        "Synchronization restored",
        "HomePASS and this door are synchronized again.",
    ),
}


class SynchronizationHistoryService:
    """Record meaningful events without duplicating synchronization decisions."""

    CREDENTIAL_REPLACEMENT_OPERATION = "credential_replacement"

    def __init__(self, repository: SynchronizationHistoryRepository) -> None:
        self._repository = repository

    async def record(
        self,
        event_type: SynchronizationHistoryEventType,
        person_id: UUID,
        access_point_id: UUID,
        *,
        occurred_at: datetime | None = None,
    ) -> SynchronizationHistoryEvent:
        severity, title, description = _EVENT_COPY[event_type]
        return await self._repository.add(
            SynchronizationHistoryEvent(
                uuid4(),
                person_id,
                access_point_id,
                occurred_at or datetime.now(UTC),
                event_type,
                severity,
                title,
                description,
            )
        )

    async def for_person(self, person_id: UUID) -> tuple[SynchronizationHistoryPresentation, ...]:
        return tuple(
            self.present(event) for event in await self._repository.list_for_person(person_id)
        )

    async def for_access_point(
        self, access_point_id: UUID
    ) -> tuple[SynchronizationHistoryPresentation, ...]:
        return tuple(
            self.present(event)
            for event in await self._repository.list_for_access_point(access_point_id)
        )

    @staticmethod
    def present(event: SynchronizationHistoryEvent) -> SynchronizationHistoryPresentation:
        """Remove internal identity and event vocabulary from a history row."""
        return SynchronizationHistoryPresentation(
            event.title, event.description, event.severity, event.occurred_at
        )

    async def lifecycle_changed(self, operation: LifecycleOperation) -> None:
        """Record credential-replacement boundary transitions once."""
        if operation.operation_type != self.CREDENTIAL_REPLACEMENT_OPERATION:
            return
        raw_person_id = operation.payload.get("person_id")
        raw_targets = operation.payload.get("targets")
        if not isinstance(raw_person_id, str) or not isinstance(raw_targets, list):
            return
        person_id = UUID(raw_person_id)
        target_ids = sorted(
            {
                UUID(raw_id)
                for target in raw_targets
                if isinstance(target, dict)
                and isinstance((raw_id := target.get("access_point_id")), str)
            },
            key=str,
        )
        event_types: tuple[SynchronizationHistoryEventType, ...] = ()
        if operation.status is LifecycleOperationStatus.PENDING:
            event_types = (SynchronizationHistoryEventType.CREDENTIAL_REPLACEMENT_STARTED,)
        elif operation.status is LifecycleOperationStatus.COMPLETED:
            event_types = (
                SynchronizationHistoryEventType.CREDENTIAL_REPLACEMENT_COMPLETED,
                SynchronizationHistoryEventType.VERIFICATION_SUCCEEDED,
                SynchronizationHistoryEventType.SYNCHRONIZATION_RESTORED,
            )
        elif operation.status is LifecycleOperationStatus.WAITING_RETRY:
            event_types = (
                SynchronizationHistoryEventType.CREDENTIAL_REPLACEMENT_FAILED,
                SynchronizationHistoryEventType.RETRY_REQUIRED,
            )
        elif operation.status is LifecycleOperationStatus.FAILED:
            event_types = (
                SynchronizationHistoryEventType.CREDENTIAL_REPLACEMENT_FAILED,
                SynchronizationHistoryEventType.MANUAL_ATTENTION_REQUIRED,
            )
        for access_point_id in target_ids:
            for event_type in event_types:
                await self.record(event_type, person_id, access_point_id)


__all__ = [
    "SynchronizationHistoryPresentation",
    "SynchronizationHistoryPresentationData",
    "SynchronizationHistoryService",
]
