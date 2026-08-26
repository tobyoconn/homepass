"""Home Assistant action for safe in-memory AES-GCM compatibility testing."""

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

from .const import DOMAIN, SERVICE_TEST_VAULT_CRYPTO_RUNTIME
from .vault import crypto_runtime

VAULT_CRYPTO_SPIKE_ACTIONS = (SERVICE_TEST_VAULT_CRYPTO_RUNTIME,)
EMPTY_SCHEMA = vol.Schema({})


@callback
def async_register_vault_crypto_spike_action(hass: HomeAssistant) -> None:
    """Register the input-free compatibility action."""

    async def handle_runtime_check(_call: ServiceCall) -> ServiceResponse:
        result = crypto_runtime.run_crypto_runtime_check()
        return cast(ServiceResponse, result.to_dict())

    hass.services.async_register(
        DOMAIN,
        SERVICE_TEST_VAULT_CRYPTO_RUNTIME,
        handle_runtime_check,
        schema=EMPTY_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )


@callback
def async_unregister_vault_crypto_spike_action(hass: HomeAssistant) -> None:
    """Remove the compatibility action."""
    hass.services.async_remove(DOMAIN, SERVICE_TEST_VAULT_CRYPTO_RUNTIME)
