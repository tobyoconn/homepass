"""Home Assistant actions for guided User setup and add-only door assignment."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime, time
from typing import cast
from uuid import NAMESPACE_URL, UUID, uuid5
from zoneinfo import ZoneInfo

import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse, callback
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.util.json import JsonObjectType

from .const import (
    ATTR_ACCESS_POINT_IDS,
    ATTR_DESCRIPTION,
    ATTR_DISPLAY_NAME,
    ATTR_ENABLED,
    ATTR_NOTES,
    ATTR_PERSON_ID,
    ATTR_PIN,
    ATTR_REQUEST_ID,
    ATTR_SCHEDULE_ID,
    DOMAIN,
    SERVICE_ASSIGN_USER_ACCESS,
    SERVICE_CREATE_USER,
    SERVICE_GET_USER_SETUP_OPTIONS,
)
from .exceptions import DuplicatePersonError, PersonNotFoundError
from .models import DayOfWeek, Schedule, WeeklyRule
from .models.person import MAX_PERSON_DESCRIPTION_LENGTH
from .models.schedule import PERMANENT_SCHEDULE_ID
from .services import UserSetupResult, UserSetupService

ATTR_SCHEDULE = "schedule"
USER_SETUP_ACTIONS = (
    SERVICE_CREATE_USER,
    SERVICE_GET_USER_SETUP_OPTIONS,
    SERVICE_ASSIGN_USER_ACCESS,
)


def _uuid(value: object, field: str) -> UUID:
    try:
        return UUID(cv.string(value))
    except ValueError:
        raise vol.Invalid(f"{field} must be a UUID") from None


def _description(value: object) -> str | None:
    if value is None:
        return None
    normalized = cv.string(value).strip()
    if not normalized:
        return None
    if len(normalized) > MAX_PERSON_DESCRIPTION_LENGTH:
        raise vol.Invalid(f"description must not exceed {MAX_PERSON_DESCRIPTION_LENGTH} characters")
    return normalized


CREATE_USER_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_REQUEST_ID): lambda value: _uuid(value, ATTR_REQUEST_ID),
        vol.Required(ATTR_DISPLAY_NAME): cv.string,
        vol.Optional(ATTR_DESCRIPTION): _description,
        vol.Optional(ATTR_NOTES): vol.Any(None, cv.string),
        vol.Optional(ATTR_ENABLED, default=True): cv.boolean,
        vol.Optional(ATTR_PIN): cv.string,
        vol.Required(ATTR_ACCESS_POINT_IDS): [lambda value: _uuid(value, ATTR_ACCESS_POINT_IDS)],
        vol.Required(ATTR_SCHEDULE): dict,
    }
)

ASSIGN_USER_ACCESS_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_REQUEST_ID): lambda value: _uuid(value, ATTR_REQUEST_ID),
        vol.Required(ATTR_PERSON_ID): lambda value: _uuid(value, ATTR_PERSON_ID),
        vol.Required(ATTR_ACCESS_POINT_IDS): [lambda value: _uuid(value, ATTR_ACCESS_POINT_IDS)],
        vol.Optional(ATTR_SCHEDULE_ID): lambda value: _uuid(value, ATTR_SCHEDULE_ID),
        vol.Optional(ATTR_SCHEDULE): dict,
        vol.Optional(ATTR_PIN): cv.string,
    }
)
EMPTY_SCHEMA = vol.Schema({})


def _optional_datetime(value: object, time_zone: str) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("Schedule validity must be a date and time")
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        parsed = parsed.replace(tzinfo=ZoneInfo(time_zone))
    return parsed.astimezone(UTC)


def _new_schedule(
    request_id: UUID,
    raw: object,
) -> Schedule:
    if not isinstance(raw, Mapping):
        raise ValueError("Schedule definition is required")
    keys = set(raw)
    allowed_keys = {
        "name",
        "time_zone",
        "valid_from",
        "valid_until",
        "weekly_rules",
        "enabled",
    }
    if not {"name", "time_zone"} <= keys or not keys <= allowed_keys:
        raise ValueError("Schedule definition is invalid")
    name = raw.get("name")
    time_zone = raw.get("time_zone")
    rules = raw.get("weekly_rules", [])
    enabled = raw.get("enabled", True)
    if (
        not isinstance(name, str)
        or not isinstance(time_zone, str)
        or not isinstance(rules, list)
        or not isinstance(enabled, bool)
    ):
        raise ValueError("Schedule definition is invalid")
    if not enabled:
        raise ValueError("Selected Schedule must be enabled")
    parsed_rules: list[WeeklyRule] = []
    for rule in rules:
        if not isinstance(rule, Mapping):
            raise ValueError("Schedule hours are invalid")
        if set(rule) != {"day_of_week", "start_time", "end_time"}:
            raise ValueError("Schedule hours are invalid")
        day = rule.get("day_of_week")
        start = rule.get("start_time")
        end = rule.get("end_time")
        if isinstance(day, bool) or not isinstance(day, int):
            raise ValueError("Schedule weekday is invalid")
        if not isinstance(start, str) or not isinstance(end, str):
            raise ValueError("Schedule hours are invalid")
        parsed_rules.append(
            WeeklyRule(
                day_of_week=DayOfWeek(day),
                start_time=time.fromisoformat(start),
                end_time=time.fromisoformat(end),
            )
        )
    now = datetime.now(UTC)
    return Schedule(
        schedule_id=uuid5(NAMESPACE_URL, f"homepass:user-setup:{request_id}:schedule"),
        name=name,
        enabled=enabled,
        time_zone=time_zone,
        valid_from=_optional_datetime(raw.get("valid_from"), time_zone),
        valid_until=_optional_datetime(raw.get("valid_until"), time_zone),
        weekly_rules=tuple(parsed_rules),
        created_at=now,
        updated_at=now,
    )


def _schedule_selection(request_id: UUID, raw: object) -> tuple[UUID, Schedule | None]:
    if not isinstance(raw, Mapping):
        raise ValueError("Schedule selection is required")
    mode = raw.get("mode")
    if mode == "permanent":
        if set(raw) != {"mode"}:
            raise ValueError("Schedule selection is invalid")
        return PERMANENT_SCHEDULE_ID, None
    if mode == "existing":
        if set(raw) != {"mode", "schedule_id"}:
            raise ValueError("Schedule selection is invalid")
        return _uuid(raw.get("schedule_id"), ATTR_SCHEDULE_ID), None
    if mode == "new":
        if set(raw) != {"mode", "definition"}:
            raise ValueError("Schedule selection is invalid")
        schedule = _new_schedule(request_id, raw.get("definition"))
        return schedule.schedule_id, schedule
    raise ValueError("Schedule selection is invalid")


def _result_response(result: UserSetupResult, *, created: bool) -> JsonObjectType:
    status = (
        "needs_attention"
        if result.attention
        else "created"
        if created
        else "failed"
        if result.status == "failed"
        else "completed"
    )
    response: dict[str, object] = {
        "status": status,
        "person": result.person.to_dict(),
        "attention": result.attention,
        "repeated": result.repeated,
        "assignments": [
            {
                "access_point_id": str(assignment.access_point_id),
                "display_name": assignment.display_name,
                "status": assignment.status,
                **({"message": assignment.message} if assignment.message is not None else {}),
            }
            for assignment in result.assignments
        ],
    }
    return cast(JsonObjectType, response)


@callback
def async_register_user_setup_actions(
    hass: HomeAssistant,
    service: UserSetupService,
) -> None:
    """Register guided User workflow actions."""

    async def handle_get_options(_call: ServiceCall) -> JsonObjectType:
        try:
            options = await service.get_options()
        except Exception:
            raise HomeAssistantError("HomePASS could not load User setup options") from None
        return cast(
            JsonObjectType,
            {
                "access_points": list(options.access_points),
                "schedules": [schedule.to_dict() for schedule in options.schedules],
            },
        )

    async def handle_create_user(call: ServiceCall) -> JsonObjectType:
        request_id = cast(UUID, call.data[ATTR_REQUEST_ID])
        try:
            schedule_id, new_schedule = _schedule_selection(request_id, call.data[ATTR_SCHEDULE])
            result = await service.create_user(
                request_id=request_id,
                display_name=cast(str, call.data[ATTR_DISPLAY_NAME]),
                description=cast(str | None, call.data.get(ATTR_DESCRIPTION)),
                notes=cast(str | None, call.data.get(ATTR_NOTES)),
                enabled=cast(bool, call.data[ATTR_ENABLED]),
                pin=cast(str | None, call.data.get(ATTR_PIN)),
                access_point_ids=tuple(cast(list[UUID], call.data[ATTR_ACCESS_POINT_IDS])),
                schedule_id=schedule_id,
                new_schedule=new_schedule,
            )
        except DuplicatePersonError:
            raise ServiceValidationError("A User with this display name already exists") from None
        except (TypeError, ValueError) as err:
            raise ServiceValidationError(str(err)) from None
        except Exception:
            raise HomeAssistantError("HomePASS could not complete User setup") from None
        return _result_response(result, created=True)

    async def handle_assign_user_access(call: ServiceCall) -> JsonObjectType:
        try:
            raw_schedule = call.data.get(ATTR_SCHEDULE)
            raw_schedule_id = call.data.get(ATTR_SCHEDULE_ID)
            if (raw_schedule is None) == (raw_schedule_id is None):
                raise ValueError("Choose exactly one Schedule")
            if raw_schedule is not None:
                schedule_id, new_schedule = _schedule_selection(
                    cast(UUID, call.data[ATTR_REQUEST_ID]), raw_schedule
                )
            else:
                schedule_id = cast(UUID, raw_schedule_id)
                new_schedule = None
            result = await service.assign_user_access(
                request_id=cast(UUID, call.data[ATTR_REQUEST_ID]),
                person_id=cast(UUID, call.data[ATTR_PERSON_ID]),
                access_point_ids=tuple(cast(list[UUID], call.data[ATTR_ACCESS_POINT_IDS])),
                schedule_id=schedule_id,
                pin=cast(str | None, call.data.get(ATTR_PIN)),
                new_schedule=new_schedule,
            )
        except PersonNotFoundError:
            raise ServiceValidationError("User not found") from None
        except (TypeError, ValueError) as err:
            raise ServiceValidationError(str(err)) from None
        except Exception:
            raise HomeAssistantError("HomePASS could not assign door access") from None
        return _result_response(result, created=False)

    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_USER_SETUP_OPTIONS,
        handle_get_options,
        schema=EMPTY_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_CREATE_USER,
        handle_create_user,
        schema=CREATE_USER_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_ASSIGN_USER_ACCESS,
        handle_assign_user_access,
        schema=ASSIGN_USER_ACCESS_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )


@callback
def async_unregister_user_setup_actions(hass: HomeAssistant) -> None:
    """Remove guided User workflow actions."""
    for action in USER_SETUP_ACTIONS:
        hass.services.async_remove(DOMAIN, action)


__all__ = [
    "USER_SETUP_ACTIONS",
    "async_register_user_setup_actions",
    "async_unregister_user_setup_actions",
]
