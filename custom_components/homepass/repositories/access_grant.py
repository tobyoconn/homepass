"""Repository for persisted Access Grant relationships."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import replace
from typing import cast
from uuid import UUID

from ..exceptions import PersonNotFoundError, StorageError
from ..models import AccessGrant, Person
from ..storage import HomePassStorageData, HomePassStorageManager, StorageRecord


class AccessGrantRepository:
    """Persist one active Access Grant per Person and Access Point."""

    def __init__(self, storage_manager: HomePassStorageManager) -> None:
        """Initialize the repository."""
        self._storage_manager = storage_manager
        self._lock = asyncio.Lock()

    async def upsert(self, grant: AccessGrant) -> AccessGrant:
        """Create or replace a relationship while preserving its identity."""

        def mutate(storage: HomePassStorageData) -> AccessGrant:
            next_grant = grant
            records = self._deserialize_records(storage)
            key = self._key(grant.person_id, grant.access_point_id)
            existing = records.get(key)
            if existing is not None:
                next_grant = replace(
                    next_grant,
                    access_grant_id=existing.access_grant_id,
                    created_at=existing.created_at,
                )
            storage["data"]["access_grants"][key] = cast(StorageRecord, next_grant.to_dict())
            return next_grant

        return await self._mutate(mutate)

    async def upsert_inheriting_person_schedule(self, grant: AccessGrant) -> AccessGrant:
        """Persist a new grant using the Person Schedule read inside the transaction."""

        def mutate(storage: HomePassStorageData) -> AccessGrant:
            person_record = storage["data"]["people"].get(str(grant.person_id))
            if person_record is None:
                raise PersonNotFoundError(str(grant.person_id))
            person = Person.from_dict(person_record)
            inherited = replace(grant, schedule_id=person.schedule_id)
            records = self._deserialize_records(storage)
            key = self._key(inherited.person_id, inherited.access_point_id)
            existing = records.get(key)
            if existing is not None:
                inherited = replace(
                    inherited,
                    access_grant_id=existing.access_grant_id,
                    created_at=existing.created_at,
                )
            storage["data"]["access_grants"][key] = cast(StorageRecord, inherited.to_dict())
            return inherited

        return await self._mutate(mutate)

    async def list_for_person(self, person_id: UUID) -> tuple[AccessGrant, ...]:
        """Return active grants for one Person ordered by Access Point ID."""
        async with self._lock:
            _, records = await self._load_records()
            return tuple(
                sorted(
                    (grant for grant in records.values() if grant.person_id == person_id),
                    key=lambda grant: str(grant.access_point_id),
                )
            )

    async def has_for_access_point(self, access_point_id: UUID) -> bool:
        """Return whether any persisted grant references an Access Point."""
        async with self._lock:
            _, records = await self._load_records()
            return any(grant.access_point_id == access_point_id for grant in records.values())

    async def remove(self, person_id: UUID, access_point_id: UUID) -> None:
        """Remove exactly one Person-to-Access-Point grant if present."""

        def mutate(storage: HomePassStorageData) -> None:
            storage["data"]["access_grants"].pop(self._key(person_id, access_point_id), None)

        await self._mutate(mutate)

    async def _load_records(self) -> tuple[HomePassStorageData, dict[str, AccessGrant]]:
        """Load and validate every persisted grant."""
        try:
            storage = await self._storage_manager.async_load()
            return storage, self._deserialize_records(storage)
        except StorageError:
            raise
        except Exception as err:
            raise StorageError("Unable to load HomePASS Access Grants") from err

    async def _mutate[ResultT](
        self,
        mutator: Callable[[HomePassStorageData], ResultT],
    ) -> ResultT:
        """Run one repository mutation in the shared storage transaction."""
        try:
            async with self._lock:
                return await self._storage_manager.async_transaction(mutator)
        except StorageError:
            raise
        except Exception as err:
            raise StorageError("Unable to save HomePASS Access Grants") from err

    @classmethod
    def _deserialize_records(cls, storage: HomePassStorageData) -> dict[str, AccessGrant]:
        """Deserialize Access Grant records from one snapshot."""
        records: dict[str, AccessGrant] = {}
        for stored_key, record in storage["data"]["access_grants"].items():
            grant = AccessGrant.from_dict(record)
            if cls._key(grant.person_id, grant.access_point_id) != stored_key:
                raise StorageError("Stored Access Grant identifier does not match its record")
            records[stored_key] = grant
        return records

    @staticmethod
    def _key(person_id: UUID, access_point_id: UUID) -> str:
        """Return the stable relationship key."""
        return f"{person_id}:{access_point_id}"
