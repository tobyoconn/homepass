"""Home Assistant action for denied policy explanations."""

from __future__ import annotations

from datetime import UTC, datetime
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
from homeassistant.helpers import config_validation as cv

from .const import (
    ATTR_ACCESS_POINT_ID,
    ATTR_PERSON_ID,
    DOMAIN,
    SERVICE_GET_POLICY_EXPLANATION,
)
from .exceptions import HomePASSError
from .services import PolicyExplanationService

POLICY_EXPLANATION_ACTIONS = (SERVICE_GET_POLICY_EXPLANATION,)


def _uuid(value: object) -> UUID:
    """Validate and convert a UUID action field."""
    try:
        return UUID(cv.string(value))
    except ValueError as err:
        raise vol.Invalid("value must be a valid UUID") from err


POLICY_EXPLANATION_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_PERSON_ID): _uuid,
        vol.Required(ATTR_ACCESS_POINT_ID): _uuid,
    }
)


@callback
def async_register_policy_explanation_actions(
    hass: HomeAssistant,
    service: PolicyExplanationService,
) -> None:
    """Register the shared policy explanation action."""

    async def handle_get_policy_explanation(call: ServiceCall) -> ServiceResponse:
        try:
            explanation = await service.explain_denied_access(
                person_id=cast(UUID, call.data[ATTR_PERSON_ID]),
                access_point_id=cast(UUID, call.data[ATTR_ACCESS_POINT_ID]),
                instant_utc=datetime.now(UTC),
            )
        except HomePASSError, ValueError:
            raise HomeAssistantError("Policy explanation is unavailable") from None
        return cast(ServiceResponse, explanation.to_dict())

    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_POLICY_EXPLANATION,
        handle_get_policy_explanation,
        schema=POLICY_EXPLANATION_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )


@callback
def async_unregister_policy_explanation_actions(hass: HomeAssistant) -> None:
    """Remove the shared policy explanation action."""
    for action in POLICY_EXPLANATION_ACTIONS:
        hass.services.async_remove(DOMAIN, action)


__all__ = [
    "POLICY_EXPLANATION_ACTIONS",
    "async_register_policy_explanation_actions",
    "async_unregister_policy_explanation_actions",
]
