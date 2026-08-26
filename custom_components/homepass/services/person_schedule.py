"""Transactional application service for Person-owned Schedules."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID, uuid4

from ..exceptions import (
    ConcurrentPersonScheduleUpdateError,
    InvalidPersonScheduleReferenceError,
    PersonNotFoundError,
    ValidationError,
)
from ..models import AccessGrant, ActivityEventType, Person, Schedule, WeeklyRule
from ..models.schedule import PERMANENT_SCHEDULE_ID
from ..storage import HomePassStorageData, HomePassStorageManager, StorageRecord
from .activity_producer import ActivityProducer


@dataclass(frozen=True, slots=True)
class PersonScheduleState:
    """Consistent default Schedule and door Schedule Groups for one Person."""

    person: Person
    schedule: Schedule
    groups: tuple[PersonScheduleGroup, ...] = ()


@dataclass(frozen=True, slots=True)
class PersonScheduleGroup:
    """One reusable Schedule and the Person's doors that reference it."""

    schedule: Schedule
    access_point_ids: tuple[UUID, ...]


@dataclass(frozen=True, slots=True)
class _PersonScheduleSaveResult:
    schedule: Schedule
    person: Person
    changed: bool


class PersonScheduleService:
    """Resolve and transactionally mutate a Person's effective Schedule."""

    def __init__(
        self,
        storage_manager: HomePassStorageManager,
        activity_producer: ActivityProducer | None = None,
    ) -> None:
        """Initialize the service with the global storage boundary."""
        self._storage_manager = storage_manager
        self._activity_producer = activity_producer

    async def get_effective_schedule(self, person_id: UUID) -> Schedule:
        """Return a consistent Person Schedule or raise a typed domain error."""
        return (await self.get_schedule_state(person_id)).schedule

    async def get_schedule_state(self, person_id: UUID) -> PersonScheduleState:
        """Return the legacy default and all door groups from one snapshot."""
        storage = await self._storage_manager.async_load()
        schedule = self._resolve(storage, person_id)
        return PersonScheduleState(
            self._people(storage)[person_id],
            schedule,
            self._groups(storage, person_id),
        )

    async def save_person_schedule(
        self,
        person_id: UUID,
        *,
        time_zone: str,
        valid_from: datetime | None,
        valid_until: datetime | None,
        weekly_rules: Sequence[WeeklyRule],
        expected_person_updated_at: datetime,
        expected_schedule_id: UUID,
        expected_schedule_revision: int,
        enabled: bool = True,
        access_point_ids: Sequence[UUID] | None = None,
    ) -> Schedule:
        """Apply edited policy values to all grants or one selected door subset."""

        def mutate(storage: HomePassStorageData) -> _PersonScheduleSaveResult:
            people = self._people(storage)
            try:
                person = people[person_id]
            except KeyError as err:
                raise PersonNotFoundError(str(person_id)) from err
            schedules = self._schedules(storage)
            try:
                current = schedules[expected_schedule_id]
            except KeyError as err:
                raise InvalidPersonScheduleReferenceError(person_id) from err
            if (
                person.updated_at != expected_person_updated_at
                or current.revision != expected_schedule_revision
            ):
                raise ConcurrentPersonScheduleUpdateError(person_id, expected_person_updated_at)

            grants = tuple(grant for grant in self._grants(storage) if grant.person_id == person_id)
            owned_schedule_ids = {person.schedule_id, *(grant.schedule_id for grant in grants)}
            if expected_schedule_id not in owned_schedule_ids:
                raise ConcurrentPersonScheduleUpdateError(person_id, expected_person_updated_at)
            selected_ids = (
                {grant.access_point_id for grant in grants}
                if access_point_ids is None
                else set(access_point_ids)
            )
            if access_point_ids is not None:
                if not selected_ids or len(selected_ids) != len(access_point_ids):
                    raise ValidationError("Select one or more unique doors")
                grant_ids = {grant.access_point_id for grant in grants}
                if not selected_ids <= grant_ids:
                    raise ValidationError(
                        "One or more selected doors are not assigned to this User"
                    )
            rules = tuple(weekly_rules)
            if enabled and valid_from is None and valid_until is None and not rules:
                target = schedules[PERMANENT_SCHEDULE_ID]
            else:
                target = self._save_custom_policy(
                    storage,
                    person,
                    current,
                    selected_access_point_ids=selected_ids,
                    time_zone=time_zone,
                    enabled=enabled,
                    valid_from=valid_from,
                    valid_until=valid_until,
                    weekly_rules=rules,
                )

            policy_changed = (
                current.enabled != target.enabled
                or current.time_zone != target.time_zone
                or current.valid_from != target.valid_from
                or current.valid_until != target.valid_until
                or current.weekly_rules != target.weekly_rules
            )
            assignment_changed = any(
                grant.access_point_id in selected_ids and grant.schedule_id != target.schedule_id
                for grant in grants
            )
            changed = (
                policy_changed
                or assignment_changed
                or (access_point_ids is None and target.schedule_id != person.schedule_id)
            )

            now = max(datetime.now(UTC), person.updated_at + timedelta(microseconds=1))
            resulting_schedule_ids = {
                target.schedule_id if grant.access_point_id in selected_ids else grant.schedule_id
                for grant in grants
            }
            next_default = (
                target.schedule_id
                if access_point_ids is None or len(resulting_schedule_ids) == 1
                else person.schedule_id
            )
            updated_person = replace(person, schedule_id=next_default, updated_at=now)
            storage["data"]["people"][str(person_id)] = cast(
                StorageRecord, updated_person.to_dict()
            )
            for key, record in tuple(storage["data"]["access_grants"].items()):
                grant = AccessGrant.from_dict(record)
                if grant.person_id == person_id and grant.access_point_id in selected_ids:
                    updated_grant = replace(
                        grant,
                        schedule_id=target.schedule_id,
                        updated_at=max(now, grant.updated_at + timedelta(microseconds=1)),
                    )
                    storage["data"]["access_grants"][key] = cast(
                        StorageRecord, updated_grant.to_dict()
                    )
            return _PersonScheduleSaveResult(target, updated_person, changed)

        result = await self._storage_manager.async_transaction(mutate)
        if result.changed and self._activity_producer is not None:
            await self._activity_producer.record(
                ActivityEventType.SCHEDULE_CHANGED,
                occurred_at=result.person.updated_at,
                source_event_key=(
                    f"person-schedule:{person_id}:{result.person.updated_at.isoformat()}"
                ),
                person=result.person,
                attributes={"schedule_name": result.schedule.name},
            )
        return result.schedule

    def _save_custom_policy(
        self,
        storage: HomePassStorageData,
        person: Person,
        current: Schedule,
        *,
        selected_access_point_ids: set[UUID],
        time_zone: str,
        enabled: bool,
        valid_from: datetime | None,
        valid_until: datetime | None,
        weekly_rules: tuple[WeeklyRule, ...],
    ) -> Schedule:
        """Update an exclusive custom Schedule or create an isolated replacement."""
        schedules = self._schedules(storage)
        shared = current.schedule_id == PERMANENT_SCHEDULE_ID or self._is_shared_outside_selection(
            storage,
            person.person_id,
            current.schedule_id,
            selected_access_point_ids,
        )
        schedule_id = uuid4() if shared else current.schedule_id
        name = (
            self._unique_name(person.display_name, schedule_id, schedules)
            if shared
            else current.name
        )
        created_at = datetime.now(UTC) if shared else current.created_at
        policy_changed = (
            current.enabled != enabled
            or current.time_zone != time_zone
            or current.valid_from != valid_from
            or current.valid_until != valid_until
            or current.weekly_rules != weekly_rules
        )
        revision = 1 if shared else current.revision + int(policy_changed)
        updated_at = (
            created_at
            if shared
            else max(datetime.now(UTC), current.updated_at + timedelta(microseconds=1))
        )
        try:
            schedule = Schedule(
                schedule_id=schedule_id,
                name=name,
                enabled=enabled,
                time_zone=time_zone,
                valid_from=valid_from,
                valid_until=valid_until,
                weekly_rules=weekly_rules,
                revision=revision,
                created_at=created_at,
                updated_at=updated_at,
            )
        except (TypeError, ValueError) as err:
            raise ValidationError(str(err)) from err
        storage["data"]["schedules"][str(schedule.schedule_id)] = cast(
            StorageRecord, schedule.to_dict()
        )
        return schedule

    @classmethod
    def _resolve(cls, storage: HomePassStorageData, person_id: UUID) -> Schedule:
        record = storage["data"]["people"].get(str(person_id))
        if record is None:
            raise PersonNotFoundError(str(person_id))
        try:
            raw_schedule_id = record.get("schedule_id")
            if not isinstance(raw_schedule_id, str):
                raise ValueError
            UUID(raw_schedule_id)
            person = Person.from_dict(record)
        except (TypeError, ValueError) as err:
            raise InvalidPersonScheduleReferenceError(person_id) from err
        schedules = cls._schedules(storage)
        try:
            schedule = schedules[person.schedule_id]
        except KeyError as err:
            raise InvalidPersonScheduleReferenceError(person_id) from err
        grants = cls._grants(storage)
        references = {person.schedule_id}
        references.update(grant.schedule_id for grant in grants if grant.person_id == person_id)
        missing = references - schedules.keys()
        if missing:
            raise InvalidPersonScheduleReferenceError(person_id)
        return schedule

    @classmethod
    def _groups(
        cls,
        storage: HomePassStorageData,
        person_id: UUID,
    ) -> tuple[PersonScheduleGroup, ...]:
        """Group the Person's grants by their authoritative Schedule reference."""
        schedules = cls._schedules(storage)
        grouped: dict[UUID, list[UUID]] = {}
        for grant in cls._grants(storage):
            if grant.person_id != person_id:
                continue
            if grant.schedule_id not in schedules:
                raise InvalidPersonScheduleReferenceError(person_id)
            grouped.setdefault(grant.schedule_id, []).append(grant.access_point_id)
        return tuple(
            PersonScheduleGroup(
                schedules[schedule_id],
                tuple(sorted(access_point_ids, key=str)),
            )
            for schedule_id, access_point_ids in sorted(
                grouped.items(),
                key=lambda item: (
                    item[0] != PERMANENT_SCHEDULE_ID,
                    schedules[item[0]].name.casefold(),
                    str(item[0]),
                ),
            )
        )

    @staticmethod
    def _people(storage: HomePassStorageData) -> dict[UUID, Person]:
        return {
            person.person_id: person
            for record in storage["data"]["people"].values()
            for person in (Person.from_dict(record),)
        }

    @staticmethod
    def _schedules(storage: HomePassStorageData) -> dict[UUID, Schedule]:
        return {
            schedule.schedule_id: schedule
            for record in storage["data"]["schedules"].values()
            for schedule in (Schedule.from_dict(record),)
        }

    @staticmethod
    def _grants(storage: HomePassStorageData) -> tuple[AccessGrant, ...]:
        return tuple(
            AccessGrant.from_dict(record) for record in storage["data"]["access_grants"].values()
        )

    @classmethod
    def _is_shared_outside_selection(
        cls,
        storage: HomePassStorageData,
        person_id: UUID,
        schedule_id: UUID,
        selected_access_point_ids: set[UUID],
    ) -> bool:
        """Return whether editing in place could affect an unselected owner."""
        if any(
            other.person_id != person_id and other.schedule_id == schedule_id
            for other in cls._people(storage).values()
        ):
            return True
        return any(
            grant.schedule_id == schedule_id
            and (
                grant.person_id != person_id
                or grant.access_point_id not in selected_access_point_ids
            )
            for grant in cls._grants(storage)
        )

    @staticmethod
    def _unique_name(display_name: str, schedule_id: UUID, schedules: dict[UUID, Schedule]) -> str:
        base = f"{display_name} Schedule"
        names = {schedule.name.casefold() for schedule in schedules.values()}
        if base.casefold() not in names:
            return base
        identifier = str(schedule_id)
        for length in range(8, len(identifier) + 1):
            candidate = f"{base} {identifier[:length]}"
            if candidate.casefold() not in names:
                return candidate
        raise ValidationError("Unable to generate a unique Person Schedule name")
