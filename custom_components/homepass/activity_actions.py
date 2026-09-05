"""Home Assistant action for presentation-safe recent Activity."""

from __future__ import annotations

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
from homeassistant.exceptions import HomeAssistantError

from .const import (
    ATTR_ACCESS_POINT_ID,
    ATTR_ACTIVITY_EVENT_TYPES,
    ATTR_LIMIT,
    ATTR_PERSON_ID,
    DOMAIN,
    SERVICE_LIST_RECENT_ACTIVITY,
)
from .exceptions import StorageError
from .services import (
    ACTIVITY_FILTER_EVENTS,
    ActivityFilter,
    ActivityFilterEvent,
    ActivityReadService,
    activity_filter_groups,
)

DEFAULT_ACTIVITY_LIMIT = 20
MAX_ACTIVITY_LIMIT = 100
ACTIVITY_ACTIONS = (SERVICE_LIST_RECENT_ACTIVITY,)


def _activity_limit(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise vol.Invalid("limit must be an integer")
    if not 1 <= value <= MAX_ACTIVITY_LIMIT:
        raise vol.Invalid(f"limit must be between 1 and {MAX_ACTIVITY_LIMIT}")
    return value


def _activity_filter_events(value: object) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise vol.Invalid("event_types must be a list of supported strings")
    if len(value) != len(set(value)):
        raise vol.Invalid("event_types must not contain duplicates")
    try:
        events = tuple(ActivityFilterEvent(item) for item in value)
    except ValueError:
        raise vol.Invalid("event_types contains an unsupported value") from None
    if not set(events) <= ACTIVITY_FILTER_EVENTS:
        raise vol.Invalid("event_types contains an unsupported value")
    return tuple(event.value for event in events)


def _activity_filter_uuid(value: object) -> str:
    if not isinstance(value, str):
        raise vol.Invalid("Activity identity filter must be a UUID string")
    try:
        return str(UUID(value))
    except ValueError:
        raise vol.Invalid("Activity identity filter must be a UUID string") from None


LIST_RECENT_ACTIVITY_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_LIMIT, default=DEFAULT_ACTIVITY_LIMIT): _activity_limit,
        vol.Optional(ATTR_ACTIVITY_EVENT_TYPES): _activity_filter_events,
        vol.Optional(ATTR_ACCESS_POINT_ID): _activity_filter_uuid,
        vol.Optional(ATTR_PERSON_ID): _activity_filter_uuid,
    }
)


@callback
def async_register_activity_actions(
    hass: HomeAssistant, activity_read_service: ActivityReadService
) -> None:
    """Register the bounded presentation-only Activity read action."""

    async def handle_list_recent_activity(call: ServiceCall) -> ServiceResponse:
        try:
            event_types = call.data.get(ATTR_ACTIVITY_EVENT_TYPES)
            door_id = call.data.get(ATTR_ACCESS_POINT_ID)
            person_id = call.data.get(ATTR_PERSON_ID)
            activity_filter = ActivityFilter(
                None
                if event_types is None
                else frozenset(
                    ActivityFilterEvent(item) for item in cast(tuple[str, ...], event_types)
                ),
                None if door_id is None else UUID(cast(str, door_id)),
                None if person_id is None else UUID(cast(str, person_id)),
            )
            limit = cast(int, call.data[ATTR_LIMIT])
            events = (
                await activity_read_service.list_recent(limit, activity_filter)
                if activity_filter.active
                else await activity_read_service.list_recent(limit)
            )
        except StorageError, TypeError, ValueError:
            raise HomeAssistantError("Recent Activity is unavailable") from None
        return cast(
            ServiceResponse,
            {
                "events": [event.to_dict() for event in events],
                "filter_groups": list(activity_filter_groups()),
            },
        )

    hass.services.async_register(
        DOMAIN,
        SERVICE_LIST_RECENT_ACTIVITY,
        handle_list_recent_activity,
        schema=LIST_RECENT_ACTIVITY_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )


@callback
def async_unregister_activity_actions(hass: HomeAssistant) -> None:
    """Remove Activity actions."""
    for action in ACTIVITY_ACTIONS:
        hass.services.async_remove(DOMAIN, action)


__all__ = [
    "ACTIVITY_ACTIONS",
    "DEFAULT_ACTIVITY_LIMIT",
    "LIST_RECENT_ACTIVITY_SCHEMA",
    "MAX_ACTIVITY_LIMIT",
    "async_register_activity_actions",
    "async_unregister_activity_actions",
]
