"""Safe homeowner-initiated recovery for one synchronized access relationship."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import partial
from typing import TypedDict, cast
from uuid import UUID, uuid4

from ..models import (
    AccessGrant,
    AccessMetadata,
    AccessPoint,
    AccessPointSynchronization,
    ActivityEventType,
    ActivityOutcome,
    LifecycleOperation,
    LifecycleOperationStatus,
    Person,
    SynchronizationHistoryEventType,
    SynchronizationStatus,
)
from ..storage import HomePassStorageData, HomePassStorageManager
from ..vault import CredentialVaultProtocol
from .access_management import AccessManagementService
from .activity_producer import ActivityProducer
from .credential_replacement import CredentialReplacementLifecycleService
from .person_deletion import PersonDeletionService
from .synchronization_history import SynchronizationHistoryService
from .synchronization_presentation import (
    SynchronizationPresentation,
    SynchronizationPresentationData,
    SynchronizationSeverity,
    synchronization_presentation,
)
from .synchronization_status import SynchronizationStatusService
from .zwave_sync import VerificationStatus


class SynchronizationRecoveryResultData(TypedDict):
    """Presentation-only action result with opaque navigation identifiers."""

    person_id: str
    access_point_id: str
    person_name: str
    door_name: str
    title: str
    description: str
    severity: SynchronizationSeverity
    retry_allowed: bool
    completed: bool
    in_progress: bool
    synchronization: SynchronizationPresentationData


@dataclass(frozen=True, slots=True)
class SynchronizationRecoveryResult:
    """Friendly result of one safe recovery request."""

    person_id: UUID
    access_point_id: UUID
    person_name: str
    door_name: str
    title: str
    description: str
    severity: SynchronizationSeverity
    completed: bool
    in_progress: bool
    synchronization: SynchronizationPresentation

    def to_dict(self) -> SynchronizationRecoveryResultData:
        """Serialize without lifecycle, driver, credential, or enum details."""
        return {
            "person_id": str(self.person_id),
            "access_point_id": str(self.access_point_id),
            "person_name": self.person_name,
            "door_name": self.door_name,
            "title": self.title,
            "description": self.description,
            "severity": self.severity,
            "retry_allowed": self.synchronization.retry_allowed,
            "completed": self.completed,
            "in_progress": self.in_progress,
            "synchronization": self.synchronization.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class _RecoveryContext:
    person: Person
    access_point: AccessPoint
    grant: AccessGrant
    metadata: AccessMetadata
    synchronization: AccessPointSynchronization
    operations: tuple[LifecycleOperation, ...]


class SynchronizationRecoveryService:
    """Validate and resume only an existing safe credential workflow."""

    def __init__(
        self,
        storage: HomePassStorageManager,
        credential_vault: CredentialVaultProtocol,
        synchronization_status_service: SynchronizationStatusService,
        access_management_service: AccessManagementService,
        credential_replacement_service: CredentialReplacementLifecycleService,
        person_deletion_service: PersonDeletionService,
        synchronization_history_service: SynchronizationHistoryService | None = None,
        activity_producer: ActivityProducer | None = None,
    ) -> None:
        """Initialize existing persistence and lifecycle boundaries."""
        self._storage = storage
        self._credential_vault = credential_vault
        self._synchronization_status_service = synchronization_status_service
        self._access_management_service = access_management_service
        self._credential_replacement_service = credential_replacement_service
        self._person_deletion_service = person_deletion_service
        self._synchronization_history_service = synchronization_history_service
        self._activity_producer = activity_producer
        self._active_recoveries: dict[
            tuple[UUID, UUID],
            asyncio.Task[SynchronizationRecoveryResult],
        ] = {}

    async def recover(
        self,
        *,
        person_id: UUID,
        access_point_id: UUID,
    ) -> SynchronizationRecoveryResult:
        """Recover one exact relationship without duplicating credential writes."""
        if not isinstance(person_id, UUID) or not isinstance(access_point_id, UUID):
            raise TypeError("Synchronization recovery identifiers must be UUIDs")
        key = (person_id, access_point_id)
        task = self._active_recoveries.get(key)
        if task is None:
            task = asyncio.create_task(self._recover_once(person_id, access_point_id))
            self._active_recoveries[key] = task
            task.add_done_callback(partial(self._forget_recovery, key))
        return await asyncio.shield(task)

    def _forget_recovery(
        self,
        key: tuple[UUID, UUID],
        completed: asyncio.Task[SynchronizationRecoveryResult],
    ) -> None:
        """Forget only the completed single-flight task registered for this relationship."""
        if self._active_recoveries.get(key) is completed:
            self._active_recoveries.pop(key, None)

    async def _recover_once(
        self,
        person_id: UUID,
        access_point_id: UUID,
    ) -> SynchronizationRecoveryResult:
        recovery_id = uuid4()
        try:
            snapshot = await self._storage.async_load()
            context = self._context(snapshot, person_id, access_point_id)
            if (
                context.metadata.vault_credential_id is None
                or not await self._credential_vault.exists(context.metadata.vault_credential_id)
            ):
                raise ValueError("Credential context is unavailable")
        except Exception:
            presentation = await self._record_unavailable(access_point_id)
            return self._result(
                person_id,
                access_point_id,
                "Selected user",
                "Selected door",
                "Synchronization unavailable",
                "HomePASS could not safely verify this access relationship. "
                "No lock change was made.",
                "error",
                presentation,
            )

        presentation = SynchronizationStatusService.relationship_presentation_from_snapshot(
            snapshot,
            (person_id, access_point_id),
            context.synchronization,
        )
        active = tuple(
            operation
            for operation in context.operations
            if operation.status
            not in {LifecycleOperationStatus.COMPLETED, LifecycleOperationStatus.CANCELLED}
        )
        if len(active) > 1:
            await self._synchronization_status_service.record_manual_attention(access_point_id)
            await self._record_history(
                SynchronizationHistoryEventType.MANUAL_ATTENTION_REQUIRED,
                person_id,
                access_point_id,
            )
            updated = await self._current_presentation(access_point_id, presentation)
            await self._record_activity(
                ActivityEventType.SYNCHRONIZATION_ATTENTION_REQUIRED,
                recovery_id,
                context,
                "overlapping-changes",
                ActivityOutcome.FAILED,
            )
            return self._result(
                person_id,
                access_point_id,
                context.person.display_name,
                context.access_point.display_name,
                "Manual attention required",
                "HomePASS found overlapping access changes and did not change the lock.",
                "error",
                updated,
            )
        if active and active[0].status in {
            LifecycleOperationStatus.PENDING,
            LifecycleOperationStatus.RUNNING,
        }:
            return self._result(
                person_id,
                access_point_id,
                context.person.display_name,
                context.access_point.display_name,
                "Synchronization in progress",
                "HomePASS is already working on this access. No duplicate change was started.",
                "info",
                presentation,
                in_progress=True,
            )
        if context.synchronization.status is SynchronizationStatus.SYNCHRONIZED:
            return self._result(
                person_id,
                access_point_id,
                context.person.display_name,
                context.access_point.display_name,
                "Already synchronized",
                "HomePASS and this lock are already synchronized.",
                "success",
                presentation,
                completed=True,
            )
        pin_verification_retry = (
            not active
            and context.synchronization.status is SynchronizationStatus.UNKNOWN
            and context.grant.synchronization_status is SynchronizationStatus.UNKNOWN
            and context.metadata.synchronization_status is SynchronizationStatus.UNKNOWN
        )
        if not presentation.retry_allowed and not pin_verification_retry:
            title = (
                "Manual attention required"
                if context.synchronization.status is SynchronizationStatus.MANUAL_ATTENTION_REQUIRED
                else "Synchronization unavailable"
            )
            return self._result(
                person_id,
                access_point_id,
                context.person.display_name,
                context.access_point.display_name,
                title,
                presentation.description,
                presentation.severity,
                presentation,
                in_progress=context.synchronization.status
                in {SynchronizationStatus.PENDING, SynchronizationStatus.SYNCHRONIZING},
            )

        if active and (
            active[0].operation_type
            not in {
                CredentialReplacementLifecycleService.OPERATION_TYPE,
                PersonDeletionService.OPERATION_TYPE,
            }
            or (
                active[0].operation_type == CredentialReplacementLifecycleService.OPERATION_TYPE
                and active[0].payload.get("resumable") is not True
            )
        ):
            await self._synchronization_status_service.record_manual_attention(access_point_id)
            await self._record_history(
                SynchronizationHistoryEventType.MANUAL_ATTENTION_REQUIRED,
                person_id,
                access_point_id,
            )
            updated = await self._current_presentation(access_point_id, presentation)
            await self._record_activity(
                ActivityEventType.SYNCHRONIZATION_ATTENTION_REQUIRED,
                recovery_id,
                context,
                "unsafe-recovery",
                ActivityOutcome.FAILED,
            )
            return self._result(
                person_id,
                access_point_id,
                context.person.display_name,
                context.access_point.display_name,
                "Manual attention required",
                "HomePASS cannot safely resume this access change. No lock change was made.",
                "error",
                updated,
            )
        if (
            not active
            and not pin_verification_retry
            and (
                context.grant.synchronization_status is not SynchronizationStatus.RETRY_REQUIRED
                or context.metadata.synchronization_status
                is not SynchronizationStatus.RETRY_REQUIRED
            )
        ):
            await self._recompute_record(access_point_id, context.synchronization)
            unavailable = synchronization_presentation(
                AccessPointSynchronization(
                    access_point_id,
                    SynchronizationStatus.UNKNOWN,
                    context.synchronization.last_evaluated_at,
                )
            )
            return self._result(
                person_id,
                access_point_id,
                context.person.display_name,
                context.access_point.display_name,
                "Synchronization unavailable",
                "This access is no longer the relationship that needs retry. "
                "No lock change was made.",
                "warning",
                unavailable,
            )

        await self._record_history(
            SynchronizationHistoryEventType.RECOVERY_STARTED,
            person_id,
            access_point_id,
        )
        try:
            verification_status = await self._resume(context, active[0] if active else None)
        except Exception:
            updated_record = await self._recompute_record(access_point_id, context.synchronization)
            updated = synchronization_presentation(updated_record)
            await self._record_history(
                SynchronizationHistoryEventType.RECOVERY_FAILED,
                person_id,
                access_point_id,
            )
            if updated.retry_allowed:
                await self._record_history(
                    SynchronizationHistoryEventType.RETRY_REQUIRED,
                    person_id,
                    access_point_id,
                )
            elif updated.severity == "error":
                await self._record_history(
                    SynchronizationHistoryEventType.MANUAL_ATTENTION_REQUIRED,
                    person_id,
                    access_point_id,
                )
            await self._record_activity(
                ActivityEventType.SYNCHRONIZATION_ATTENTION_REQUIRED,
                recovery_id,
                context,
                "recovery-failed",
                ActivityOutcome.FAILED,
            )
            if updated.retry_allowed:
                title = "Synchronization could not be completed"
                description = "HomePASS could not confirm the change. You can try again."
            elif updated.severity == "error":
                title = "Manual attention required"
                description = updated.description
            else:
                title = "Synchronization unavailable"
                description = "HomePASS could not safely confirm this access relationship."
            return self._result(
                person_id,
                access_point_id,
                context.person.display_name,
                context.access_point.display_name,
                title,
                description,
                updated.severity,
                updated,
            )

        if verification_status is None:
            updated_record = await self._recompute_record(access_point_id, context.synchronization)
            updated = synchronization_presentation(updated_record)
        else:
            updated_record, updated = await self._current_relationship(
                person_id,
                access_point_id,
                context.synchronization,
                presentation,
            )
        if updated_record.status is SynchronizationStatus.SYNCHRONIZED:
            await self._record_history(
                SynchronizationHistoryEventType.RECOVERY_COMPLETED,
                person_id,
                access_point_id,
            )
            await self._record_history(
                SynchronizationHistoryEventType.SYNCHRONIZATION_RESTORED,
                person_id,
                access_point_id,
            )
            await self._record_activity(
                ActivityEventType.SYNCHRONIZATION_RECOVERED,
                recovery_id,
                context,
                "recovery-completed",
                ActivityOutcome.SUCCEEDED,
            )
            return self._result(
                person_id,
                access_point_id,
                context.person.display_name,
                context.access_point.display_name,
                "Synchronization complete",
                "HomePASS confirmed that this access is synchronized with the lock.",
                "success",
                updated,
                completed=True,
            )
        if updated_record.status in {
            SynchronizationStatus.SYNCHRONIZING,
            SynchronizationStatus.PENDING,
        }:
            return self._result(
                person_id,
                access_point_id,
                context.person.display_name,
                context.access_point.display_name,
                "Synchronization in progress",
                updated.description,
                updated.severity,
                updated,
                in_progress=True,
            )
        if updated_record.status is SynchronizationStatus.MANUAL_ATTENTION_REQUIRED:
            if verification_status == "failed":
                updated = SynchronizationPresentation(
                    "PIN confirmation failed",
                    "HomePASS could not confirm this PIN. Retry synchronization or change the PIN.",
                    "error",
                    True,
                    updated_record.last_evaluated_at,
                )
            await self._record_activity(
                ActivityEventType.SYNCHRONIZATION_ATTENTION_REQUIRED,
                recovery_id,
                context,
                "manual-attention",
                ActivityOutcome.FAILED,
            )
            return self._result(
                person_id,
                access_point_id,
                context.person.display_name,
                context.access_point.display_name,
                (
                    "PIN confirmation failed"
                    if verification_status == "failed"
                    else "Manual attention required"
                ),
                (
                    "HomePASS could not confirm this PIN. Retry synchronization or change the PIN."
                    if verification_status == "failed"
                    else updated.description
                ),
                updated.severity,
                updated,
            )
        if updated_record.status is SynchronizationStatus.UNKNOWN:
            updated = SynchronizationPresentation(
                "PIN verification pending",
                "HomePASS programmed this PIN but has not yet confirmed it at the lock.",
                "warning",
                True,
                updated_record.last_evaluated_at,
            )
            return self._result(
                person_id,
                access_point_id,
                context.person.display_name,
                context.access_point.display_name,
                "PIN verification pending",
                "HomePASS programmed this PIN but has not yet confirmed it at the lock.",
                "warning",
                updated,
            )
        await self._record_activity(
            ActivityEventType.SYNCHRONIZATION_ATTENTION_REQUIRED,
            recovery_id,
            context,
            "recovery-unconfirmed",
            ActivityOutcome.FAILED,
        )
        return self._result(
            person_id,
            access_point_id,
            context.person.display_name,
            context.access_point.display_name,
            "Synchronization could not be completed",
            updated.description,
            updated.severity,
            updated,
        )

    async def _record_history(
        self,
        event_type: SynchronizationHistoryEventType,
        person_id: UUID,
        access_point_id: UUID,
    ) -> None:
        if self._synchronization_history_service is not None:
            await self._synchronization_history_service.record(
                event_type, person_id, access_point_id
            )

    async def _record_activity(
        self,
        event_type: ActivityEventType,
        recovery_id: UUID,
        context: _RecoveryContext,
        suffix: str,
        outcome: ActivityOutcome,
    ) -> None:
        if self._activity_producer is None:
            return
        await self._activity_producer.record(
            event_type,
            occurred_at=datetime.now(UTC),
            source_event_key=(
                f"synchronization-recovery:{recovery_id}:"
                f"{context.person.person_id}:{context.access_point.id}:{suffix}"
            ),
            person=context.person,
            access_point=context.access_point,
            correlation_id=recovery_id,
            outcome=outcome,
        )

    async def _resume(
        self,
        context: _RecoveryContext,
        operation: LifecycleOperation | None,
    ) -> VerificationStatus | None:
        if operation is not None:
            if operation.status is not LifecycleOperationStatus.WAITING_RETRY:
                raise ValueError("Lifecycle operation is not safely retryable")
            if operation.operation_type == CredentialReplacementLifecycleService.OPERATION_TYPE:
                await self._credential_replacement_service.retry_pin(context.person.person_id)
                return None
            if operation.operation_type == PersonDeletionService.OPERATION_TYPE:
                await self._person_deletion_service.delete_person(context.person.person_id)
                return None
            raise ValueError("Lifecycle operation cannot be recovered safely")
        if (
            context.grant.synchronization_status is SynchronizationStatus.UNKNOWN
            and context.metadata.synchronization_status is SynchronizationStatus.UNKNOWN
        ):
            return await self._access_management_service.retry_provisioning_verification(
                context.person.person_id,
                context.access_point.id,
                expected_updated_at=context.metadata.updated_at,
            )
        if (
            context.grant.synchronization_status is not SynchronizationStatus.RETRY_REQUIRED
            and context.metadata.synchronization_status is not SynchronizationStatus.RETRY_REQUIRED
        ):
            raise ValueError("Selected relationship is not the retryable relationship")
        await self._access_management_service.retry_removal_verification(
            context.person.person_id,
            context.access_point.id,
            expected_updated_at=context.metadata.updated_at,
        )
        return None

    @classmethod
    def _context(
        cls,
        snapshot: HomePassStorageData,
        person_id: UUID,
        access_point_id: UUID,
    ) -> _RecoveryContext:
        data = snapshot["data"]
        person = Person.from_dict(data["people"][str(person_id)])
        access_point = AccessPoint.from_dict(data["access_points"][str(access_point_id)])
        enrollment = cast(dict[str, object], data["settings"]["managed_access_points"])[
            str(access_point_id)
        ]
        if not isinstance(enrollment, dict) or enrollment.get("managed") is not True:
            raise ValueError("Access Point is not managed")
        key = f"{person_id}:{access_point_id}"
        grant = AccessGrant.from_dict(data["access_grants"][key])
        metadata = AccessMetadata.from_dict(data["access_metadata"][key])
        synchronization = SynchronizationStatusService.relationship_records_from_snapshot(
            snapshot
        ).get((person_id, access_point_id))
        if (
            person.person_id != person_id
            or access_point.id != access_point_id
            or grant.person_id != person_id
            or grant.access_point_id != access_point_id
            or metadata.person_id != person_id
            or metadata.access_point_id != access_point_id
            or synchronization is None
            or synchronization.access_point_id != access_point_id
            or metadata.vault_credential_id is None
            or grant.credential_id != metadata.vault_credential_id.value
            or grant.synchronization_status is not metadata.synchronization_status
        ):
            raise ValueError("Synchronization relationship is inconsistent")
        operations: list[LifecycleOperation] = []
        for raw_operation in data["lifecycle_operations"].values():
            operation = LifecycleOperation.from_dict(raw_operation)
            references_relationship = cls._references_relationship(
                operation,
                person_id,
                access_point_id,
            )
            if references_relationship:
                operations.append(operation)
                continue
            if (
                operation.payload.get("person_id") == str(person_id)
                and operation.operation_type
                in {
                    CredentialReplacementLifecycleService.OPERATION_TYPE,
                    PersonDeletionService.OPERATION_TYPE,
                }
                and operation.status
                not in {
                    LifecycleOperationStatus.COMPLETED,
                    LifecycleOperationStatus.CANCELLED,
                }
            ):
                raise ValueError("Lifecycle relationship is ambiguous")
        return _RecoveryContext(
            person,
            access_point,
            grant,
            metadata,
            synchronization,
            tuple(operations),
        )

    @staticmethod
    def _references_relationship(
        operation: LifecycleOperation,
        person_id: UUID,
        access_point_id: UUID,
    ) -> bool:
        if operation.payload.get("person_id") != str(person_id):
            return False
        targets = operation.payload.get("targets")
        if not isinstance(targets, list):
            raise ValueError("Lifecycle targets are unavailable")
        for target in targets:
            if not isinstance(target, dict):
                raise ValueError("Lifecycle target is unavailable")
            raw_access_point_id = target.get("access_point_id")
            if not isinstance(raw_access_point_id, str):
                raise ValueError("Lifecycle target is unavailable")
            if UUID(raw_access_point_id) == access_point_id:
                return True
        return False

    async def _record_unavailable(
        self,
        access_point_id: UUID,
    ) -> SynchronizationPresentation:
        try:
            record = await self._synchronization_status_service.record_manual_attention(
                access_point_id
            )
            return synchronization_presentation(record)
        except Exception:
            return synchronization_presentation(
                AccessPointSynchronization(
                    access_point_id,
                    SynchronizationStatus.UNKNOWN,
                    datetime.now(UTC),
                )
            )

    async def _recompute_record(
        self,
        access_point_id: UUID,
        fallback: AccessPointSynchronization,
    ) -> AccessPointSynchronization:
        try:
            return await self._synchronization_status_service.recompute(access_point_id)
        except Exception:
            return fallback

    async def _current_relationship(
        self,
        person_id: UUID,
        access_point_id: UUID,
        fallback_record: AccessPointSynchronization,
        fallback_presentation: SynchronizationPresentation,
    ) -> tuple[AccessPointSynchronization, SynchronizationPresentation]:
        """Reload one relationship after exact verification from one snapshot."""
        try:
            snapshot = await self._storage.async_load()
            record = SynchronizationStatusService.relationship_records_from_snapshot(snapshot).get(
                (person_id, access_point_id)
            )
            if record is None:
                return fallback_record, fallback_presentation
            presentation = SynchronizationStatusService.relationship_presentation_from_snapshot(
                snapshot,
                (person_id, access_point_id),
                record,
            )
            return record, presentation
        except Exception:
            return fallback_record, fallback_presentation

    async def _current_presentation(
        self,
        access_point_id: UUID,
        fallback: SynchronizationPresentation,
    ) -> SynchronizationPresentation:
        try:
            return await self._synchronization_status_service.presentation(access_point_id)
        except Exception:
            return fallback

    @staticmethod
    def _result(
        person_id: UUID,
        access_point_id: UUID,
        person_name: str,
        door_name: str,
        title: str,
        description: str,
        severity: SynchronizationSeverity,
        synchronization: SynchronizationPresentation,
        *,
        completed: bool = False,
        in_progress: bool = False,
    ) -> SynchronizationRecoveryResult:
        return SynchronizationRecoveryResult(
            person_id,
            access_point_id,
            person_name,
            door_name,
            title,
            description,
            severity,
            completed,
            in_progress,
            synchronization,
        )


__all__ = [
    "SynchronizationRecoveryResult",
    "SynchronizationRecoveryResultData",
    "SynchronizationRecoveryService",
]
