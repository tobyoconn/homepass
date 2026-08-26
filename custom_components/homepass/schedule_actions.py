"""Home Assistant actions for HomePASS schedules."""

from __future__ import annotations

from collections.abc import Awaitable, Mapping
from datetime import datetime
from typing import cast
from uuid import UUID

import voluptuous as vol
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
    callback,
)
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv

from .const import (
    ATTR_ENABLED,
    ATTR_NAME,
    ATTR_SCHEDULE_ID,
    ATTR_TIME_ZONE,
    ATTR_VALID_FROM,
    ATTR_VALID_UNTIL,
    ATTR_WEEKLY_RULES,
    DOMAIN,
    SERVICE_CREATE_SCHEDULE,
    SERVICE_DELETE_SCHEDULE,
    SERVICE_GET_SCHEDULE,
    SERVICE_LIST_SCHEDULES,
    SERVICE_UPDATE_SCHEDULE,
)
from .exceptions import (
    DuplicateScheduleError,
    ProtectedScheduleError,
    ScheduleNotFoundError,
    StorageError,
    ValidationError,
)
from .models import DayOfWeek, Schedule, WeeklyRule
from .services.schedule import UNSET, ScheduleField, ScheduleService

SCHEDULE_ACTIONS = (
    SERVICE_CREATE_SCHEDULE,
    SERVICE_UPDATE_SCHEDULE,
    SERVICE_DELETE_SCHEDULE,
    SERVICE_GET_SCHEDULE,
    SERVICE_LIST_SCHEDULES,
)


def _non_empty_string(value: object, field_name: str) -> str:
    """Validate and normalize a required string."""
    normalized = cv.string(value).strip()
    if not normalized:
        raise vol.Invalid(f"{field_name} must not be empty")
    return normalized


def _schedule_id(value: object) -> UUID:
    """Validate and convert a Schedule UUID."""
    try:
        return UUID(cv.string(value))
    except ValueError as err:
        raise vol.Invalid("schedule_id must be a valid UUID") from err


def _weekly_rule(value: object) -> WeeklyRule:
    """Validate and convert one weekly rule through the domain model."""
    if not isinstance(value, Mapping):
        raise vol.Invalid("weekly_rules entries must be objects")
    try:
        day = value["day_of_week"]
        start = value["start_time"]
        end = value["end_time"]
    except KeyError as err:
        raise vol.Invalid(f"weekly rule is missing {err.args[0]}") from err
    try:
        if isinstance(day, bool):
            raise ValueError
        return WeeklyRule(
            day_of_week=DayOfWeek(int(day)),
            start_time=cv.time(start),
            end_time=cv.time(end),
        )
    except (TypeError, ValueError, vol.Invalid) as err:
        raise vol.Invalid(f"invalid weekly rule: {err}") from err


def _weekly_rules(value: object) -> tuple[WeeklyRule, ...]:
    """Validate and convert a weekly rule list."""
    if not isinstance(value, list):
        raise vol.Invalid("weekly_rules must be a list")
    return tuple(_weekly_rule(rule) for rule in value)


CREATE_SCHEDULE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_NAME): lambda value: _non_empty_string(value, ATTR_NAME),
        vol.Required(ATTR_TIME_ZONE): cv.time_zone,
        vol.Optional(ATTR_ENABLED, default=True): cv.boolean,
        vol.Optional(ATTR_VALID_FROM): vol.Any(None, cv.datetime),
        vol.Optional(ATTR_VALID_UNTIL): vol.Any(None, cv.datetime),
        vol.Optional(ATTR_WEEKLY_RULES, default=list): _weekly_rules,
    }
)

UPDATE_SCHEDULE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_SCHEDULE_ID): _schedule_id,
        vol.Optional(ATTR_NAME): lambda value: _non_empty_string(value, ATTR_NAME),
        vol.Optional(ATTR_TIME_ZONE): cv.time_zone,
        vol.Optional(ATTR_ENABLED): cv.boolean,
        vol.Optional(ATTR_VALID_FROM): vol.Any(None, cv.datetime),
        vol.Optional(ATTR_VALID_UNTIL): vol.Any(None, cv.datetime),
        vol.Optional(ATTR_WEEKLY_RULES): _weekly_rules,
    }
)

SCHEDULE_ID_SCHEMA = vol.Schema({vol.Required(ATTR_SCHEDULE_ID): _schedule_id})
EMPTY_SCHEMA = vol.Schema({})


async def _execute[ResultT](operation: Awaitable[ResultT]) -> ResultT:
    """Execute a Schedule operation and expose Home Assistant errors."""
    try:
        return await operation
    except DuplicateScheduleError as err:
        raise ServiceValidationError("A schedule with this name already exists") from err
    except (ScheduleNotFoundError, ProtectedScheduleError, ValidationError) as err:
        raise ServiceValidationError(str(err)) from err
    except StorageError as err:
        raise HomeAssistantError("HomePASS could not persist Schedule data") from err


def _schedule_response(schedule: Schedule) -> ServiceResponse:
    """Serialize one Schedule as action response data."""
    return cast(ServiceResponse, {"schedule": schedule.to_dict()})


def _schedules_response(schedules: tuple[Schedule, ...]) -> ServiceResponse:
    """Serialize Schedules as action response data."""
    return cast(
        ServiceResponse,
        {"schedules": [schedule.to_dict() for schedule in schedules]},
    )


def _field[T](call: ServiceCall, key: str) -> ScheduleField[T]:
    """Return an update field or the omitted-field sentinel."""
    return cast(ScheduleField[T], call.data.get(key, UNSET))


@callback
def async_register_schedule_actions(
    hass: HomeAssistant,
    schedule_service: ScheduleService,
) -> None:
    """Register HomePASS Schedule actions."""

    async def handle_create_schedule(call: ServiceCall) -> ServiceResponse:
        schedule = await _execute(
            schedule_service.create_schedule(
                cast(str, call.data[ATTR_NAME]),
                cast(str, call.data[ATTR_TIME_ZONE]),
                enabled=cast(bool, call.data[ATTR_ENABLED]),
                valid_from=cast(datetime | None, call.data.get(ATTR_VALID_FROM)),
                valid_until=cast(datetime | None, call.data.get(ATTR_VALID_UNTIL)),
                weekly_rules=cast(tuple[WeeklyRule, ...], call.data[ATTR_WEEKLY_RULES]),
            )
        )
        return _schedule_response(schedule)

    async def handle_update_schedule(call: ServiceCall) -> ServiceResponse:
        schedule = await _execute(
            schedule_service.update_schedule(
                cast(UUID, call.data[ATTR_SCHEDULE_ID]),
                name=_field(call, ATTR_NAME),
                time_zone=_field(call, ATTR_TIME_ZONE),
                enabled=_field(call, ATTR_ENABLED),
                valid_from=_field(call, ATTR_VALID_FROM),
                valid_until=_field(call, ATTR_VALID_UNTIL),
                weekly_rules=_field(call, ATTR_WEEKLY_RULES),
            )
        )
        return _schedule_response(schedule)

    async def handle_delete_schedule(call: ServiceCall) -> None:
        await _execute(schedule_service.delete_schedule(cast(UUID, call.data[ATTR_SCHEDULE_ID])))

    async def handle_get_schedule(call: ServiceCall) -> ServiceResponse:
        schedule = await _execute(
            schedule_service.get_schedule(cast(UUID, call.data[ATTR_SCHEDULE_ID]))
        )
        return _schedule_response(schedule)

    async def handle_list_schedules(_call: ServiceCall) -> ServiceResponse:
        schedules = await _execute(schedule_service.list_schedules())
        return _schedules_response(schedules)

    hass.services.async_register(
        DOMAIN,
        SERVICE_CREATE_SCHEDULE,
        handle_create_schedule,
        schema=CREATE_SCHEDULE_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_UPDATE_SCHEDULE,
        handle_update_schedule,
        schema=UPDATE_SCHEDULE_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_DELETE_SCHEDULE,
        handle_delete_schedule,
        schema=SCHEDULE_ID_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_SCHEDULE,
        handle_get_schedule,
        schema=SCHEDULE_ID_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_LIST_SCHEDULES,
        handle_list_schedules,
        schema=EMPTY_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )


@callback
def async_unregister_schedule_actions(hass: HomeAssistant) -> None:
    """Remove HomePASS Schedule actions."""
    for action in SCHEDULE_ACTIONS:
        hass.services.async_remove(DOMAIN, action)
