"""Pure domain evaluation for ordinary HomePASS Schedule policies."""

from __future__ import annotations

from datetime import UTC, datetime, time
from enum import StrEnum
from zoneinfo import ZoneInfo

from .schedule import DayOfWeek, Schedule, WeeklyRule


class ScheduleEvaluation(StrEnum):
    """Sanitized reason produced by evaluating one Schedule at one instant."""

    ACTIVE = "active"
    DISABLED = "disabled"
    NOT_YET_VALID = "not_yet_valid"
    EXPIRED = "expired"
    OUTSIDE_WEEKLY_RULE = "outside_weekly_rule"

    @property
    def active(self) -> bool:
        """Return whether the Schedule authorizes the evaluated instant."""
        return self is ScheduleEvaluation.ACTIVE


def evaluate_schedule(schedule: Schedule, instant_utc: datetime) -> ScheduleEvaluation:
    """Evaluate an ordinary Schedule policy at one timezone-aware instant.

    SCHEDULE-004A intentionally excludes DST gap, overlap, and duration-cap semantics.
    """
    if instant_utc.tzinfo is None or instant_utc.utcoffset() is None:
        raise ValueError("Schedule evaluation instant must be timezone-aware")

    instant = instant_utc.astimezone(UTC)
    if not schedule.enabled:
        return ScheduleEvaluation.DISABLED
    if schedule.valid_from is not None and instant < schedule.valid_from:
        return ScheduleEvaluation.NOT_YET_VALID
    if schedule.valid_until is not None and instant >= schedule.valid_until:
        return ScheduleEvaluation.EXPIRED
    if not schedule.weekly_rules:
        return ScheduleEvaluation.ACTIVE

    local_instant = instant.astimezone(ZoneInfo(schedule.time_zone))
    local_day = DayOfWeek(local_instant.isoweekday())
    local_time = local_instant.time()
    if any(_rule_matches(rule, local_day, local_time) for rule in schedule.weekly_rules):
        return ScheduleEvaluation.ACTIVE
    return ScheduleEvaluation.OUTSIDE_WEEKLY_RULE


def _rule_matches(rule: WeeklyRule, local_day: DayOfWeek, local_time: time) -> bool:
    """Return whether an ordinary local weekday and time match one weekly rule."""
    if rule.start_time < rule.end_time:
        return local_day == rule.day_of_week and rule.start_time <= local_time < rule.end_time

    following_day = DayOfWeek(rule.day_of_week % len(DayOfWeek) + 1)
    return (local_day == rule.day_of_week and local_time >= rule.start_time) or (
        local_day == following_day and local_time < rule.end_time
    )
