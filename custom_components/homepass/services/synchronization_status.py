"""Application service for canonical managed Access Point synchronization status."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import cast
from uuid import UUID

from ..models import (
    AccessGrant,
    AccessMetadata,
    AccessPointSynchronization,
    LifecycleOperation,
    LifecycleOperationStatus,
    SynchronizationHistoryEvent,
    SynchronizationHistoryEventType,
    SynchronizationStatus,
    aggregate_synchronization_status,
)
from ..repositories import SynchronizationStatusRepository
from ..repositories.access_metadata import AccessMetadataRepository
from ..storage import HomePassStorageData, HomePassStorageManager
from ..vault import CredentialMetadata
from .synchronization_presentation import (
    SynchronizationPresentation,
    synchronization_presentation,
)

_MANAGED_ACCESS_POINTS_SETTING = "managed_access_points"

_LIFECYCLE_EVIDENCE = {
    LifecycleOperationStatus.PENDING: SynchronizationStatus.PENDING,
    LifecycleOperationStatus.RUNNING: SynchronizationStatus.SYNCHRONIZING,
    LifecycleOperationStatus.WAITING_RETRY: SynchronizationStatus.RETRY_REQUIRED,
    LifecycleOperationStatus.FAILED: SynchronizationStatus.MANUAL_ATTENTION_REQUIRED,
    LifecycleOperationStatus.COMPLETED: SynchronizationStatus.SYNCHRONIZED,
}


class SynchronizationStatusService:
    """Evaluate and persist one canonical status for every managed Access Point."""

    def __init__(
        self,
        storage: HomePassStorageManager,
        repository: SynchronizationStatusRepository,
        access_metadata_repository: AccessMetadataRepository | None = None,
    ) -> None:
        """Initialize the shared snapshot and persistence boundaries."""
        self._storage = storage
        self._repository = repository
        self._access_metadata_repository = access_metadata_repository

    async def recompute(
        self,
        access_point_id: UUID,
        *,
        evaluated_at: datetime | None = None,
    ) -> AccessPointSynchronization:
        """Recompute one managed Access Point from current durable evidence."""
        snapshot = await self._load_repaired_snapshot()
        self._require_managed(snapshot, access_point_id)
        record = AccessPointSynchronization(
            access_point_id,
            self._evaluate(snapshot, access_point_id),
            evaluated_at or datetime.now(UTC),
        )
        return await self._repository.upsert(record)

    async def recompute_all(
        self,
        *,
        evaluated_at: datetime | None = None,
    ) -> tuple[AccessPointSynchronization, ...]:
        """Recompute every managed Access Point from one isolated snapshot."""
        snapshot = await self._load_repaired_snapshot()
        timestamp = evaluated_at or datetime.now(UTC)
        records = tuple(
            AccessPointSynchronization(
                access_point_id,
                self._evaluate(snapshot, access_point_id),
                timestamp,
            )
            for access_point_id in self._managed_ids(snapshot)
        )
        return await self._repository.replace_all(records)

    async def record_synchronized(
        self,
        access_point_id: UUID,
        *,
        evaluated_at: datetime | None = None,
    ) -> AccessPointSynchronization:
        """Record a synchronization result after an operation was explicitly verified."""
        snapshot = await self._load_repaired_snapshot()
        self._require_managed(snapshot, access_point_id)
        status = (
            SynchronizationStatus.MANUAL_ATTENTION_REQUIRED
            if AccessMetadataRepository.integrity_issues_from_snapshot(snapshot, access_point_id)
            else SynchronizationStatus.SYNCHRONIZED
        )
        return await self._repository.upsert(
            AccessPointSynchronization(
                access_point_id,
                status,
                evaluated_at or datetime.now(UTC),
            )
        )

    async def record_manual_attention(
        self,
        access_point_id: UUID,
        *,
        evaluated_at: datetime | None = None,
    ) -> AccessPointSynchronization:
        """Fail closed when recovery cannot safely interpret relationship evidence."""
        snapshot = await self._load_repaired_snapshot()
        self._require_managed(snapshot, access_point_id)
        return await self._repository.upsert(
            AccessPointSynchronization(
                access_point_id,
                SynchronizationStatus.MANUAL_ATTENTION_REQUIRED,
                evaluated_at or datetime.now(UTC),
            )
        )

    async def lifecycle_changed(self, operation: LifecycleOperation) -> None:
        """Recompute every managed Access Point referenced by a lifecycle transition."""
        if not isinstance(operation, LifecycleOperation):
            raise TypeError("Synchronization lifecycle observation requires an operation")
        snapshot = await self._storage.async_load()
        managed_ids = set(self._managed_ids(snapshot))
        referenced_ids = self._operation_access_point_ids(operation)
        timestamp = datetime.now(UTC)
        for access_point_id in sorted(referenced_ids & managed_ids, key=str):
            await self._repository.upsert(
                AccessPointSynchronization(
                    access_point_id,
                    self._evaluate(snapshot, access_point_id),
                    timestamp,
                )
            )

    async def presentation(
        self,
        access_point_id: UUID,
    ) -> SynchronizationPresentation:
        """Return shared homeowner-facing presentation for one persisted status."""
        return synchronization_presentation(await self._repository.get(access_point_id))

    async def relationship_presentations(
        self,
    ) -> dict[tuple[UUID, UUID], SynchronizationPresentation]:
        """Present each persisted credential relationship from one isolated snapshot."""
        snapshot = await self._storage.async_load()
        return self.relationship_presentations_from_snapshot(snapshot)

    @classmethod
    def relationship_presentations_from_snapshot(
        cls,
        snapshot: HomePassStorageData,
    ) -> dict[tuple[UUID, UUID], SynchronizationPresentation]:
        """Present relationship status without loading outside the supplied snapshot."""
        return {
            key: cls.relationship_presentation_from_snapshot(snapshot, key, record)
            for key, record in cls.relationship_records_from_snapshot(snapshot).items()
        }

    @staticmethod
    def relationship_presentation_from_snapshot(
        snapshot: HomePassStorageData,
        key: tuple[UUID, UUID],
        record: AccessPointSynchronization,
    ) -> SynchronizationPresentation:
        """Explain PIN verification state from one authoritative snapshot."""
        person_id, access_point_id = key
        relationship_key = f"{person_id}:{access_point_id}"
        raw_grant = snapshot["data"]["access_grants"].get(relationship_key)
        raw_metadata = snapshot["data"]["access_metadata"].get(relationship_key)
        raw_authority = snapshot["data"].get("credential_metadata", {}).get(str(person_id))
        try:
            grant = None if raw_grant is None else AccessGrant.from_dict(raw_grant)
            metadata = None if raw_metadata is None else AccessMetadata.from_dict(raw_metadata)
            authority = (
                None if raw_authority is None else CredentialMetadata.from_dict(raw_authority)
            )
        except (KeyError, TypeError, ValueError):
            grant = None
            metadata = None
            authority = None
        if (
            grant is None
            or metadata is None
            or authority is None
            or not authority.enabled
            or authority.person_id != person_id
            or metadata.vault_credential_id is None
            or grant.credential_id != authority.credential_id.value
            or metadata.vault_credential_id != authority.credential_id
        ):
            return SynchronizationPresentation(
                "Access setup needs attention",
                "Credential ownership could not be verified safely.",
                "error",
                False,
                record.last_evaluated_at,
            )
        history = sorted(
            (
                SynchronizationHistoryEvent.from_dict(raw_event)
                for raw_event in snapshot["data"].get("synchronization_history", {}).values()
                if raw_event.get("person_id") == str(person_id)
                and raw_event.get("access_point_id") == str(access_point_id)
            ),
            key=lambda event: (event.occurred_at, str(event.event_id)),
            reverse=True,
        )
        latest = None if not history else history[0].event_type
        if record.status is SynchronizationStatus.UNKNOWN and latest in {
            SynchronizationHistoryEventType.VERIFICATION_PENDING,
            SynchronizationHistoryEventType.VERIFICATION_FAILED,
        }:
            return SynchronizationPresentation(
                "PIN verification pending",
                "HomePASS programmed this PIN but has not yet confirmed it at the lock.",
                "warning",
                True,
                record.last_evaluated_at,
            )
        if (
            record.status is SynchronizationStatus.MANUAL_ATTENTION_REQUIRED
            and latest is SynchronizationHistoryEventType.VERIFICATION_FAILED
        ):
            return SynchronizationPresentation(
                "PIN confirmation failed",
                "HomePASS could not confirm this PIN. Retry synchronization or change the PIN.",
                "error",
                True,
                record.last_evaluated_at,
            )
        return synchronization_presentation(record)

    @classmethod
    def relationship_records_from_snapshot(
        cls,
        snapshot: HomePassStorageData,
    ) -> dict[tuple[UUID, UUID], AccessPointSynchronization]:
        """Evaluate relationship status entirely within one supplied snapshot."""
        canonical = cls.canonical_records_from_snapshot(snapshot)
        lifecycle_evidence: dict[tuple[UUID, UUID], list[SynchronizationStatus]] = {}
        for raw_record in snapshot["data"]["lifecycle_operations"].values():
            operation = LifecycleOperation.from_dict(raw_record)
            raw_person_id = operation.payload.get("person_id")
            status = _LIFECYCLE_EVIDENCE.get(operation.status)
            if not isinstance(raw_person_id, str) or status is None:
                continue
            person_id = UUID(raw_person_id)
            for access_point_id in cls._operation_access_point_ids(operation):
                lifecycle_evidence.setdefault((person_id, access_point_id), []).append(status)
        records: dict[tuple[UUID, UUID], AccessPointSynchronization] = {}
        for key, raw_grant in snapshot["data"]["access_grants"].items():
            grant = AccessGrant.from_dict(raw_grant)
            if key != f"{grant.person_id}:{grant.access_point_id}":
                raise ValueError("Stored Access Grant identifier does not match its record")
            raw_metadata = snapshot["data"]["access_metadata"].get(key)
            if raw_metadata is None:
                relationship_status = SynchronizationStatus.MANUAL_ATTENTION_REQUIRED
            else:
                metadata = AccessMetadata.from_dict(raw_metadata)
                if (
                    metadata.person_id != grant.person_id
                    or metadata.access_point_id != grant.access_point_id
                    or metadata.vault_credential_id is None
                    or metadata.vault_credential_id.value != grant.credential_id
                ):
                    relationship_status = SynchronizationStatus.MANUAL_ATTENTION_REQUIRED
                else:
                    relationship_status = aggregate_synchronization_status(
                        (
                            grant.synchronization_status,
                            metadata.synchronization_status,
                            *lifecycle_evidence.get((grant.person_id, grant.access_point_id), ()),
                        )
                    )
            canonical_record = canonical.get(grant.access_point_id)
            if canonical_record is None:
                continue
            if AccessMetadataRepository.integrity_issues_from_snapshot(
                snapshot, grant.access_point_id
            ):
                relationship_status = SynchronizationStatus.MANUAL_ATTENTION_REQUIRED
            if (
                relationship_status is SynchronizationStatus.RETRY_REQUIRED
                and canonical_record.status is not SynchronizationStatus.RETRY_REQUIRED
            ):
                relationship_status = SynchronizationStatus.MANUAL_ATTENTION_REQUIRED
            records[(grant.person_id, grant.access_point_id)] = AccessPointSynchronization(
                grant.access_point_id,
                relationship_status,
                canonical_record.last_evaluated_at,
            )
        return records

    @staticmethod
    def canonical_records_from_snapshot(
        snapshot: HomePassStorageData,
    ) -> dict[UUID, AccessPointSynchronization]:
        """Load canonical records entirely within one supplied snapshot."""
        records: dict[UUID, AccessPointSynchronization] = {}
        for stored_id, raw_record in snapshot["data"]["synchronization_statuses"].items():
            record = AccessPointSynchronization.from_dict(raw_record)
            if stored_id != str(record.access_point_id):
                raise ValueError("Stored synchronization identifier does not match its record")
            records[record.access_point_id] = record
        return records

    @classmethod
    def managed_access_point_ids_from_snapshot(
        cls,
        snapshot: HomePassStorageData,
    ) -> tuple[UUID, ...]:
        """Return the complete managed synchronization scope from one snapshot."""
        return cls._managed_ids(snapshot)

    @staticmethod
    def _evaluate(
        snapshot: HomePassStorageData,
        access_point_id: UUID,
    ) -> SynchronizationStatus:
        """Aggregate relationship and lifecycle evidence conservatively."""
        issues = AccessMetadataRepository.integrity_issues_from_snapshot(snapshot, access_point_id)
        blocking_issues = {
            "duplicate_slot",
            "orphan_person",
            "grant_ownership",
            "credential_authority",
            "synchronization_conflict",
        }
        if issues & blocking_issues:
            return SynchronizationStatus.MANUAL_ATTENTION_REQUIRED
        evidence = [
            metadata.synchronization_status
            for raw_record in snapshot["data"]["access_metadata"].values()
            if (metadata := AccessMetadata.from_dict(raw_record)).access_point_id == access_point_id
        ]
        evidence.extend(
            grant.synchronization_status
            for raw_record in snapshot["data"]["access_grants"].values()
            if (grant := AccessGrant.from_dict(raw_record)).access_point_id == access_point_id
        )
        for raw_record in snapshot["data"]["lifecycle_operations"].values():
            operation = LifecycleOperation.from_dict(raw_record)
            if access_point_id not in SynchronizationStatusService._operation_access_point_ids(
                operation
            ):
                continue
            status = _LIFECYCLE_EVIDENCE.get(operation.status)
            if status is not None:
                evidence.append(status)
        status = aggregate_synchronization_status(evidence)
        if status is SynchronizationStatus.SYNCHRONIZED and issues:
            return SynchronizationStatus.MANUAL_ATTENTION_REQUIRED
        return status

    async def _load_repaired_snapshot(self) -> HomePassStorageData:
        """Repair deterministic legacy orphans before evaluating current ownership."""
        if self._access_metadata_repository is not None:
            await self._access_metadata_repository.repair_deterministic_orphans()
        return await self._storage.async_load()

    @staticmethod
    def _managed_ids(snapshot: HomePassStorageData) -> tuple[UUID, ...]:
        """Decode the complete managed Access Point scope deterministically."""
        settings = snapshot["data"]["settings"]
        raw_enrollments = settings.get(_MANAGED_ACCESS_POINTS_SETTING)
        if not isinstance(raw_enrollments, dict):
            raise ValueError("Managed Access Point status is unavailable")
        managed: list[UUID] = []
        for raw_id, raw_enrollment in raw_enrollments.items():
            if not isinstance(raw_id, str) or not isinstance(raw_enrollment, dict):
                raise ValueError("Managed Access Point status is unavailable")
            if raw_enrollment.get("managed") is True:
                managed.append(UUID(raw_id))
        return tuple(sorted(managed, key=str))

    @classmethod
    def _require_managed(
        cls,
        snapshot: HomePassStorageData,
        access_point_id: UUID,
    ) -> None:
        """Reject status evaluation outside the managed Access Point scope."""
        if access_point_id not in cls._managed_ids(snapshot):
            raise ValueError("Synchronization status is available only for managed doors")

    @staticmethod
    def _operation_access_point_ids(operation: LifecycleOperation) -> set[UUID]:
        """Extract explicitly labeled Access Point references from safe journal payloads."""
        references: set[UUID] = set()

        def visit(value: object) -> None:
            if isinstance(value, dict):
                for key, item in value.items():
                    if key == "access_point_id":
                        if not isinstance(item, str):
                            raise ValueError("Lifecycle Access Point reference is invalid")
                        references.add(UUID(item))
                    else:
                        visit(item)
            elif isinstance(value, list):
                for item in value:
                    visit(item)

        visit(cast(object, operation.payload))
        return references


__all__ = ["SynchronizationStatusService"]
