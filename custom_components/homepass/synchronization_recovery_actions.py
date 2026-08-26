"""Home Assistant action boundary for synchronization recovery."""

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
from homeassistant.helpers import config_validation as cv

from .const import (
    ATTR_ACCESS_POINT_ID,
    ATTR_PERSON_ID,
    DOMAIN,
    SERVICE_RETRY_SYNCHRONIZATION,
)
from .services import SynchronizationRecoveryService

SYNCHRONIZATION_RECOVERY_ACTIONS = (SERVICE_RETRY_SYNCHRONIZATION,)


def _uuid(value: object) -> UUID:
    """Validate an opaque relationship identifier at the action boundary."""
    try:
        return UUID(cv.string(value))
    except ValueError as err:
        raise vol.Invalid("identifier must be a valid UUID") from err


RETRY_SYNCHRONIZATION_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_PERSON_ID): _uuid,
        vol.Required(ATTR_ACCESS_POINT_ID): _uuid,
    }
)


@callback
def async_register_synchronization_recovery_action(
    hass: HomeAssistant,
    recovery_service: SynchronizationRecoveryService,
) -> None:
    """Register the single shared synchronization retry action."""

    async def handle_retry(call: ServiceCall) -> ServiceResponse:
        result = await recovery_service.recover(
            person_id=cast(UUID, call.data[ATTR_PERSON_ID]),
            access_point_id=cast(UUID, call.data[ATTR_ACCESS_POINT_ID]),
        )
        return cast(ServiceResponse, result.to_dict())

    hass.services.async_register(
        DOMAIN,
        SERVICE_RETRY_SYNCHRONIZATION,
        handle_retry,
        schema=RETRY_SYNCHRONIZATION_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )


@callback
def async_unregister_synchronization_recovery_action(hass: HomeAssistant) -> None:
    """Remove the synchronization recovery action."""
    hass.services.async_remove(DOMAIN, SERVICE_RETRY_SYNCHRONIZATION)


__all__ = [
    "RETRY_SYNCHRONIZATION_SCHEMA",
    "SYNCHRONIZATION_RECOVERY_ACTIONS",
    "async_register_synchronization_recovery_action",
    "async_unregister_synchronization_recovery_action",
]
