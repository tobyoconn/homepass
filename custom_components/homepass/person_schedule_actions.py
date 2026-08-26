"""Home Assistant actions for Person-owned Schedules."""

from __future__ import annotations

from collections.abc import Awaitable, Mapping
from datetime import UTC, datetime
from typing import cast
from uuid import UUID
from zoneinfo import ZoneInfo

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
    ATTR_ACCESS_POINT_IDS,
    ATTR_ENABLED,
    ATTR_EXPECTED_PERSON_UPDATED_AT,
    ATTR_EXPECTED_SCHEDULE_REVISION,
    ATTR_PERSON_ID,
    ATTR_SCHEDULE_ID,
    ATTR_TIME_ZONE,
    ATTR_VALID_FROM,
    ATTR_VALID_UNTIL,
    ATTR_WEEKLY_RULES,
    DOMAIN,
    SERVICE_GET_PERSON_SCHEDULE,
    SERVICE_SAVE_PERSON_SCHEDULE,
)
from .exceptions import (
    ConcurrentPersonScheduleUpdateError,
    InvalidPersonScheduleReferenceError,
    PersonNotFoundError,
    PersonScheduleConflictError,
    StorageError,
    ValidationError,
)
from .models import DayOfWeek, WeeklyRule
from .services import PersonScheduleService, PersonScheduleState

PERSON_SCHEDULE_ACTIONS = (SERVICE_GET_PERSON_SCHEDULE, SERVICE_SAVE_PERSON_SCHEDULE)


def _uuid(value: object, field_name: str) -> UUID:
    """Validate one UUID action field."""
    try:
        return UUID(cv.string(value))
    except ValueError as err:
        raise vol.Invalid(f"{field_name} must be a valid UUID") from err


def _positive_revision(value: object) -> int:
    """Validate a non-boolean positive Schedule revision."""
    if isinstance(value, bool):
        raise vol.Invalid("expected_schedule_revision must be a positive integer")
    try:
        revision = cv.positive_int(value)
    except vol.Invalid as err:
        raise vol.Invalid("expected_schedule_revision must be a positive integer") from err
    if revision < 1:
        raise vol.Invalid("expected_schedule_revision must be a positive integer")
    return cast(int, revision)


def _weekly_rule(value: object) -> WeeklyRule:
    """Validate one complete replacement weekly rule."""
    if not isinstance(value, Mapping):
        raise vol.Invalid("weekly_rules entries must be objects")
    try:
        day = value["day_of_week"]
        start = value["start_time"]
        end = value["end_time"]
        if isinstance(day, bool):
            raise ValueError
        return WeeklyRule(DayOfWeek(int(day)), cv.time(start), cv.time(end))
    except (KeyError, TypeError, ValueError, vol.Invalid) as err:
        raise vol.Invalid("weekly_rules contains an invalid rule") from err


def _weekly_rules(value: object) -> tuple[WeeklyRule, ...]:
    """Validate the complete weekly-rule replacement collection."""
    if not isinstance(value, list):
        raise vol.Invalid("weekly_rules must be a list")
    return tuple(_weekly_rule(rule) for rule in value)


def _expected_datetime(value: object) -> datetime:
    """Validate an aware editor concurrency timestamp."""
    parsed = cv.datetime(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise vol.Invalid("expected_person_updated_at must be timezone-aware")
    return parsed.astimezone(UTC)


def _schedule_datetime(value: object, time_zone: str) -> datetime | None:
    """Interpret local builder values in the configured Home Assistant timezone."""
    if value is None:
        return None
    try:
        parsed = datetime.fromisoformat(cv.string(value))
    except ValueError as err:
        raise ServiceValidationError("person_schedule_validation") from err
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        parsed = parsed.replace(tzinfo=ZoneInfo(time_zone))
    return parsed.astimezone(UTC)


GET_PERSON_SCHEDULE_SCHEMA = vol.Schema(
    {vol.Required(ATTR_PERSON_ID): lambda value: _uuid(value, ATTR_PERSON_ID)}
)
SAVE_PERSON_SCHEDULE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_PERSON_ID): lambda value: _uuid(value, ATTR_PERSON_ID),
        vol.Required(ATTR_TIME_ZONE): cv.time_zone,
        vol.Required(ATTR_VALID_FROM): vol.Any(None, cv.string),
        vol.Required(ATTR_VALID_UNTIL): vol.Any(None, cv.string),
        vol.Required(ATTR_WEEKLY_RULES): _weekly_rules,
        vol.Required(ATTR_EXPECTED_PERSON_UPDATED_AT): _expected_datetime,
        vol.Required(ATTR_SCHEDULE_ID): lambda value: _uuid(value, ATTR_SCHEDULE_ID),
        vol.Required(ATTR_EXPECTED_SCHEDULE_REVISION): _positive_revision,
        vol.Optional(ATTR_ENABLED, default=True): cv.boolean,
        vol.Optional(ATTR_ACCESS_POINT_IDS): [lambda value: _uuid(value, ATTR_ACCESS_POINT_IDS)],
    }
)


async def _execute[ResultT](operation: Awaitable[ResultT]) -> ResultT:
    """Translate Person Schedule domain failures without exposing internals."""
    try:
        return await operation
    except PersonScheduleConflictError as err:
        raise ServiceValidationError("person_schedule_conflict") from err
    except ConcurrentPersonScheduleUpdateError as err:
        raise ServiceValidationError("concurrent_person_schedule_update") from err
    except ValidationError as err:
        raise ServiceValidationError("person_schedule_validation") from err
    except PersonNotFoundError as err:
        raise ServiceValidationError("person_not_found") from err
    except InvalidPersonScheduleReferenceError as err:
        raise HomeAssistantError("person_schedule_unavailable") from err
    except StorageError as err:
        raise HomeAssistantError("person_schedule_storage_error") from err


def _state_response(state: PersonScheduleState) -> ServiceResponse:
    """Serialize the default and authoritative door Schedule Groups."""
    return cast(
        ServiceResponse,
        {
            "schedule": state.schedule.to_dict(),
            ATTR_EXPECTED_PERSON_UPDATED_AT: state.person.updated_at.isoformat(),
            ATTR_SCHEDULE_ID: str(state.schedule.schedule_id),
            ATTR_EXPECTED_SCHEDULE_REVISION: state.schedule.revision,
            "schedule_groups": [
                {
                    "schedule": group.schedule.to_dict(),
                    ATTR_ACCESS_POINT_IDS: [
                        str(access_point_id) for access_point_id in group.access_point_ids
                    ],
                    ATTR_EXPECTED_SCHEDULE_REVISION: group.schedule.revision,
                }
                for group in state.groups
            ],
        },
    )


@callback
def async_register_person_schedule_actions(
    hass: HomeAssistant,
    service: PersonScheduleService,
) -> None:
    """Register Person Schedule load and save actions."""

    async def handle_get(call: ServiceCall) -> ServiceResponse:
        state = await _execute(service.get_schedule_state(cast(UUID, call.data[ATTR_PERSON_ID])))
        return _state_response(state)

    async def handle_save(call: ServiceCall) -> ServiceResponse:
        time_zone = cast(str, call.data[ATTR_TIME_ZONE])
        schedule = await _execute(
            service.save_person_schedule(
                cast(UUID, call.data[ATTR_PERSON_ID]),
                time_zone=time_zone,
                enabled=cast(bool, call.data[ATTR_ENABLED]),
                valid_from=_schedule_datetime(call.data[ATTR_VALID_FROM], time_zone),
                valid_until=_schedule_datetime(call.data[ATTR_VALID_UNTIL], time_zone),
                weekly_rules=cast(tuple[WeeklyRule, ...], call.data[ATTR_WEEKLY_RULES]),
                expected_person_updated_at=cast(
                    datetime, call.data[ATTR_EXPECTED_PERSON_UPDATED_AT]
                ),
                expected_schedule_id=cast(UUID, call.data[ATTR_SCHEDULE_ID]),
                expected_schedule_revision=cast(int, call.data[ATTR_EXPECTED_SCHEDULE_REVISION]),
                access_point_ids=cast(
                    tuple[UUID, ...] | None,
                    (
                        tuple(call.data[ATTR_ACCESS_POINT_IDS])
                        if ATTR_ACCESS_POINT_IDS in call.data
                        else None
                    ),
                ),
            )
        )
        return cast(ServiceResponse, {"schedule": schedule.to_dict()})

    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_PERSON_SCHEDULE,
        handle_get,
        schema=GET_PERSON_SCHEDULE_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SAVE_PERSON_SCHEDULE,
        handle_save,
        schema=SAVE_PERSON_SCHEDULE_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )


@callback
def async_unregister_person_schedule_actions(hass: HomeAssistant) -> None:
    """Remove Person Schedule actions."""
    for action in PERSON_SCHEDULE_ACTIONS:
        hass.services.async_remove(DOMAIN, action)
