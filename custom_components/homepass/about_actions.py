"""Home Assistant action for the dedicated HomePASS About page."""

from __future__ import annotations

from typing import cast

import voluptuous as vol
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
    callback,
)
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN, SERVICE_GET_ABOUT
from .exceptions import StorageError
from .services import AboutService

ABOUT_ACTIONS = (SERVICE_GET_ABOUT,)


@callback
def async_register_about_action(hass: HomeAssistant, service: AboutService) -> None:
    """Register the presentation-safe About action."""

    async def handle_get_about(_call: ServiceCall) -> ServiceResponse:
        try:
            about = await service.load()
        except HomeAssistantError, StorageError, KeyError, TypeError, ValueError:
            raise HomeAssistantError("About information is unavailable") from None
        return cast(ServiceResponse, about.to_dict())

    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_ABOUT,
        handle_get_about,
        schema=vol.Schema({}),
        supports_response=SupportsResponse.ONLY,
    )


@callback
def async_unregister_about_action(hass: HomeAssistant) -> None:
    """Remove the About action."""
    for action in ABOUT_ACTIONS:
        hass.services.async_remove(DOMAIN, action)


__all__ = ["ABOUT_ACTIONS", "async_register_about_action", "async_unregister_about_action"]
