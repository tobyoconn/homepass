"""Append-only durable Activity Event repository."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import cast
from uuid import UUID

from ..exceptions import ActivityDuplicateConflictError, StorageError
from ..models import ActivityEvent
from ..storage import HomePassStorageData, HomePassStorageManager, StorageRecord

ACTIVITY_RETENTION_LIMIT = 500


def activity_order(event: ActivityEvent) -> tuple[datetime, datetime, str]:
    """Return the ADR-011 deterministic event ordering key."""
    return event.occurred_at, event.recorded_at, str(event.event_id)


@dataclass(frozen=True, slots=True)
class ActivityAppendResult:
    """Result of an atomic append or exact duplicate suppression."""

    event: ActivityEvent
    recorded: bool


class ActivityRepository:
    """Persist immutable Activity Events with deterministic global retention."""

    def __init__(self, storage: HomePassStorageManager) -> None:
        self._storage = storage
        self._lock = asyncio.Lock()

    async def append(self, event: ActivityEvent) -> ActivityAppendResult:
        """Append a fact once, suppress exact redelivery, and retain the newest 500."""
        if not isinstance(event, ActivityEvent):
            raise TypeError("Activity repository accepts only ActivityEvent values")

        def mutate(snapshot: HomePassStorageData) -> ActivityAppendResult:
            records = snapshot["data"]["activity_events"]
            event_key = str(event.event_id)
            existing_record = records.get(event_key)
            if existing_record is not None:
                existing = ActivityEvent.from_dict(existing_record)
                if not existing.same_fact_as(event):
                    raise ActivityDuplicateConflictError(
                        "Activity event identity belongs to a different fact"
                    )
                return ActivityAppendResult(existing, False)

            if event.deduplication_key is not None:
                duplicate_key = str(event.deduplication_key)
                for record in records.values():
                    if record.get("deduplication_key") != duplicate_key:
                        continue
                    existing = ActivityEvent.from_dict(record)
                    if not existing.same_fact_as(event):
                        raise ActivityDuplicateConflictError(
                            "Activity duplicate identity belongs to a different fact"
                        )
                    return ActivityAppendResult(existing, False)

            records[event_key] = cast(StorageRecord, event.to_dict())
            ordered = sorted(
                (ActivityEvent.from_dict(record) for record in records.values()),
                key=activity_order,
                reverse=True,
            )
            for expired in ordered[ACTIVITY_RETENTION_LIMIT:]:
                records.pop(str(expired.event_id))
            return ActivityAppendResult(event, event_key in records)

        return await self._mutate(mutate)

    async def get(self, event_id: UUID) -> ActivityEvent | None:
        """Return one retained event by its stable identity."""
        if not isinstance(event_id, UUID):
            raise TypeError("Activity event_id must be a UUID")
        try:
            async with self._lock:
                snapshot = await self._storage.async_load()
            record = snapshot["data"]["activity_events"].get(str(event_id))
            return None if record is None else ActivityEvent.from_dict(record)
        except StorageError:
            raise
        except Exception as err:
            raise StorageError("Unable to load Activity Event") from err

    async def list_events(
        self,
        *,
        limit: int = ACTIVITY_RETENTION_LIMIT,
        newest_first: bool = True,
    ) -> tuple[ActivityEvent, ...]:
        """Return a bounded deterministic view in either chronological direction."""
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 500:
            raise ValueError("Activity limit must be between 1 and 500")
        if not isinstance(newest_first, bool):
            raise TypeError("Activity ordering direction must be a boolean")
        try:
            async with self._lock:
                snapshot = await self._storage.async_load()
            events = tuple(
                ActivityEvent.from_dict(record)
                for record in snapshot["data"]["activity_events"].values()
            )
            return tuple(sorted(events, key=activity_order, reverse=newest_first)[:limit])
        except StorageError:
            raise
        except Exception as err:
            raise StorageError("Unable to load Activity Events") from err

    async def _mutate[ResultT](self, mutator: Callable[[HomePassStorageData], ResultT]) -> ResultT:
        try:
            async with self._lock:
                return await self._storage.async_transaction(mutator)
        except ActivityDuplicateConflictError, StorageError:
            raise
        except Exception as err:
            raise StorageError("Unable to save Activity Event") from err


__all__ = [
    "ACTIVITY_RETENTION_LIMIT",
    "ActivityAppendResult",
    "ActivityRepository",
    "activity_order",
]
