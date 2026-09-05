"""Home Assistant action for dashboard synchronization attention."""

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

from .const import DOMAIN, SERVICE_GET_DASHBOARD_ATTENTION
from .services import DashboardAttentionService

DASHBOARD_ATTENTION_ACTIONS = (SERVICE_GET_DASHBOARD_ATTENTION,)


@callback
def async_register_dashboard_attention_actions(
    hass: HomeAssistant,
    service: DashboardAttentionService,
) -> None:
    """Register the dashboard attention aggregate action."""

    async def handle_get_dashboard_attention(_call: ServiceCall) -> ServiceResponse:
        try:
            summary = await service.get_dashboard_attention()
        except HomeAssistantError, KeyError, TypeError, ValueError:
            raise HomeAssistantError("Synchronization attention unavailable") from None
        return cast(ServiceResponse, summary.to_dict())

    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_DASHBOARD_ATTENTION,
        handle_get_dashboard_attention,
        schema=vol.Schema({}),
        supports_response=SupportsResponse.ONLY,
    )


@callback
def async_unregister_dashboard_attention_actions(hass: HomeAssistant) -> None:
    """Remove the dashboard attention action."""
    for action in DASHBOARD_ATTENTION_ACTIONS:
        hass.services.async_remove(DOMAIN, action)


__all__ = [
    "DASHBOARD_ATTENTION_ACTIONS",
    "async_register_dashboard_attention_actions",
    "async_unregister_dashboard_attention_actions",
]
