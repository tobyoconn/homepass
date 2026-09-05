"""Private authenticated WebSocket transport for PIN replacement."""

from __future__ import annotations

from typing import Any
from uuid import UUID

import voluptuous as vol
from homeassistant.components.websocket_api import DOMAIN as WEBSOCKET_API_DOMAIN
from homeassistant.components.websocket_api import async_register_command
from homeassistant.components.websocket_api.connection import ActiveConnection
from homeassistant.components.websocket_api.decorators import async_response, websocket_command
from homeassistant.core import HomeAssistant, callback

from .exceptions import (
    ConcurrentCredentialReplacementError,
    CredentialReplacementError,
    LifecycleOperationExecutionError,
    ValidationError,
)
from .services.credential_replacement import CredentialReplacementLifecycleService

WS_TYPE_VALIDATE_REPLACEMENT_PIN = "homepass/validate_replacement_pin"
WS_TYPE_REPLACE_PIN = "homepass/replace_pin"


def _person_id(value: object) -> UUID:
    if not isinstance(value, str):
        raise ValueError
    try:
        return UUID(value)
    except ValueError:
        raise ValueError from None


def _authorize(connection: ActiveConnection, msg: dict[str, Any]) -> bool:
    if connection.user is not None and connection.user.is_admin:
        return True
    connection.send_error(msg["id"], "admin_required", "Administrator access required")
    return False


async def async_handle_validate_candidate(
    service: CredentialReplacementLifecycleService,
    connection: ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Return only whether a PIN is valid and differs from the current PIN."""
    if not _authorize(connection, msg):
        return
    try:
        changed = await service.validate_pin_candidate(_person_id(msg["person_id"]), msg["pin"])
    except ValueError, ValidationError:
        connection.send_result(msg["id"], {"valid": False, "changed": False})
    except Exception:
        connection.send_error(msg["id"], "validation_unavailable", "Unable to validate PIN")
    else:
        connection.send_result(msg["id"], {"valid": True, "changed": changed})


async def async_handle_replace_pin(
    service: CredentialReplacementLifecycleService,
    connection: ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Replace a PIN while returning only homeowner-safe outcomes."""
    if not _authorize(connection, msg):
        return
    try:
        person_id = _person_id(msg["person_id"])
        operation = (
            await service.retry_pin(person_id)
            if msg.get("retry") is True
            else await service.replace_pin(person_id, msg["pin"])
        )
    except ValueError, ValidationError:
        connection.send_error(msg["id"], "validation", "Enter a different valid PIN")
    except ConcurrentCredentialReplacementError:
        connection.send_error(msg["id"], "concurrent_update", "Access changed concurrently")
    except LifecycleOperationExecutionError:
        connection.send_error(msg["id"], "replacement_pending", "Replacement not confirmed")
    except CredentialReplacementError:
        connection.send_error(msg["id"], "replacement_unavailable", "Replacement unavailable")
    except Exception:
        connection.send_error(msg["id"], "replacement_failed", "Replacement failed")
    else:
        connection.send_result(msg["id"], {"completed": operation.status.value == "completed"})


@callback
def async_register_credential_replacement_websocket(
    hass: HomeAssistant, service: CredentialReplacementLifecycleService
) -> None:
    """Register private credential-replacement commands."""

    @websocket_command(
        {
            vol.Required("type"): WS_TYPE_VALIDATE_REPLACEMENT_PIN,
            vol.Required("person_id"): str,
            vol.Required("pin"): str,
        }
    )
    @async_response
    async def validate(
        _hass: HomeAssistant,
        connection: ActiveConnection,
        msg: dict[str, Any],
    ) -> None:
        await async_handle_validate_candidate(service, connection, msg)

    @websocket_command(
        {
            vol.Required("type"): WS_TYPE_REPLACE_PIN,
            vol.Required("person_id"): str,
            vol.Required("pin"): str,
            vol.Optional("retry", default=False): bool,
        }
    )
    @async_response
    async def replace(
        _hass: HomeAssistant,
        connection: ActiveConnection,
        msg: dict[str, Any],
    ) -> None:
        await async_handle_replace_pin(service, connection, msg)

    async_register_command(hass, validate)
    async_register_command(hass, replace)


@callback
def async_unregister_credential_replacement_websocket(hass: HomeAssistant) -> None:
    handlers = hass.data.get(WEBSOCKET_API_DOMAIN)
    if isinstance(handlers, dict):
        handlers.pop(WS_TYPE_VALIDATE_REPLACEMENT_PIN, None)
        handlers.pop(WS_TYPE_REPLACE_PIN, None)
