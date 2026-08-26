"""Persistence for canonical managed Access Point synchronization status."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import cast
from uuid import UUID

from ..exceptions import StorageError
from ..models import AccessPointSynchronization
from ..storage import HomePassStorageData, HomePassStorageManager, StorageRecord


class SynchronizationStatusRepository:
    """Persist one deterministic status record per managed Access Point."""

    def __init__(self, storage: HomePassStorageManager) -> None:
        """Initialize the shared storage boundary."""
        self._storage = storage
        self._lock = asyncio.Lock()

    async def get(self, access_point_id: UUID) -> AccessPointSynchronization:
        """Load one status or fail closed when it is unavailable."""
        records = await self._load_records()
        try:
            return records[access_point_id]
        except KeyError as err:
            raise StorageError("Synchronization status is unavailable") from err

    async def list_all(self) -> tuple[AccessPointSynchronization, ...]:
        """List statuses in deterministic Access Point order."""
        records = await self._load_records()
        return tuple(records[key] for key in sorted(records, key=str))

    async def upsert(
        self,
        record: AccessPointSynchronization,
    ) -> AccessPointSynchronization:
        """Persist one evaluation without allowing its timestamp to move backwards."""

        def mutate(snapshot: HomePassStorageData) -> AccessPointSynchronization:
            existing_data = snapshot["data"]["synchronization_statuses"].get(
                str(record.access_point_id)
            )
            if existing_data is not None:
                existing = AccessPointSynchronization.from_dict(existing_data)
                if record.last_evaluated_at < existing.last_evaluated_at:
                    raise ValueError("Synchronization evaluation timestamp cannot move backwards")
            snapshot["data"]["synchronization_statuses"][str(record.access_point_id)] = cast(
                StorageRecord,
                record.to_dict(),
            )
            return record

        return await self._mutate(mutate)

    async def replace_all(
        self,
        records: tuple[AccessPointSynchronization, ...],
    ) -> tuple[AccessPointSynchronization, ...]:
        """Atomically replace the complete managed Access Point status set."""
        if len({record.access_point_id for record in records}) != len(records):
            raise ValueError("Synchronization statuses must have unique Access Point IDs")

        def mutate(snapshot: HomePassStorageData) -> tuple[AccessPointSynchronization, ...]:
            snapshot["data"]["synchronization_statuses"] = {
                str(record.access_point_id): cast(StorageRecord, record.to_dict())
                for record in records
            }
            return records

        return await self._mutate(mutate)

    async def remove(self, access_point_id: UUID) -> None:
        """Remove a status after its Access Point stops being managed."""

        def mutate(snapshot: HomePassStorageData) -> None:
            snapshot["data"]["synchronization_statuses"].pop(str(access_point_id), None)

        await self._mutate(mutate)

    async def _load_records(self) -> dict[UUID, AccessPointSynchronization]:
        """Load and validate every status record."""
        try:
            async with self._lock:
                snapshot = await self._storage.async_load()
            records: dict[UUID, AccessPointSynchronization] = {}
            for stored_id, raw_record in snapshot["data"]["synchronization_statuses"].items():
                record = AccessPointSynchronization.from_dict(raw_record)
                if str(record.access_point_id) != stored_id:
                    raise ValueError("Stored synchronization identifier does not match its record")
                records[record.access_point_id] = record
            return records
        except StorageError:
            raise
        except Exception as err:
            raise StorageError("Unable to load synchronization status") from err

    async def _mutate[ResultT](
        self,
        mutator: Callable[[HomePassStorageData], ResultT],
    ) -> ResultT:
        """Run one status mutation through the shared transaction boundary."""
        try:
            async with self._lock:
                return await self._storage.async_transaction(mutator)
        except StorageError:
            raise
        except Exception as err:
            raise StorageError("Unable to save synchronization status") from err


__all__ = ["SynchronizationStatusRepository"]
