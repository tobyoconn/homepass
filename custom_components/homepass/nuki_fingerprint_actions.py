"""Administrator actions for guided Nuki fingerprint enrollment."""

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
from homeassistant.exceptions import ServiceValidationError, Unauthorized

from .const import (
    ATTR_ACCESS_POINT_ID,
    ATTR_PERSON_ID,
    DOMAIN,
    SERVICE_COMPLETE_NUKI_FINGERPRINT_ENROLLMENT,
    SERVICE_GET_NUKI_FINGERPRINT_STATUS,
    SERVICE_START_NUKI_FINGERPRINT_ENROLLMENT,
)

if TYPE_CHECKING:
    from .services import NukiFingerprintService
    from .services.nuki_audit_ingestion import NukiAuditIngestionService

_ATTR_REFRESH_FROM_LOCK = "refresh_from_lock"


async def _require_admin(hass: HomeAssistant, call: ServiceCall) -> None:
    if call.context.user_id is None:
        raise Unauthorized(context=call.context)
    user = await hass.auth.async_get_user(call.context.user_id)
    if user is None or not user.is_admin:
        raise Unauthorized(context=call.context)


@callback
def async_register_nuki_fingerprint_actions(
    hass: HomeAssistant,
    service: NukiFingerprintService,
    audit_ingestion: NukiAuditIngestionService | None,
) -> None:
    """Register the non-biometric enrollment coordination actions."""

    async def status(call: ServiceCall) -> ServiceResponse:
        await _require_admin(hass, call)
        try:
            audit_check: dict[str, int] | None = None
            if call.data[_ATTR_REFRESH_FROM_LOCK]:
                if audit_ingestion is None:
                    raise ValueError("Local Nuki audit access is not configured")
                audit_check = await audit_ingestion.async_refresh()
            result = await service.status_for_person(UUID(call.data[ATTR_PERSON_ID]))
            if audit_check is not None:
                result = {**result, "audit_check": audit_check}
        except (KeyError, TypeError, ValueError) as err:
            raise ServiceValidationError(str(err)) from err
        except Exception as err:  # noqa: BLE001 - return a secret-safe UI error
            raise ServiceValidationError(
                "HomePASS could not read the Nuki activity log over Bluetooth. "
                "Check that the lock is nearby and online, then try again."
            ) from err
        return cast("ServiceResponse", result)

    async def start(call: ServiceCall) -> ServiceResponse:
        await _require_admin(hass, call)
        try:
            result = await service.start(
                UUID(call.data[ATTR_PERSON_ID]), UUID(call.data[ATTR_ACCESS_POINT_ID])
            )
        except (KeyError, TypeError, ValueError) as err:
            raise ServiceValidationError(str(err)) from err
        return cast("ServiceResponse", result)

    async def complete(call: ServiceCall) -> ServiceResponse:
        await _require_admin(hass, call)
        try:
            result = await service.mark_nuki_app_complete(
                UUID(call.data[ATTR_PERSON_ID]), UUID(call.data[ATTR_ACCESS_POINT_ID])
            )
        except (KeyError, TypeError, ValueError) as err:
            raise ServiceValidationError(str(err)) from err
        return cast("ServiceResponse", result)

    person_schema = vol.Schema(
        {
            vol.Required(ATTR_PERSON_ID): str,
            vol.Optional(_ATTR_REFRESH_FROM_LOCK, default=False): bool,
        }
    )
    enrollment_schema = vol.Schema(
        {
            vol.Required(ATTR_PERSON_ID): str,
            vol.Required(ATTR_ACCESS_POINT_ID): str,
        }
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_NUKI_FINGERPRINT_STATUS,
        status,
        schema=person_schema,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_START_NUKI_FINGERPRINT_ENROLLMENT,
        start,
        schema=enrollment_schema,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_COMPLETE_NUKI_FINGERPRINT_ENROLLMENT,
        complete,
        schema=enrollment_schema,
        supports_response=SupportsResponse.ONLY,
    )


@callback
def async_unregister_nuki_fingerprint_actions(hass: HomeAssistant) -> None:
    """Remove guided fingerprint enrollment actions."""
    for action in (
        SERVICE_GET_NUKI_FINGERPRINT_STATUS,
        SERVICE_START_NUKI_FINGERPRINT_ENROLLMENT,
        SERVICE_COMPLETE_NUKI_FINGERPRINT_ENROLLMENT,
    ):
        hass.services.async_remove(DOMAIN, action)


__all__ = [
    "async_register_nuki_fingerprint_actions",
    "async_unregister_nuki_fingerprint_actions",
]
