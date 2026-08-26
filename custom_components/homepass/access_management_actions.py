"""Home Assistant action for editing access assignments."""

from __future__ import annotations

from uuid import UUID

import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse, callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.util.json import JsonObjectType

from .const import (
    ATTR_ACCESS_POINT_IDS,
    ATTR_PERSON_ID,
    DOMAIN,
    SERVICE_UPDATE_ACCESS,
)
from .exceptions import AccessUpdateError
from .services import AccessManagementService

UPDATE_ACCESS_ACTIONS = (SERVICE_UPDATE_ACCESS,)
UPDATE_ACCESS_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_PERSON_ID): str,
        vol.Required(ATTR_ACCESS_POINT_IDS): [str],
    }
)


def _uuid(value: str, field_name: str) -> UUID:
    """Parse one UUID without reflecting invalid input."""
    try:
        return UUID(value)
    except ValueError:
        raise ServiceValidationError(f"{field_name} must contain UUID values") from None


@callback
def async_register_access_management_actions(
    hass: HomeAssistant,
    service: AccessManagementService,
) -> None:
    """Register the access-management application action."""

    async def handle_update_access(call: ServiceCall) -> JsonObjectType:
        person_id = _uuid(call.data[ATTR_PERSON_ID], ATTR_PERSON_ID)
        access_point_ids = tuple(
            _uuid(value, ATTR_ACCESS_POINT_IDS) for value in call.data[ATTR_ACCESS_POINT_IDS]
        )
        try:
            result = await service.update_access(person_id, access_point_ids)
        except ValueError as err:
            raise ServiceValidationError(str(err)) from None
        except AccessUpdateError as err:
            return {
                "status": "failed",
                "reason": (
                    "pin_incompatible"
                    if err.exception_type == "CredentialCompatibilityError"
                    else "access_update_failed"
                ),
                "added": [],
                "removed": [],
                "unchanged": [],
                "access_points": (
                    []
                    if err.access_point_id is None
                    else [
                        {
                            "access_point_id": str(err.access_point_id),
                            "status": "failed",
                        }
                    ]
                ),
            }
        return {
            "status": result.status,
            "added": [str(access_point_id) for access_point_id in result.added],
            "removed": [str(access_point_id) for access_point_id in result.removed],
            "unchanged": [str(access_point_id) for access_point_id in result.unchanged],
            "access_points": [
                {
                    "access_point_id": str(access_point.access_point_id),
                    "status": access_point.status,
                }
                for access_point in result.access_points
            ],
        }

    hass.services.async_register(
        DOMAIN,
        SERVICE_UPDATE_ACCESS,
        handle_update_access,
        schema=UPDATE_ACCESS_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )


@callback
def async_unregister_access_management_actions(hass: HomeAssistant) -> None:
    """Remove access-management actions."""
    for action in UPDATE_ACCESS_ACTIONS:
        hass.services.async_remove(DOMAIN, action)
