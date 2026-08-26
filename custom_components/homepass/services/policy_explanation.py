"""Presentation-ready explanation for one denied authorization relationship."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time
from typing import Literal, TypedDict
from uuid import UUID
from zoneinfo import ZoneInfo

from ..exceptions import PolicyExplanationUnavailableError
from ..models import AuthorizationDecision, DayOfWeek, Schedule, WeeklyRule
from .authorization import AuthorizationService
from .authorization_presentation import authorization_explanation

type WeeklyHoursKind = Literal["always", "simple", "advanced"]

_MONTH_NAMES = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)


class PolicyValidityData(TypedDict):
    """Homeowner-facing absolute validity presentation."""

    summary: str
    valid_from: str | None
    valid_until: str | None


class PolicyWeeklyHoursData(TypedDict):
    """Homeowner-facing weekly-hours presentation."""

    kind: WeeklyHoursKind
    summary: str
    days: str | None
    hours: str | None


class PolicyCurrentLocalData(TypedDict):
    """Evaluation instant rendered in the Schedule timezone."""

    day: str
    date: str
    time: str
    time_zone: str


class PolicyExplanationData(TypedDict):
    """Serialized policy explanation without internal identifiers."""

    title: str
    reason: str
    person_name: str
    door_name: str
    schedule_name: str
    validity: PolicyValidityData
    weekly_hours: PolicyWeeklyHoursData
    current_local: PolicyCurrentLocalData


@dataclass(frozen=True, slots=True)
class PolicyValidity:
    """Absolute validity formatted for direct presentation."""

    summary: str
    valid_from: str | None
    valid_until: str | None

    def to_dict(self) -> PolicyValidityData:
        """Serialize absolute validity."""
        return {
            "summary": self.summary,
            "valid_from": self.valid_from,
            "valid_until": self.valid_until,
        }


@dataclass(frozen=True, slots=True)
class PolicyWeeklyHours:
    """Weekly policy formatted without flattening advanced rules."""

    kind: WeeklyHoursKind
    summary: str
    days: str | None = None
    hours: str | None = None

    def to_dict(self) -> PolicyWeeklyHoursData:
        """Serialize weekly hours."""
        return {
            "kind": self.kind,
            "summary": self.summary,
            "days": self.days,
            "hours": self.hours,
        }


@dataclass(frozen=True, slots=True)
class PolicyCurrentLocal:
    """Current evaluation time formatted in the policy timezone."""

    day: str
    date: str
    time: str
    time_zone: str

    def to_dict(self) -> PolicyCurrentLocalData:
        """Serialize the local evaluation instant."""
        return {
            "day": self.day,
            "date": self.date,
            "time": self.time,
            "time_zone": self.time_zone,
        }


@dataclass(frozen=True, slots=True)
class PolicyExplanation:
    """Safe explanation of one denied Person-to-Door relationship."""

    reason: str
    person_name: str
    door_name: str
    schedule_name: str
    validity: PolicyValidity
    weekly_hours: PolicyWeeklyHours
    current_local: PolicyCurrentLocal

    def to_dict(self) -> PolicyExplanationData:
        """Serialize only presentation-ready values."""
        return {
            "title": "Access unavailable",
            "reason": self.reason,
            "person_name": self.person_name,
            "door_name": self.door_name,
            "schedule_name": self.schedule_name,
            "validity": self.validity.to_dict(),
            "weekly_hours": self.weekly_hours.to_dict(),
            "current_local": self.current_local.to_dict(),
        }


class PolicyExplanationService:
    """Explain one denied relationship using AuthorizationService's single snapshot."""

    def __init__(self, authorization_service: AuthorizationService) -> None:
        """Initialize with the existing authorization application boundary."""
        self._authorization_service = authorization_service

    async def explain_denied_access(
        self,
        *,
        person_id: UUID,
        access_point_id: UUID,
        instant_utc: datetime,
    ) -> PolicyExplanation:
        """Return a safe explanation for the selected relationship and instant."""
        relationship = await self._authorization_service.resolve_person_for_access_point(
            person_id=person_id,
            access_point_id=access_point_id,
            instant_utc=instant_utc,
        )
        if relationship.decision is AuthorizationDecision.ALLOWED:
            raise PolicyExplanationUnavailableError(
                "An allowed relationship has no denial explanation"
            )
        schedule = relationship.schedule
        return PolicyExplanation(
            reason=authorization_explanation(relationship.decision),
            person_name=relationship.person.display_name,
            door_name=relationship.access_point.display_name,
            schedule_name=schedule.name,
            validity=_format_validity(schedule),
            weekly_hours=_format_weekly_hours(schedule.weekly_rules),
            current_local=_format_current_local(schedule, instant_utc),
        )


def _format_validity(schedule: Schedule) -> PolicyValidity:
    """Format exact absolute bounds in the Schedule timezone."""
    if schedule.valid_from is None and schedule.valid_until is None:
        return PolicyValidity("Permanent", None, None)
    zone = ZoneInfo(schedule.time_zone)
    valid_from = (
        None
        if schedule.valid_from is None
        else _format_local_datetime(schedule.valid_from.astimezone(zone))
    )
    valid_until = (
        None
        if schedule.valid_until is None
        else _format_local_datetime(schedule.valid_until.astimezone(zone))
    )
    return PolicyValidity("Limited dates", valid_from, valid_until)


def _format_weekly_hours(rules: tuple[WeeklyRule, ...]) -> PolicyWeeklyHours:
    """Format the builder-safe subset or explicitly identify advanced rules."""
    if not rules:
        return PolicyWeeklyHours("always", "24-hour access")
    intervals = {(rule.start_time, rule.end_time) for rule in rules}
    days = [rule.day_of_week for rule in rules]
    simple = (
        len(intervals) == 1
        and len(days) == len(set(days))
        and all(rule.start_time < rule.end_time for rule in rules)
    )
    if not simple:
        return PolicyWeeklyHours("advanced", "This schedule contains advanced rules.")
    start, end = next(iter(intervals))
    return PolicyWeeklyHours(
        "simple",
        "Scheduled access",
        days=_format_days(tuple(days)),
        hours=f"{_format_clock_time(start)}–{_format_clock_time(end)}",
    )


def _format_current_local(schedule: Schedule, instant_utc: datetime) -> PolicyCurrentLocal:
    """Render the explicit evaluation instant in the Schedule timezone."""
    if instant_utc.tzinfo is None or instant_utc.utcoffset() is None:
        raise ValueError("Policy explanation instant must be timezone-aware")
    local = instant_utc.astimezone(ZoneInfo(schedule.time_zone))
    return PolicyCurrentLocal(
        day=DayOfWeek(local.isoweekday()).name.title(),
        date=_format_date(local),
        time=_format_clock_time(local.timetz().replace(tzinfo=None)),
        time_zone=schedule.time_zone.replace("_", " "),
    )


def _format_days(days: tuple[DayOfWeek, ...]) -> str:
    """Format selected ISO weekdays as compact contiguous ranges."""
    ordered = sorted(set(days), key=int)
    if len(ordered) == len(DayOfWeek):
        return "Every day"
    runs: list[list[DayOfWeek]] = []
    for day in ordered:
        if not runs or int(day) != int(runs[-1][-1]) + 1:
            runs.append([day])
        else:
            runs[-1].append(day)
    labels = [
        run[0].name.title() if len(run) == 1 else f"{run[0].name.title()}–{run[-1].name.title()}"
        for run in runs
    ]
    if len(labels) == 1:
        return labels[0]
    if len(labels) == 2:
        return " and ".join(labels)
    return f"{', '.join(labels[:-1])}, and {labels[-1]}"


def _format_local_datetime(value: datetime) -> str:
    """Format one local date/time without platform-specific directives."""
    return f"{_format_date(value)} at {_format_clock_time(value.timetz().replace(tzinfo=None))}"


def _format_date(value: datetime) -> str:
    """Format a homeowner-facing Gregorian date."""
    return f"{_MONTH_NAMES[value.month - 1]} {value.day}, {value.year}"


def _format_clock_time(value: time) -> str:
    """Format a local clock time using 12-hour homeowner notation."""
    suffix = "AM" if value.hour < 12 else "PM"
    hour = value.hour % 12 or 12
    return f"{hour}:{value.minute:02d} {suffix}"


__all__ = [
    "PolicyCurrentLocal",
    "PolicyExplanation",
    "PolicyExplanationService",
    "PolicyValidity",
    "PolicyWeeklyHours",
    "WeeklyHoursKind",
]
