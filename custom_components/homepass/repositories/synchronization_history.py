"""Durable synchronization history repository."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import cast
from uuid import UUID

from ..exceptions import StorageError
from ..models import SynchronizationHistoryEvent
from ..storage import HomePassStorageData, HomePassStorageManager, StorageRecord

HISTORY_LIMIT_PER_RELATIONSHIP = 50


class SynchronizationHistoryRepository:
    """Persist immutable bounded history for access relationships."""

    def __init__(self, storage: HomePassStorageManager) -> None:
        self._storage = storage
        self._lock = asyncio.Lock()

    async def add(self, event: SynchronizationHistoryEvent) -> SynchronizationHistoryEvent:
        """Append one event and atomically trim only its relationship."""

        def mutate(snapshot: HomePassStorageData) -> SynchronizationHistoryEvent:
            records = snapshot["data"]["synchronization_history"]
            key = str(event.event_id)
            if key in records:
                raise ValueError("Synchronization history event already exists")
            records[key] = cast(StorageRecord, event.to_dict())
            related = sorted(
                (
                    SynchronizationHistoryEvent.from_dict(record)
                    for record in records.values()
                    if record.get("person_id") == str(event.person_id)
                    and record.get("access_point_id") == str(event.access_point_id)
                ),
                key=lambda item: (item.occurred_at, str(item.event_id)),
                reverse=True,
            )
            for expired in related[HISTORY_LIMIT_PER_RELATIONSHIP:]:
                records.pop(str(expired.event_id))
            return event

        return await self._mutate(mutate)

    async def list_for_relationship(
        self, person_id: UUID, access_point_id: UUID
    ) -> tuple[SynchronizationHistoryEvent, ...]:
        return tuple(
            event
            for event in await self._load()
            if event.person_id == person_id and event.access_point_id == access_point_id
        )

    async def list_for_person(self, person_id: UUID) -> tuple[SynchronizationHistoryEvent, ...]:
        return tuple(event for event in await self._load() if event.person_id == person_id)

    async def list_for_access_point(
        self, access_point_id: UUID
    ) -> tuple[SynchronizationHistoryEvent, ...]:
        return tuple(
            event for event in await self._load() if event.access_point_id == access_point_id
        )

    async def _load(self) -> tuple[SynchronizationHistoryEvent, ...]:
        try:
            async with self._lock:
                snapshot = await self._storage.async_load()
            events = tuple(
                SynchronizationHistoryEvent.from_dict(record)
                for record in snapshot["data"]["synchronization_history"].values()
            )
            return tuple(
                sorted(
                    events, key=lambda item: (item.occurred_at, str(item.event_id)), reverse=True
                )
            )
        except StorageError:
            raise
        except Exception as err:
            raise StorageError("Unable to load synchronization history") from err

    async def _mutate[ResultT](self, mutator: Callable[[HomePassStorageData], ResultT]) -> ResultT:
        try:
            async with self._lock:
                return await self._storage.async_transaction(mutator)
        except StorageError:
            raise
        except Exception as err:
            raise StorageError("Unable to save synchronization history") from err


__all__ = ["HISTORY_LIMIT_PER_RELATIONSHIP", "SynchronizationHistoryRepository"]
