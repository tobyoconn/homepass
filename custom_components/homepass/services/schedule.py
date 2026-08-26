"""Schedule application service for HomePASS."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from enum import Enum
from uuid import UUID, uuid4

from ..exceptions import ValidationError
from ..models import ActivityEventType, Schedule, WeeklyRule
from ..repositories.schedule import ScheduleRepository
from .activity_producer import ActivityProducer


class _Unset(Enum):
    """Distinguish omitted update fields from explicit null validity bounds."""

    VALUE = "unset"


UNSET = _Unset.VALUE
type ScheduleField[T] = T | _Unset


class ScheduleService:
    """Coordinate application operations for reusable schedules."""

    def __init__(
        self,
        repository: ScheduleRepository,
        activity_producer: ActivityProducer | None = None,
    ) -> None:
        """Initialize the service with its Schedule repository."""
        self._repository = repository
        self._activity_producer = activity_producer

    async def create_schedule(
        self,
        name: str,
        time_zone: str,
        *,
        enabled: bool = True,
        valid_from: datetime | None = None,
        valid_until: datetime | None = None,
        weekly_rules: Sequence[WeeklyRule] = (),
    ) -> Schedule:
        """Create and persist a validated schedule."""
        schedule = self._build_schedule(
            name=name,
            time_zone=time_zone,
            enabled=enabled,
            valid_from=valid_from,
            valid_until=valid_until,
            weekly_rules=weekly_rules,
        )
        await self._repository.add(schedule)
        await self._record_activity(ActivityEventType.SCHEDULE_CREATED, schedule)
        return schedule

    async def update_schedule(
        self,
        schedule_id: UUID,
        *,
        name: ScheduleField[str] = UNSET,
        time_zone: ScheduleField[str] = UNSET,
        enabled: ScheduleField[bool] = UNSET,
        valid_from: ScheduleField[datetime | None] = UNSET,
        valid_until: ScheduleField[datetime | None] = UNSET,
        weekly_rules: ScheduleField[Sequence[WeeklyRule]] = UNSET,
    ) -> Schedule:
        """Create and persist an updated immutable schedule snapshot."""
        current = await self._repository.get(schedule_id)
        next_name = current.name if name is UNSET else name
        next_time_zone = current.time_zone if time_zone is UNSET else time_zone
        next_enabled = current.enabled if enabled is UNSET else enabled
        next_valid_from = current.valid_from if valid_from is UNSET else valid_from
        next_valid_until = current.valid_until if valid_until is UNSET else valid_until
        next_weekly_rules = current.weekly_rules if weekly_rules is UNSET else weekly_rules
        anything_changed = not (
            next_name == current.name
            and next_time_zone == current.time_zone
            and next_enabled == current.enabled
            and next_valid_from == current.valid_from
            and next_valid_until == current.valid_until
            and tuple(next_weekly_rules) == current.weekly_rules
        )
        policy_changed = (
            next_enabled != current.enabled
            or next_time_zone != current.time_zone
            or next_valid_from != current.valid_from
            or next_valid_until != current.valid_until
            or tuple(next_weekly_rules) != current.weekly_rules
        )
        updated = self._build_schedule(
            schedule_id=current.schedule_id,
            name=next_name,
            time_zone=next_time_zone,
            enabled=next_enabled,
            valid_from=next_valid_from,
            valid_until=next_valid_until,
            weekly_rules=next_weekly_rules,
            revision=current.revision + int(policy_changed),
            created_at=current.created_at,
            updated_at=max(datetime.now(UTC), current.updated_at + timedelta(microseconds=1)),
        )
        await self._repository.update(updated)
        if anything_changed:
            await self._record_activity(ActivityEventType.SCHEDULE_UPDATED, updated)
        return updated

    async def delete_schedule(self, schedule_id: UUID) -> None:
        """Delete a schedule."""
        schedule = await self._repository.get(schedule_id)
        await self._repository.remove(schedule_id)
        await self._record_activity(
            ActivityEventType.SCHEDULE_REMOVED,
            schedule,
            occurred_at=datetime.now(UTC),
        )

    async def get_schedule(self, schedule_id: UUID) -> Schedule:
        """Return a schedule."""
        return await self._repository.get(schedule_id)

    async def list_schedules(self) -> tuple[Schedule, ...]:
        """Return all schedules in repository order."""
        return await self._repository.list_all()

    async def _record_activity(
        self,
        event_type: ActivityEventType,
        schedule: Schedule,
        *,
        occurred_at: datetime | None = None,
    ) -> None:
        if self._activity_producer is None:
            return
        await self._activity_producer.record(
            event_type,
            occurred_at=schedule.updated_at if occurred_at is None else occurred_at,
            source_event_key=(
                f"schedule:{schedule.schedule_id}:{event_type.value}:"
                f"{schedule.updated_at.isoformat()}"
            ),
            attributes={"schedule_name": schedule.name},
        )

    @staticmethod
    def _build_schedule(
        *,
        name: str,
        time_zone: str,
        schedule_id: UUID | None = None,
        enabled: bool = True,
        valid_from: datetime | None = None,
        valid_until: datetime | None = None,
        weekly_rules: Sequence[WeeklyRule] = (),
        revision: int = 1,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> Schedule:
        """Build a validated schedule and expose domain validation errors."""
        default_time = datetime.now(UTC)
        try:
            return Schedule(
                schedule_id=uuid4() if schedule_id is None else schedule_id,
                name=name,
                enabled=enabled,
                time_zone=time_zone,
                valid_from=valid_from,
                valid_until=valid_until,
                weekly_rules=tuple(weekly_rules),
                revision=revision,
                created_at=default_time if created_at is None else created_at,
                updated_at=default_time if updated_at is None else updated_at,
            )
        except (TypeError, ValueError) as err:
            raise ValidationError(str(err)) from err
