"""Home Assistant action for secure Give Access provisioning."""

from __future__ import annotations

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
from homeassistant.util.json import JsonObjectType

from .const import (
    ATTR_ACCESS_POINT_ID,
    ATTR_PERSON_ID,
    ATTR_PIN,
    DOMAIN,
    SERVICE_GIVE_ACCESS,
)
from .exceptions import DuplicateAccessError, ValidationError
from .services import GiveAccessService

GIVE_ACCESS_ACTIONS = (SERVICE_GIVE_ACCESS,)
PIN_SAFE_SCHEMA = vol.Schema({}, extra=vol.ALLOW_EXTRA)


def _required_uuid(call: ServiceCall, key: str) -> UUID:
    """Read a required UUID without echoing its input."""
    value = call.data.get(key)
    if not isinstance(value, str):
        raise ServiceValidationError(f"{key} is required")
    try:
        return UUID(value)
    except ValueError:
        raise ServiceValidationError(f"{key} must be a UUID") from None


def _required_pin(call: ServiceCall) -> str:
    """Read the invocation-only PIN without including it in errors."""
    value = call.data.get(ATTR_PIN)
    if not isinstance(value, str):
        raise ServiceValidationError("pin is required")
    return value


@callback
def async_register_give_access_actions(
    hass: HomeAssistant,
    service: GiveAccessService,
) -> None:
    """Register the Give Access application action."""

    async def handle_give_access(call: ServiceCall) -> ServiceResponse:
        try:
            result = await service.give_access(
                _required_uuid(call, ATTR_PERSON_ID),
                _required_uuid(call, ATTR_ACCESS_POINT_ID),
                _required_pin(call),
            )
        except DuplicateAccessError as err:
            raise ServiceValidationError(
                "This user already has access to the selected access point"
            ) from err
        except ValidationError as err:
            raise ServiceValidationError(str(err)) from None
        except ValueError as err:
            raise ServiceValidationError(str(err)) from None
        response: JsonObjectType = {
            "status": result.status,
            "person_display_name": result.person_display_name,
            "access_point_display_name": result.access_point_display_name,
            "slot": result.slot,
            "error": result.error,
        }
        if hass.config.debug and result.diagnostic is not None:
            response.update(
                {
                    "stage": result.diagnostic.stage,
                    "service": result.diagnostic.service,
                    "exception": result.diagnostic.exception,
                    "verification_status": result.diagnostic.verification_status,
                }
            )
        return response

    hass.services.async_register(
        DOMAIN,
        SERVICE_GIVE_ACCESS,
        handle_give_access,
        schema=PIN_SAFE_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )


@callback
def async_unregister_give_access_actions(hass: HomeAssistant) -> None:
    """Remove the Give Access action."""
    for action in GIVE_ACCESS_ACTIONS:
        hass.services.async_remove(DOMAIN, action)
