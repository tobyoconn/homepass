"""Schedule domain model."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, time
from enum import IntEnum
from typing import Self, TypedDict
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

PERMANENT_SCHEDULE_NAME = "Permanent"
# UUIDv5 keeps the reserved system identity stable across installations without storing a
# deployment-specific seed. NAMESPACE_URL matches existing deterministic HomePASS IDs.
PERMANENT_SCHEDULE_ID = uuid5(NAMESPACE_URL, "homepass:system-schedule:permanent")
_PERMANENT_SCHEDULE_TIMESTAMP = datetime(2026, 7, 17, tzinfo=UTC)


class DayOfWeek(IntEnum):
    """ISO weekday on which a weekly rule begins."""

    MONDAY = 1
    TUESDAY = 2
    WEDNESDAY = 3
    THURSDAY = 4
    FRIDAY = 5
    SATURDAY = 6
    SUNDAY = 7


class WeeklyRuleData(TypedDict):
    """JSON-compatible representation of a weekly rule."""

    day_of_week: int
    start_time: str
    end_time: str


class ScheduleData(TypedDict):
    """JSON-compatible representation of a schedule."""

    schedule_id: str
    name: str
    enabled: bool
    time_zone: str
    valid_from: str | None
    valid_until: str | None
    weekly_rules: list[WeeklyRuleData]
    revision: int
    created_at: str
    updated_at: str


def _utcnow() -> datetime:
    """Return the current UTC time."""
    return datetime.now(UTC)


def _required(data: Mapping[str, object], field_name: str) -> object:
    """Return a required serialized field."""
    try:
        return data[field_name]
    except KeyError as err:
        raise ValueError(f"Missing required Schedule field: {field_name}") from err


def _normalize_datetime(value: datetime, field_name: str) -> datetime:
    """Validate a datetime and normalize it to UTC."""
    if not isinstance(value, datetime):
        raise TypeError(f"Schedule {field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"Schedule {field_name} must be timezone-aware")
    return value.astimezone(UTC)


def _parse_datetime(value: object, field_name: str) -> datetime:
    """Parse a serialized datetime."""
    if not isinstance(value, str):
        raise TypeError(f"Schedule {field_name} must be an ISO 8601 string")
    try:
        return datetime.fromisoformat(value)
    except ValueError as err:
        raise ValueError(f"Schedule {field_name} must be a valid ISO 8601 datetime") from err


def _parse_optional_datetime(value: object, field_name: str) -> datetime | None:
    """Parse an optional serialized datetime."""
    if value is None:
        return None
    return _parse_datetime(value, field_name)


def _format_time(value: time) -> str:
    """Serialize a minute-precision local time."""
    return value.isoformat(timespec="minutes")


def _parse_time(value: object, field_name: str) -> time:
    """Parse a serialized local time."""
    if not isinstance(value, str):
        raise TypeError(f"WeeklyRule {field_name} must be an ISO 8601 time string")
    try:
        return time.fromisoformat(value)
    except ValueError as err:
        raise ValueError(f"WeeklyRule {field_name} must be a valid ISO 8601 time") from err


@dataclass(frozen=True, slots=True)
class WeeklyRule:
    """An immutable recurring local-time interval."""

    day_of_week: DayOfWeek
    start_time: time
    end_time: time

    def __post_init__(self) -> None:
        """Validate the weekly interval."""
        if not isinstance(self.day_of_week, DayOfWeek):
            raise TypeError("WeeklyRule day_of_week must be a DayOfWeek")
        for field_name in ("start_time", "end_time"):
            value = getattr(self, field_name)
            if not isinstance(value, time):
                raise TypeError(f"WeeklyRule {field_name} must be a time")
            if value.tzinfo is not None:
                raise ValueError(f"WeeklyRule {field_name} must be a local time without timezone")
            if value.second != 0 or value.microsecond != 0:
                raise ValueError(f"WeeklyRule {field_name} must use minute precision")
        if self.start_time == self.end_time:
            raise ValueError("WeeklyRule start_time and end_time must not be equal")

    def to_dict(self) -> WeeklyRuleData:
        """Serialize the weekly rule."""
        return {
            "day_of_week": self.day_of_week.value,
            "start_time": _format_time(self.start_time),
            "end_time": _format_time(self.end_time),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> Self:
        """Deserialize and validate a weekly rule."""
        day = _required(data, "day_of_week")
        if isinstance(day, bool) or not isinstance(day, int):
            raise TypeError("WeeklyRule day_of_week must be an integer")
        try:
            day_of_week = DayOfWeek(day)
        except ValueError as err:
            raise ValueError("WeeklyRule day_of_week must be an ISO weekday from 1 to 7") from err
        return cls(
            day_of_week=day_of_week,
            start_time=_parse_time(_required(data, "start_time"), "start_time"),
            end_time=_parse_time(_required(data, "end_time"), "end_time"),
        )


def _minute_of_day(value: time) -> int:
    """Return a minute offset for a validated local time."""
    return value.hour * 60 + value.minute


def _rule_segments(rule: WeeklyRule) -> tuple[tuple[int, int], ...]:
    """Expand a rule into non-wrapping segments in an ISO week."""
    week_minutes = 7 * 24 * 60
    start = (rule.day_of_week.value - 1) * 24 * 60 + _minute_of_day(rule.start_time)
    end = (rule.day_of_week.value - 1) * 24 * 60 + _minute_of_day(rule.end_time)
    if end <= start:
        end += 24 * 60
    if end <= week_minutes:
        return ((start, end),)
    return ((start, week_minutes), (0, end - week_minutes))


def _validate_rules(rules: tuple[WeeklyRule, ...]) -> None:
    """Reject duplicate or overlapping weekly intervals."""
    if len(set(rules)) != len(rules):
        raise ValueError("Schedule weekly_rules must not contain duplicates")
    segments = sorted(segment for rule in rules for segment in _rule_segments(rule))
    if any(
        current[0] < previous[1] for previous, current in zip(segments, segments[1:], strict=False)
    ):
        raise ValueError("Schedule weekly_rules must not overlap")


@dataclass(frozen=True, slots=True)
class Schedule:
    """An immutable reusable HomePASS time policy."""

    name: str
    time_zone: str
    schedule_id: UUID = field(default_factory=uuid4)
    enabled: bool = True
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    weekly_rules: tuple[WeeklyRule, ...] = ()
    revision: int = 1
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)

    def __post_init__(self) -> None:
        """Validate and canonicalize the schedule."""
        if not isinstance(self.schedule_id, UUID):
            raise TypeError("Schedule schedule_id must be a UUID")
        if not isinstance(self.name, str):
            raise TypeError("Schedule name must be a string")
        name = self.name.strip()
        if not name:
            raise ValueError("Schedule name must not be empty")
        if not isinstance(self.enabled, bool):
            raise TypeError("Schedule enabled must be a boolean")
        if not isinstance(self.time_zone, str):
            raise TypeError("Schedule time_zone must be a string")
        if not self.time_zone or self.time_zone != self.time_zone.strip():
            raise ValueError("Schedule time_zone must be a valid IANA timezone")
        try:
            ZoneInfo(self.time_zone)
        except (ZoneInfoNotFoundError, ValueError) as err:
            raise ValueError("Schedule time_zone must be a valid IANA timezone") from err
        if isinstance(self.revision, bool) or not isinstance(self.revision, int):
            raise TypeError("Schedule revision must be an integer")
        if self.revision < 1:
            raise ValueError("Schedule revision must be positive")
        raw_rules: object = self.weekly_rules
        if not isinstance(raw_rules, Sequence) or isinstance(raw_rules, str | bytes):
            raise TypeError("Schedule weekly_rules must be a sequence of WeeklyRule values")
        rules = tuple(raw_rules)
        if not all(isinstance(rule, WeeklyRule) for rule in rules):
            raise TypeError("Schedule weekly_rules must contain only WeeklyRule values")
        rules = tuple(
            sorted(
                rules,
                key=lambda rule: (
                    rule.day_of_week.value,
                    rule.start_time,
                    rule.end_time,
                ),
            )
        )
        _validate_rules(rules)

        valid_from = (
            None if self.valid_from is None else _normalize_datetime(self.valid_from, "valid_from")
        )
        valid_until = (
            None
            if self.valid_until is None
            else _normalize_datetime(self.valid_until, "valid_until")
        )
        if valid_from is not None and valid_until is not None and valid_until <= valid_from:
            raise ValueError("Schedule valid_until must be later than valid_from")
        created_at = _normalize_datetime(self.created_at, "created_at")
        updated_at = _normalize_datetime(self.updated_at, "updated_at")
        if updated_at < created_at:
            raise ValueError("Schedule updated_at must not be earlier than created_at")

        object.__setattr__(self, "name", name)
        object.__setattr__(self, "weekly_rules", rules)
        object.__setattr__(self, "valid_from", valid_from)
        object.__setattr__(self, "valid_until", valid_until)
        object.__setattr__(self, "created_at", created_at)
        object.__setattr__(self, "updated_at", updated_at)

    def to_dict(self) -> ScheduleData:
        """Serialize the schedule to JSON-compatible data."""
        return {
            "schedule_id": str(self.schedule_id),
            "name": self.name,
            "enabled": self.enabled,
            "time_zone": self.time_zone,
            "valid_from": None if self.valid_from is None else self.valid_from.isoformat(),
            "valid_until": None if self.valid_until is None else self.valid_until.isoformat(),
            "weekly_rules": [rule.to_dict() for rule in self.weekly_rules],
            "revision": self.revision,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> Self:
        """Deserialize and validate a schedule."""
        raw_id = _required(data, "schedule_id")
        if not isinstance(raw_id, str):
            raise TypeError("Schedule schedule_id must be a UUID string")
        try:
            schedule_id = UUID(raw_id)
        except ValueError as err:
            raise ValueError("Schedule schedule_id must be a valid UUID") from err
        raw_rules = _required(data, "weekly_rules")
        if not isinstance(raw_rules, list):
            raise TypeError("Schedule weekly_rules must be a list")
        if not all(isinstance(rule, Mapping) for rule in raw_rules):
            raise TypeError("Schedule weekly_rules must contain objects")
        name = _required(data, "name")
        enabled = _required(data, "enabled")
        time_zone = _required(data, "time_zone")
        revision = _required(data, "revision")
        if not isinstance(name, str):
            raise TypeError("Schedule name must be a string")
        if not isinstance(enabled, bool):
            raise TypeError("Schedule enabled must be a boolean")
        if not isinstance(time_zone, str):
            raise TypeError("Schedule time_zone must be a string")
        if isinstance(revision, bool) or not isinstance(revision, int):
            raise TypeError("Schedule revision must be an integer")
        return cls(
            schedule_id=schedule_id,
            name=name,
            enabled=enabled,
            time_zone=time_zone,
            valid_from=_parse_optional_datetime(_required(data, "valid_from"), "valid_from"),
            valid_until=_parse_optional_datetime(_required(data, "valid_until"), "valid_until"),
            weekly_rules=tuple(WeeklyRule.from_dict(rule) for rule in raw_rules),
            revision=revision,
            created_at=_parse_datetime(_required(data, "created_at"), "created_at"),
            updated_at=_parse_datetime(_required(data, "updated_at"), "updated_at"),
        )


def permanent_schedule() -> Schedule:
    """Return the deterministic protected system schedule."""
    return Schedule(
        schedule_id=PERMANENT_SCHEDULE_ID,
        name=PERMANENT_SCHEDULE_NAME,
        enabled=True,
        time_zone="UTC",
        valid_from=None,
        valid_until=None,
        weekly_rules=(),
        revision=1,
        created_at=_PERMANENT_SCHEDULE_TIMESTAMP,
        updated_at=_PERMANENT_SCHEDULE_TIMESTAMP,
    )
