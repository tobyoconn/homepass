"""Translate HomePASS schedules at the provider boundary."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .base import AuthorizationSchedule

if TYPE_CHECKING:
    from ..models import Schedule


def authorization_schedule_from_homepass(schedule: Schedule) -> AuthorizationSchedule:
    """Map the schedule subset supported by physical keypad providers."""
    windows = {(rule.start_time, rule.end_time) for rule in schedule.weekly_rules}
    if len(windows) > 1:
        raise ValueError(
            "This provider supports one recurring time window shared by selected weekdays"
        )
    from_minute: int | None = None
    until_minute: int | None = None
    if windows:
        start_time, end_time = next(iter(windows))
        from_minute = start_time.hour * 60 + start_time.minute
        until_minute = end_time.hour * 60 + end_time.minute
        if until_minute <= from_minute:
            raise ValueError("This provider does not support overnight recurring access windows")
    return AuthorizationSchedule(
        valid_from=schedule.valid_from,
        valid_until=schedule.valid_until,
        weekdays=frozenset(rule.day_of_week.value for rule in schedule.weekly_rules),
        from_minute=from_minute,
        until_minute=until_minute,
    )


__all__ = ["authorization_schedule_from_homepass"]
