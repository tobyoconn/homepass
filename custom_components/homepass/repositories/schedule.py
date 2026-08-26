"""Schedule repository for HomePASS."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import cast
from uuid import UUID

from ..exceptions import (
    DuplicateScheduleError,
    ProtectedScheduleError,
    ScheduleNotFoundError,
    StorageError,
)
from ..models import (
    PERMANENT_SCHEDULE_ID,
    PERMANENT_SCHEDULE_NAME,
    AccessGrant,
    Person,
    Schedule,
    permanent_schedule,
)
from ..storage import HomePassStorageData, HomePassStorageManager, StorageRecord
from .base import Repository


class ScheduleRepository(Repository[Schedule, UUID]):
    """Persist and retrieve immutable Schedule domain models."""

    def __init__(self, storage_manager: HomePassStorageManager) -> None:
        """Initialize the repository."""
        self._storage_manager = storage_manager
        self._lock = asyncio.Lock()

    async def get(self, entity_id: UUID) -> Schedule:
        """Return a schedule by UUID."""
        async with self._lock:
            await self._ensure_permanent()
            _, schedules = await self._load_schedules()
            try:
                return schedules[entity_id]
            except KeyError as err:
                raise ScheduleNotFoundError(str(entity_id)) from err

    async def list_all(self) -> tuple[Schedule, ...]:
        """Return all schedules ordered by name and UUID."""
        async with self._lock:
            await self._ensure_permanent()
            _, schedules = await self._load_schedules()
            return tuple(
                sorted(
                    schedules.values(),
                    key=lambda schedule: (
                        schedule.schedule_id != PERMANENT_SCHEDULE_ID,
                        schedule.name.casefold(),
                        str(schedule.schedule_id),
                    ),
                )
            )

    async def add(self, entity: Schedule) -> None:
        """Add a schedule when its UUID and normalized name are unique."""

        def mutate(storage: HomePassStorageData) -> None:
            schedules = self._deserialize_schedules(storage, repair_permanent=True)
            if entity.schedule_id == PERMANENT_SCHEDULE_ID:
                raise ProtectedScheduleError("The Permanent schedule identifier is reserved")
            self._ensure_unique(entity, schedules)
            storage["data"]["schedules"][str(entity.schedule_id)] = self._serialize(entity)

        await self._mutate(mutate)

    async def update(self, entity: Schedule) -> None:
        """Replace an existing schedule."""

        def mutate(storage: HomePassStorageData) -> None:
            schedules = self._deserialize_schedules(storage, repair_permanent=True)
            if entity.schedule_id == PERMANENT_SCHEDULE_ID:
                raise ProtectedScheduleError("The Permanent schedule cannot be modified")
            if entity.schedule_id not in schedules:
                raise ScheduleNotFoundError(str(entity.schedule_id))
            self._ensure_not_person_owned(storage, entity.schedule_id)
            self._ensure_unique(entity, schedules, exclude_id=entity.schedule_id)
            storage["data"]["schedules"][str(entity.schedule_id)] = self._serialize(entity)

        await self._mutate(mutate)

    async def remove(self, entity_id: UUID) -> None:
        """Remove a schedule by UUID."""

        def mutate(storage: HomePassStorageData) -> None:
            schedules = self._deserialize_schedules(storage, repair_permanent=True)
            if entity_id == PERMANENT_SCHEDULE_ID:
                raise ProtectedScheduleError("The Permanent schedule cannot be deleted")
            if entity_id not in schedules:
                raise ScheduleNotFoundError(str(entity_id))
            self._ensure_not_person_owned(storage, entity_id)
            del storage["data"]["schedules"][str(entity_id)]

        await self._mutate(mutate)

    async def exists(self, entity_id: UUID) -> bool:
        """Return whether a schedule exists for a UUID."""
        async with self._lock:
            await self._ensure_permanent()
            _, schedules = await self._load_schedules()
            return entity_id in schedules

    async def _load_schedules(
        self,
    ) -> tuple[HomePassStorageData, dict[UUID, Schedule]]:
        """Load and deserialize the schedules collection."""
        try:
            storage = await self._storage_manager.async_load()
            return storage, self._deserialize_schedules(storage)
        except StorageError:
            raise
        except Exception as err:
            raise StorageError("Unable to load HomePASS schedules") from err

    async def _ensure_permanent(self) -> None:
        """Repair the protected Schedule through the transaction boundary if needed."""
        try:
            storage = await self._storage_manager.async_load()
            permanent_record = self._serialize(permanent_schedule())
            if storage["data"]["schedules"].get(str(PERMANENT_SCHEDULE_ID)) == permanent_record:
                return

            def repair(working: HomePassStorageData) -> None:
                working["data"]["schedules"][str(PERMANENT_SCHEDULE_ID)] = permanent_record

            await self._storage_manager.async_transaction(repair)
        except Exception as err:
            raise StorageError("Unable to save HomePASS schedules") from err

    async def _mutate(self, mutator: Callable[[HomePassStorageData], None]) -> None:
        """Run one repository mutation in the shared storage transaction."""
        try:
            async with self._lock:
                await self._storage_manager.async_transaction(mutator)
        except (
            DuplicateScheduleError,
            ProtectedScheduleError,
            ScheduleNotFoundError,
            StorageError,
        ):
            raise
        except Exception as err:
            raise StorageError("Unable to save HomePASS schedules") from err

    @classmethod
    def _deserialize_schedules(
        cls,
        storage: HomePassStorageData,
        *,
        repair_permanent: bool = False,
    ) -> dict[UUID, Schedule]:
        """Deserialize Schedule records from one snapshot."""
        schedules: dict[UUID, Schedule] = {}
        for stored_id, record in storage["data"]["schedules"].items():
            if stored_id == str(PERMANENT_SCHEDULE_ID):
                continue
            schedule = Schedule.from_dict(record)
            if str(schedule.schedule_id) != stored_id:
                raise StorageError(f"Stored schedule identifier does not match record: {stored_id}")
            if schedule.name.casefold() == PERMANENT_SCHEDULE_NAME.casefold():
                raise StorageError("Stored user schedule uses the reserved Permanent name")
            schedules[schedule.schedule_id] = schedule
        permanent = permanent_schedule()
        if repair_permanent:
            storage["data"]["schedules"][str(PERMANENT_SCHEDULE_ID)] = cls._serialize(permanent)
        schedules[PERMANENT_SCHEDULE_ID] = permanent
        return schedules

    @staticmethod
    def _serialize(schedule: Schedule) -> StorageRecord:
        """Serialize a schedule for the storage collection."""
        return cast(StorageRecord, schedule.to_dict())

    @staticmethod
    def _ensure_unique(
        schedule: Schedule,
        schedules: dict[UUID, Schedule],
        *,
        exclude_id: UUID | None = None,
    ) -> None:
        """Ensure a schedule UUID and normalized name are unique."""
        if schedule.schedule_id in schedules and schedule.schedule_id != exclude_id:
            raise DuplicateScheduleError(str(schedule.schedule_id))
        normalized_name = schedule.name.casefold()
        if any(
            existing.schedule_id != exclude_id and existing.name.casefold() == normalized_name
            for existing in schedules.values()
        ):
            raise DuplicateScheduleError(schedule.name)

    @staticmethod
    def _ensure_not_person_owned(storage: HomePassStorageData, schedule_id: UUID) -> None:
        """Protect Schedules referenced by People or unrelated grant projections."""
        if any(
            Person.from_dict(record).schedule_id == schedule_id
            for record in storage["data"]["people"].values()
        ) or any(
            AccessGrant.from_dict(record).schedule_id == schedule_id
            for record in storage["data"]["access_grants"].values()
        ):
            raise ProtectedScheduleError(
                "Person-owned schedules must be changed through the Person Schedule service"
            )
