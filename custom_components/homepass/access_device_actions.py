"""Home Assistant actions for HomePASS Door-associated devices."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast
from uuid import UUID

import voluptuous as vol
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
    callback,
)
from homeassistant.exceptions import ServiceValidationError

from .const import (
    ATTR_ACCESS_DEVICE_ID,
    ATTR_ACCESS_POINT_ID,
    ATTR_BUTTON_ACTIONS,
    ATTR_DEVICE_ID,
    ATTR_DISPLAY_NAME,
    DOMAIN,
    SERVICE_ADD_ACCESS_DEVICE,
    SERVICE_LIST_ACCESS_DEVICES,
    SERVICE_REMOVE_ACCESS_DEVICE,
    SERVICE_UPDATE_ACCESS_DEVICE,
)
from .exceptions import HomePASSError

if TYPE_CHECKING:
    from .services import AccessDeviceService

ACCESS_DEVICE_ACTIONS = (
    SERVICE_LIST_ACCESS_DEVICES,
    SERVICE_ADD_ACCESS_DEVICE,
    SERVICE_UPDATE_ACCESS_DEVICE,
    SERVICE_REMOVE_ACCESS_DEVICE,
)
EMPTY_SCHEMA = vol.Schema({})
ADD_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_DEVICE_ID): str,
        vol.Required(ATTR_ACCESS_POINT_ID): str,
        vol.Optional(ATTR_DISPLAY_NAME): vol.All(str, vol.Length(min=1, max=80)),
    }
)
UPDATE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_ACCESS_DEVICE_ID): str,
        vol.Optional(ATTR_ACCESS_POINT_ID): str,
        vol.Optional(ATTR_DISPLAY_NAME): vol.All(str, vol.Length(min=1, max=80)),
        vol.Optional("enabled"): bool,
        vol.Optional(ATTR_BUTTON_ACTIONS): dict,
    }
)
REMOVE_SCHEMA = vol.Schema({vol.Required(ATTR_ACCESS_DEVICE_ID): str})


@callback
def async_register_access_device_actions(
    hass: HomeAssistant,
    service: AccessDeviceService,
) -> None:
    """Register administrator-only access-device actions."""

    async def require_admin(call: ServiceCall) -> None:
        user = (
            await hass.auth.async_get_user(call.context.user_id)
            if call.context.user_id is not None
            else None
        )
        if user is None or not user.is_admin:
            raise ServiceValidationError("Only a HomePASS administrator can manage devices")

    async def handle_list(call: ServiceCall) -> ServiceResponse:
        await require_admin(call)
        try:
            views, candidates = await service.list_overview()
        except HomePASSError:
            raise ServiceValidationError("HomePASS devices are unavailable") from None
        return cast(
            "ServiceResponse",
            {
                "access_devices": [item.to_dict() for item in views],
                "available_devices": list(candidates),
            },
        )

    async def handle_add(call: ServiceCall) -> ServiceResponse:
        await require_admin(call)
        try:
            view = await service.add_keypad(
                home_assistant_device_id=call.data[ATTR_DEVICE_ID],
                access_point_id=UUID(call.data[ATTR_ACCESS_POINT_ID]),
                display_name=call.data.get(ATTR_DISPLAY_NAME),
            )
        except (HomePASSError, TypeError, ValueError) as err:
            raise ServiceValidationError(str(err)) from None
        return cast("ServiceResponse", {"access_device": view.to_dict()})

    async def handle_update(call: ServiceCall) -> ServiceResponse:
        await require_admin(call)
        try:
            view = await service.update(
                UUID(call.data[ATTR_ACCESS_DEVICE_ID]),
                access_point_id=(
                    UUID(call.data[ATTR_ACCESS_POINT_ID])
                    if ATTR_ACCESS_POINT_ID in call.data
                    else None
                ),
                display_name=call.data.get(ATTR_DISPLAY_NAME),
                enabled=call.data.get("enabled"),
                button_actions=call.data.get(ATTR_BUTTON_ACTIONS),
            )
        except (HomePASSError, TypeError, ValueError) as err:
            raise ServiceValidationError(str(err)) from None
        return cast("ServiceResponse", {"access_device": view.to_dict()})

    async def handle_remove(call: ServiceCall) -> ServiceResponse:
        await require_admin(call)
        try:
            removed = await service.remove(UUID(call.data[ATTR_ACCESS_DEVICE_ID]))
        except (HomePASSError, TypeError, ValueError) as err:
            raise ServiceValidationError(str(err)) from None
        return cast("ServiceResponse", {"removed": removed})

    hass.services.async_register(
        DOMAIN,
        SERVICE_LIST_ACCESS_DEVICES,
        handle_list,
        schema=EMPTY_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_ADD_ACCESS_DEVICE,
        handle_add,
        schema=ADD_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_UPDATE_ACCESS_DEVICE,
        handle_update,
        schema=UPDATE_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_REMOVE_ACCESS_DEVICE,
        handle_remove,
        schema=REMOVE_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )


@callback
def async_unregister_access_device_actions(hass: HomeAssistant) -> None:
    for action in ACCESS_DEVICE_ACTIONS:
        hass.services.async_remove(DOMAIN, action)


__all__ = [
    "ACCESS_DEVICE_ACTIONS",
    "async_register_access_device_actions",
    "async_unregister_access_device_actions",
]
