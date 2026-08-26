"""Repository for non-secret access synchronization metadata."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from contextlib import suppress
from dataclasses import replace
from typing import cast
from uuid import UUID

from ..exceptions import CredentialSlotIntegrityError, StorageError
from ..models import (
    AccessGrant,
    AccessMetadata,
    LifecycleOperation,
    LifecycleOperationStatus,
    SynchronizationStatus,
)
from ..storage import HomePassStorageData, HomePassStorageManager, StorageRecord


class AccessMetadataRepository:
    """Persist Access Metadata by its Person and Access Point relationship."""

    def __init__(self, storage_manager: HomePassStorageManager) -> None:
        """Initialize the repository."""
        self._storage_manager = storage_manager
        self._lock = asyncio.Lock()

    async def upsert(self, metadata: AccessMetadata) -> AccessMetadata:
        """Create or replace one relationship while preserving its creation time."""

        def mutate(storage: HomePassStorageData) -> AccessMetadata:
            self.repair_deterministic_orphans_in_snapshot(storage)
            next_metadata = metadata
            records = self._deserialize_records(storage)
            existing = records.get((metadata.person_id, metadata.access_point_id))
            if existing is not None:
                next_metadata = replace(next_metadata, created_at=existing.created_at)
            if any(
                record.access_point_id == metadata.access_point_id
                and record.slot == metadata.slot
                and (record.person_id, record.access_point_id)
                != (metadata.person_id, metadata.access_point_id)
                for record in records.values()
            ):
                raise CredentialSlotIntegrityError
            storage["data"]["access_metadata"][self._key(next_metadata)] = self._serialize(
                next_metadata
            )
            return next_metadata

        return await self._mutate(mutate)

    async def repair_deterministic_orphans(self) -> tuple[tuple[UUID, UUID], ...]:
        """Remove only legacy slot records that cannot own a credential or relationship."""
        async with self._lock:
            snapshot = await self._storage_manager.async_load()
            candidates = self.deterministic_orphans_from_snapshot(snapshot)
            if not candidates:
                return ()

            def mutate(storage: HomePassStorageData) -> tuple[tuple[UUID, UUID], ...]:
                removed = self.repair_deterministic_orphans_in_snapshot(storage)
                return tuple(sorted(removed, key=lambda key: (str(key[0]), str(key[1]))))

            try:
                return await self._storage_manager.async_transaction(mutate)
            except StorageError:
                raise
            except Exception as err:
                raise StorageError("Unable to repair HomePASS credential slot ownership") from err

    @classmethod
    def deterministic_orphans_from_snapshot(
        cls,
        storage: HomePassStorageData,
    ) -> set[tuple[UUID, UUID]]:
        """Identify unambiguous legacy metadata with no possible current owner."""
        people = storage["data"]["people"]
        grants = storage["data"]["access_grants"]
        authorities = storage["data"].get("credential_metadata", {})
        active_operation_people = cls._active_operation_people(storage)
        return {
            key
            for key, metadata in cls._deserialize_records(storage).items()
            if str(metadata.person_id) not in people
            and cls._key(metadata) not in grants
            and str(metadata.person_id) not in authorities
            and metadata.vault_credential_id is None
            and metadata.synchronization_status is not SynchronizationStatus.SYNCHRONIZED
            and metadata.person_id not in active_operation_people
        }

    @classmethod
    def repair_deterministic_orphans_in_snapshot(
        cls,
        storage: HomePassStorageData,
    ) -> set[tuple[UUID, UUID]]:
        """Repair only deterministic legacy orphans in one atomic working snapshot."""
        removed = cls.deterministic_orphans_from_snapshot(storage)
        for key in removed:
            storage["data"]["access_metadata"].pop(f"{key[0]}:{key[1]}", None)
        return removed

    @classmethod
    def integrity_issues_from_snapshot(
        cls,
        storage: HomePassStorageData,
        access_point_id: UUID,
    ) -> frozenset[str]:
        """Return non-presentational ownership defects for one Door."""
        issues: set[str] = set()
        records = cls._deserialize_records(storage)
        grants: dict[tuple[UUID, UUID], AccessGrant] = {}
        for stored_key, raw_grant in storage["data"]["access_grants"].items():
            grant = AccessGrant.from_dict(raw_grant)
            if stored_key != f"{grant.person_id}:{grant.access_point_id}":
                issues.add("grant_identifier")
            grants[(grant.person_id, grant.access_point_id)] = grant

        slots: dict[int, list[AccessMetadata]] = {}
        for key, metadata in records.items():
            if metadata.access_point_id != access_point_id:
                continue
            slots.setdefault(metadata.slot, []).append(metadata)
            relationship_grant = grants.get(key)
            raw_authority = (
                storage["data"].get("credential_metadata", {}).get(str(metadata.person_id))
            )
            if str(metadata.person_id) not in storage["data"]["people"]:
                issues.add("orphan_person")
            if relationship_grant is None:
                issues.add("missing_grant")
            elif (
                metadata.vault_credential_id is None
                or relationship_grant.credential_id != metadata.vault_credential_id.value
            ):
                issues.add("grant_ownership")
            if raw_authority is None or metadata.vault_credential_id is None:
                issues.add("missing_authority")
            else:
                from ..vault import CredentialMetadata

                authority = CredentialMetadata.from_dict(raw_authority)
                if (
                    authority.person_id != metadata.person_id
                    or authority.credential_id != metadata.vault_credential_id
                    or not authority.enabled
                ):
                    issues.add("credential_authority")
            if relationship_grant is not None and (
                relationship_grant.synchronization_status is SynchronizationStatus.SYNCHRONIZED
            ) != (metadata.synchronization_status is SynchronizationStatus.SYNCHRONIZED):
                issues.add("synchronization_conflict")
        if any(len(owners) > 1 for owners in slots.values()):
            issues.add("duplicate_slot")
        for key, grant in grants.items():
            if grant.access_point_id != access_point_id:
                continue
            if str(grant.person_id) not in storage["data"]["people"]:
                issues.add("orphan_person")
            if key not in records:
                issues.add("missing_slot")
            if str(grant.person_id) not in storage["data"].get("credential_metadata", {}):
                issues.add("missing_authority")
        return frozenset(issues)

    @staticmethod
    def _active_operation_people(storage: HomePassStorageData) -> set[UUID]:
        """Return People referenced by incomplete lifecycle operations."""
        terminal = {LifecycleOperationStatus.COMPLETED, LifecycleOperationStatus.CANCELLED}
        people: set[UUID] = set()
        for raw_operation in storage["data"]["lifecycle_operations"].values():
            operation = LifecycleOperation.from_dict(raw_operation)
            if operation.status in terminal:
                continue
            AccessMetadataRepository._collect_uuid_values(operation.payload, people)
        return people

    @staticmethod
    def _collect_uuid_values(value: object, found: set[UUID]) -> None:
        """Collect UUID strings from structured lifecycle payloads without inference."""
        if isinstance(value, str):
            with suppress(ValueError):
                found.add(UUID(value))
        elif isinstance(value, dict):
            for nested in value.values():
                AccessMetadataRepository._collect_uuid_values(nested, found)
        elif isinstance(value, list):
            for nested in value:
                AccessMetadataRepository._collect_uuid_values(nested, found)

    async def list_for_person(self, person_id: UUID) -> tuple[AccessMetadata, ...]:
        """Return one Person's access metadata ordered by Access Point ID."""
        async with self._lock:
            _, records = await self._load_records()
            return tuple(
                sorted(
                    (metadata for metadata in records.values() if metadata.person_id == person_id),
                    key=lambda metadata: str(metadata.access_point_id),
                )
            )

    async def list_all(self) -> tuple[AccessMetadata, ...]:
        """Return every persisted synchronization record in stable order."""
        async with self._lock:
            _, records = await self._load_records()
            return tuple(
                sorted(
                    records.values(),
                    key=lambda metadata: (str(metadata.person_id), str(metadata.access_point_id)),
                )
            )

    async def remove(self, person_id: UUID, access_point_id: UUID) -> None:
        """Remove exactly one relationship if present."""

        def mutate(storage: HomePassStorageData) -> None:
            storage["data"]["access_metadata"].pop(f"{person_id}:{access_point_id}", None)

        await self._mutate(mutate)

    async def _load_records(
        self,
    ) -> tuple[HomePassStorageData, dict[tuple[UUID, UUID], AccessMetadata]]:
        """Load and validate every access metadata record."""
        try:
            storage = await self._storage_manager.async_load()
            return storage, self._deserialize_records(storage)
        except (CredentialSlotIntegrityError, StorageError):
            raise
        except Exception as err:
            raise StorageError("Unable to load HomePASS access metadata") from err

    async def _mutate[ResultT](
        self,
        mutator: Callable[[HomePassStorageData], ResultT],
    ) -> ResultT:
        """Run one repository mutation in the shared storage transaction."""
        try:
            async with self._lock:
                return await self._storage_manager.async_transaction(mutator)
        except (CredentialSlotIntegrityError, StorageError):
            raise
        except Exception as err:
            raise StorageError("Unable to save HomePASS access metadata") from err

    @classmethod
    def _deserialize_records(
        cls,
        storage: HomePassStorageData,
    ) -> dict[tuple[UUID, UUID], AccessMetadata]:
        """Deserialize Access Metadata records from one snapshot."""
        records: dict[tuple[UUID, UUID], AccessMetadata] = {}
        for stored_key, record in storage["data"]["access_metadata"].items():
            metadata = AccessMetadata.from_dict(record)
            if cls._key(metadata) != stored_key:
                raise StorageError("Stored access metadata identifier does not match its record")
            records[(metadata.person_id, metadata.access_point_id)] = metadata
        return records

    @staticmethod
    def _key(metadata: AccessMetadata) -> str:
        """Return the deterministic non-secret relationship key."""
        return f"{metadata.person_id}:{metadata.access_point_id}"

    @staticmethod
    def _serialize(metadata: AccessMetadata) -> StorageRecord:
        """Serialize non-secret metadata for the shared storage manager."""
        return cast(StorageRecord, metadata.to_dict())
