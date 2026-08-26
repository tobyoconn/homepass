"""Private authenticated WebSocket transport for Secure PIN Reveal."""

from __future__ import annotations

import logging
from collections.abc import Callable
from contextlib import suppress
from time import monotonic
from typing import Any
from uuid import UUID, uuid4

import voluptuous as vol
from homeassistant.components.websocket_api import DOMAIN as WEBSOCKET_API_DOMAIN
from homeassistant.components.websocket_api import async_register_command
from homeassistant.components.websocket_api.connection import ActiveConnection
from homeassistant.components.websocket_api.decorators import async_response, websocket_command
from homeassistant.core import HomeAssistant, callback

from .reveal import (
    CredentialRevealService,
    RevealAuditError,
    RevealCredentialUnavailableError,
    RevealError,
    RevealRateLimitedError,
    RevealVaultUnavailableError,
)

WS_TYPE_REVEAL_PIN = "homepass/reveal_pin"

_LOGGER = logging.getLogger(__name__)


def _request_trace(
    msg: dict[str, Any],
) -> tuple[str, Callable[[str], None], Callable[[str, str, str], None]]:
    """Create one safe request correlation and elapsed-time recorder."""
    try:
        request_id = str(_safe_uuid(msg.get("request_id")))
    except ValueError:
        request_id = str(uuid4())
    raw_asset_version = msg.get("panel_asset_version")
    asset_version = (
        raw_asset_version
        if isinstance(raw_asset_version, str)
        and (
            raw_asset_version == "dev"
            or (
                len(raw_asset_version) == 12
                and all(character in "0123456789abcdef" for character in raw_asset_version)
            )
        )
        else "unknown"
    )
    try:
        person_id = str(_safe_uuid(msg.get("person_id")))
    except ValueError:
        person_id = "invalid"
    raw_access_point_id = msg.get("access_point_id")
    try:
        access_point_id = (
            "person" if raw_access_point_id is None else str(_safe_uuid(raw_access_point_id))
        )
    except ValueError:
        access_point_id = "invalid"
    started = monotonic()

    def log(stage: str, error_code: str = "none", error_message: str = "none") -> None:
        try:
            _LOGGER.info(
                "PIN Reveal trace request_id=%s panel_asset_version=%s person_id=%s "
                "access_point_id=%s stage=%s error_code=%s error_message=%s elapsed_ms=%.3f",
                request_id,
                asset_version,
                person_id,
                access_point_id,
                stage,
                error_code,
                error_message,
                (monotonic() - started) * 1000,
            )
        except Exception:
            return

    def trace(stage: str) -> None:
        log(stage)

    def trace_error(stage: str, error_code: str, error_message: str) -> None:
        log(stage, error_code, error_message)

    return request_id, trace, trace_error


def _safe_uuid(value: object) -> UUID:
    """Parse a stable identifier without echoing caller input."""
    if not isinstance(value, str):
        raise ValueError
    try:
        return UUID(value)
    except ValueError:
        raise ValueError from None


async def async_handle_reveal(
    reveal_service: CredentialRevealService,
    connection: ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Authorize and answer exactly one direct Reveal request."""
    _request_id, trace, trace_error = _request_trace(msg)
    trace("websocket_handler_entered")
    user = connection.user
    if user is None or not user.is_admin:
        if user is not None:
            try:
                person_id = _safe_uuid(msg["person_id"])
                access_point_id = (
                    None
                    if msg.get("access_point_id") is None
                    else _safe_uuid(msg["access_point_id"])
                )
            except ValueError:
                pass
            else:
                with suppress(RevealAuditError):
                    await reveal_service.audit_denied(
                        user.id,
                        person_id,
                        access_point_id,
                        trace=trace,
                    )
        connection.send_error(msg["id"], "admin_required", "Administrator access required")
        trace_error(
            "websocket_error_returned",
            "admin_required",
            "administrator_access_required",
        )
        return
    trace("administrator_authorization_completed")

    try:
        person_id = _safe_uuid(msg["person_id"])
        access_point_id = (
            None if msg.get("access_point_id") is None else _safe_uuid(msg["access_point_id"])
        )
    except ValueError:
        connection.send_error(msg["id"], "credential_unavailable", "Credential unavailable")
        trace_error(
            "websocket_error_returned",
            "credential_unavailable",
            "credential_unavailable",
        )
        return

    try:
        plaintext = await reveal_service.reveal(
            user.id,
            person_id,
            access_point_id,
            trace=trace,
        )
    except RevealRateLimitedError as err:
        connection.send_error(
            msg["id"],
            "rate_limited",
            f"Too many requests. Try again in {err.retry_after} seconds.",
        )
        trace_error("websocket_error_returned", "rate_limited", "too_many_requests")
    except RevealCredentialUnavailableError:
        connection.send_error(msg["id"], "credential_unavailable", "Credential unavailable")
        trace_error(
            "websocket_error_returned",
            "credential_unavailable",
            "credential_unavailable",
        )
    except RevealVaultUnavailableError:
        connection.send_error(msg["id"], "vault_unavailable", "Vault unavailable")
        trace_error(
            "websocket_error_returned",
            "vault_unavailable",
            "vault_unavailable",
        )
    except RevealAuditError:
        connection.send_error(msg["id"], "reveal_failed", "Reveal failed")
        trace_error("websocket_error_returned", "reveal_failed", "audit_failed")
    except RevealError:
        connection.send_error(msg["id"], "reveal_failed", "Reveal failed")
        trace_error("websocket_error_returned", "reveal_failed", "retrieval_failed")
    else:
        connection.send_result(msg["id"], {"pin": plaintext})
        trace("websocket_result_returned")


@callback
def async_register_reveal_websocket(
    hass: HomeAssistant,
    reveal_service: CredentialRevealService,
) -> None:
    """Register the private direct-response Reveal command."""

    @websocket_command(
        {
            vol.Required("type"): WS_TYPE_REVEAL_PIN,
            vol.Required("person_id"): str,
            vol.Optional("access_point_id"): str,
            vol.Optional("request_id"): str,
            vol.Optional("panel_asset_version"): str,
        }
    )
    @async_response
    async def handle_reveal(
        _hass: HomeAssistant,
        connection: ActiveConnection,
        msg: dict[str, Any],
    ) -> None:
        await async_handle_reveal(reveal_service, connection, msg)

    async_register_command(hass, handle_reveal)


@callback
def async_unregister_reveal_websocket(hass: HomeAssistant) -> None:
    """Remove the private Reveal command when HomePASS unloads."""
    handlers = hass.data.get(WEBSOCKET_API_DOMAIN)
    if isinstance(handlers, dict):
        handlers.pop(WS_TYPE_REVEAL_PIN, None)


__all__ = [
    "WS_TYPE_REVEAL_PIN",
    "async_handle_reveal",
    "async_register_reveal_websocket",
    "async_unregister_reveal_websocket",
]
