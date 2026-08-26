"""Home Assistant actions for the temporary Z-Wave synchronization spike."""

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
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError

from .const import (
    ATTR_DISPLAY_NAME,
    ATTR_LOCK_ENTITY_ID,
    ATTR_PIN,
    ATTR_USER_ID,
    DOMAIN,
    SERVICE_TEST_ZWAVE_DELETE_USER,
    SERVICE_TEST_ZWAVE_PIN_SYNC,
)
from .services.zwave_sync import (
    ZWaveDriverError,
    ZWaveInvalidTargetError,
    ZWavePinSyncService,
    ZWaveSyncValidationError,
)

ZWAVE_SPIKE_ACTIONS = (
    SERVICE_TEST_ZWAVE_PIN_SYNC,
    SERVICE_TEST_ZWAVE_DELETE_USER,
)

# Validation happens in the handler so Home Assistant never debug-logs a rejected
# schema containing the ephemeral PIN.
SPIKE_ACTION_SCHEMA = vol.Schema({}, extra=vol.ALLOW_EXTRA)


def _required_string(call: ServiceCall, key: str) -> str:
    """Read a required string without including its value in an error."""
    value = call.data.get(key)
    if not isinstance(value, str):
        raise ServiceValidationError(f"{key} is required and must be a string")
    return value


def _required_user_id(call: ServiceCall) -> int:
    """Read a positive user identifier."""
    value = call.data.get(ATTR_USER_ID)
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 65535:
        raise ServiceValidationError("user_id is required and must be from 1 to 65535")
    return value


async def _sync_pin(
    service: ZWavePinSyncService,
    call: ServiceCall,
) -> ServiceResponse:
    """Validate and execute the controlled PIN synchronization spike."""
    try:
        response = await service.sync_pin(
            _required_string(call, ATTR_LOCK_ENTITY_ID),
            _required_string(call, ATTR_DISPLAY_NAME),
            _required_string(call, ATTR_PIN),
        )
    except (ZWaveSyncValidationError, ZWaveInvalidTargetError) as err:
        raise ServiceValidationError(str(err)) from None
    except ZWaveDriverError:
        raise HomeAssistantError("HomePASS could not create the Z-Wave user") from None
    return cast(ServiceResponse, response)


async def _delete_user(
    service: ZWavePinSyncService,
    call: ServiceCall,
) -> ServiceResponse:
    """Validate and execute deletion of one requested spike user."""
    try:
        response = await service.delete_user(
            _required_string(call, ATTR_LOCK_ENTITY_ID),
            _required_user_id(call),
        )
    except (ZWaveSyncValidationError, ZWaveInvalidTargetError) as err:
        raise ServiceValidationError(str(err)) from None
    except ZWaveDriverError:
        raise HomeAssistantError("HomePASS could not delete the Z-Wave user") from None
    return cast(ServiceResponse, response)


@callback
def async_register_zwave_spike_actions(
    hass: HomeAssistant,
    service: ZWavePinSyncService,
) -> None:
    """Register controlled Z-Wave synchronization spike actions."""

    async def handle_sync_pin(call: ServiceCall) -> ServiceResponse:
        return await _sync_pin(service, call)

    async def handle_delete_user(call: ServiceCall) -> ServiceResponse:
        return await _delete_user(service, call)

    hass.services.async_register(
        DOMAIN,
        SERVICE_TEST_ZWAVE_PIN_SYNC,
        handle_sync_pin,
        schema=SPIKE_ACTION_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_TEST_ZWAVE_DELETE_USER,
        handle_delete_user,
        schema=SPIKE_ACTION_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )


@callback
def async_unregister_zwave_spike_actions(hass: HomeAssistant) -> None:
    """Remove controlled Z-Wave synchronization spike actions."""
    for action in ZWAVE_SPIKE_ACTIONS:
        hass.services.async_remove(DOMAIN, action)
