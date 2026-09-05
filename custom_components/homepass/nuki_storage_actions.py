"""Read-only administrator action for local Nuki keypad storage status."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, cast

import voluptuous as vol
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
    callback,
)
from homeassistant.exceptions import HomeAssistantError, Unauthorized

from .const import DOMAIN, SERVICE_GET_NUKI_STORAGE_STATUS
from .models import AccessDriver
from .providers import ProviderCommunicationError

if TYPE_CHECKING:
    from .providers import AuthorizationProvider
    from .services import AccessMetadataService, NukiFingerprintService

_SCAN_ATTEMPTS = 3
_SCAN_RETRY_DELAY = 2.0
_SCAN_ATTEMPT_TIMEOUT = 15.0


async def _require_admin(hass: HomeAssistant, call: ServiceCall) -> None:
    if call.context.user_id is None:
        raise Unauthorized(context=call.context)
    user = await hass.auth.async_get_user(call.context.user_id)
    if user is None or not user.is_admin:
        raise Unauthorized(context=call.context)


async def _load_status(
    provider: AuthorizationProvider | None,
    lock_entity_id: str,
    metadata_service: AccessMetadataService,
    fingerprint_service: NukiFingerprintService,
) -> dict[str, object]:
    """Build a secret-free status snapshot from the configured local provider."""
    if provider is None or not lock_entity_id:
        return {
            "configured": False,
            "lock_entity_id": lock_entity_id,
            "pins": {"total": 0, "managed": 0, "existing": 0, "entries": []},
            "fingerprints": {
                "linked_count": 0,
                "entries": [],
                "complete_lock_inventory_available": False,
            },
        }

    records = None
    for attempt in range(_SCAN_ATTEMPTS):
        try:
            async with asyncio.timeout(_SCAN_ATTEMPT_TIMEOUT):
                records = await provider.list_authorizations()
        except TimeoutError as err:
            communication_error = ProviderCommunicationError("Nuki keypad storage scan timed out")
            if attempt + 1 == _SCAN_ATTEMPTS:
                raise communication_error from err
            await asyncio.sleep(_SCAN_RETRY_DELAY)
        except ProviderCommunicationError:
            if attempt + 1 == _SCAN_ATTEMPTS:
                raise
            await asyncio.sleep(_SCAN_RETRY_DELAY)
        else:
            break
    if records is None:
        raise AssertionError("Nuki storage scan retry loop did not terminate")

    managed_ids = {
        str(record.slot)
        for record in await metadata_service.list_all()
        if record.driver is AccessDriver.NUKI and record.lock_entity_id == lock_entity_id
    }
    entries = [
        {
            "nuki_id": record.external_id,
            "name": record.display_name,
            "enabled": record.enabled,
            "management": ("homepass" if record.external_id in managed_ids else "existing"),
        }
        for record in records
    ]
    managed_count = sum(item["management"] == "homepass" for item in entries)
    return {
        "configured": True,
        "lock_entity_id": lock_entity_id,
        "pins": {
            "total": len(entries),
            "managed": managed_count,
            "existing": len(entries) - managed_count,
            "entries": entries,
        },
        "fingerprints": await fingerprint_service.storage_summary(lock_entity_id),
    }


@callback
def async_register_nuki_storage_action(
    hass: HomeAssistant,
    provider: AuthorizationProvider | None,
    lock_entity_id: str,
    metadata_service: AccessMetadataService,
    fingerprint_service: NukiFingerprintService,
) -> None:
    """Register the read-only Nuki storage inspection action."""

    async def status(call: ServiceCall) -> ServiceResponse:
        await _require_admin(hass, call)
        try:
            result = await _load_status(
                provider,
                lock_entity_id,
                metadata_service,
                fingerprint_service,
            )
        except ProviderCommunicationError as err:
            raise HomeAssistantError(
                "HomePASS could not read the Nuki keypad storage. Keep the lock "
                "within Bluetooth range and try again."
            ) from err
        return cast("ServiceResponse", result)

    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_NUKI_STORAGE_STATUS,
        status,
        schema=vol.Schema({}),
        supports_response=SupportsResponse.ONLY,
    )


@callback
def async_unregister_nuki_storage_action(hass: HomeAssistant) -> None:
    """Remove the Nuki storage inspection action."""
    hass.services.async_remove(DOMAIN, SERVICE_GET_NUKI_STORAGE_STATUS)


__all__ = [
    "async_register_nuki_storage_action",
    "async_unregister_nuki_storage_action",
]
