"""Public, cryptographically authenticated NFC and passkey HTTP views."""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import Any, Final

from aiohttp import web
from homeassistant.components.http import HomeAssistantView, StaticPathConfig
from homeassistant.core import HomeAssistant

from ..const import VERSION
from ..services import PropertySettingsService
from .access import TAP_SESSION_TTL_SECONDS, NfcAccessService
from .webauthn_service import HomePassWebAuthnService

_LOGGER = logging.getLogger(__name__)
_RUNTIME_KEY: Final = "homepass_nfc_runtime"
_REGISTERED_KEY: Final = "homepass_nfc_views_registered"
_STATIC_REGISTERED_KEY: Final = "homepass_nfc_static_registered"
_REGISTERED_VIEW_NAMES_KEY: Final = "homepass_nfc_registered_view_names"
_STATIC_PATH: Final = "/homepass_nfc_static"
_FRONTEND = Path(__file__).parent / "frontend"


@dataclass(frozen=True, slots=True)
class _Runtime:
    access: NfcAccessService
    webauthn: HomePassWebAuthnService
    property_settings: PropertySettingsService


def _headers() -> dict[str, str]:
    return {
        "Cache-Control": "no-store, max-age=0",
        "Content-Security-Policy": "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self'; connect-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'",
        "Referrer-Policy": "no-referrer",
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
    }


def _page(config: dict[str, Any]) -> web.Response:
    encoded = json.dumps(config, separators=(",", ":")).replace("<", "\\u003c")
    mode = config["mode"]
    test_mode = config.get("testMode") is True
    title = "Set up HomePASS" if mode == "enroll" else config.get("door", "Door access")
    property_name = config.get("property") or "HomePASS property"
    eyebrow = (
        "Secure enrollment"
        if mode == "enroll"
        else "NTAG216 test access"
        if test_mode
        else "Secure NFC access"
    )
    test_notice = '<p class="test-notice">Temporary NTAG216 test tag</p>' if test_mode else ""
    trust_copy = (
        "Protected by HomePASS, your current Door policy, and your device passkey."
        if test_mode
        else "Protected by HomePASS, secure NFC verification, and your device passkey."
    )
    authorization_notice = (
        '<p class="authorization-notice">HomePASS door access is for enrolled, '
        "authorized users only. If you are not enrolled, contact the property "
        "owner for entry.</p>"
        if mode != "enroll"
        else ""
    )
    body = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#2450e6"><title>{escape(title)} · HomePASS</title>
<link rel="icon" type="image/svg+xml" href="/homepass_static/assets/homepass-favicon.svg">
<link rel="stylesheet" href="{_STATIC_PATH}/nfc-access.css?version={VERSION}"></head>
<body><div class="page-shell"><main class="access-card" id="card">
<header class="brand-header"><img class="logo" src="/homepass_static/assets/homepass-mark-concept-1.png" alt="HomePASS">
<p class="property-context"><span class="property-label">Property</span><strong class="property-name">{escape(property_name)}</strong></p></header>
<section class="door-hero"><div class="door-symbol" aria-hidden="true"><img src="/homepass_static/assets/nfc-symbol.svg" alt=""></div>
{test_notice}<p class="eyebrow" id="eyebrow">{escape(eyebrow)}</p><h1 id="title">{escape(title)}</h1>
<p class="message" id="message">Preparing secure access…</p>{authorization_notice}</section>
<div class="access-action"><button id="primary" disabled>Loading…</button><div class="status" id="status" role="status" aria-live="polite"></div>
<p class="completion-note" id="completion-note" hidden>You’re finished here. You can safely close this page or navigate away.</p></div>
<footer class="trust-footer"><span class="trust-mark" aria-hidden="true">✓</span><p id="trust-copy">{escape(trust_copy)}</p></footer>
</main></div><script type="application/json" id="homepass-config">{encoded}</script><script src="{_STATIC_PATH}/nfc-access.js?version={VERSION}" defer></script></body></html>"""
    return web.Response(text=body, content_type="text/html", headers=_headers())


async def _property_name(runtime: _Runtime) -> str:
    try:
        return (await runtime.property_settings.load()).settings.property_name
    except Exception:  # noqa: BLE001 - branding must not block secure access
        _LOGGER.warning("HomePASS property name could not be loaded for an NFC page")
        return ""


def _json(data: dict[str, Any], status: int = 200) -> web.Response:
    return web.json_response(data, status=status, headers=_headers())


async def _body(request: web.Request) -> dict[str, Any]:
    if request.content_length is not None and request.content_length > 64_000:
        raise web.HTTPRequestEntityTooLarge(max_size=64_000, actual_size=request.content_length)
    try:
        raw = await request.content.readexactly(64_001)
    except asyncio.IncompleteReadError as err:
        raw = err.partial
    else:
        raise web.HTTPRequestEntityTooLarge(max_size=64_000, actual_size=len(raw))
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as err:
        raise web.HTTPBadRequest(text="Invalid JSON request") from err
    if not isinstance(data, dict):
        raise web.HTTPBadRequest(text="Invalid request")
    return data


class _NfcView(HomeAssistantView):
    requires_auth = False

    def __init__(self, hass: HomeAssistant) -> None:
        self._hass = hass

    def runtime(self, request: web.Request) -> _Runtime:
        runtime = self._hass.data.get(_RUNTIME_KEY)
        if not isinstance(runtime, _Runtime):
            raise web.HTTPServiceUnavailable(text="HomePASS NFC is unavailable")
        if (
            request.method == "POST"
            and request.headers.get("Origin") != runtime.webauthn.public_origin
        ):
            raise web.HTTPForbidden(text="Request origin is invalid")
        return runtime


class NfcTapView(_NfcView):
    url = "/api/homepass/nfc/t/{public_id}"
    name = "api:homepass:nfc:tap"

    async def get(self, request: web.Request, public_id: str) -> web.Response:
        runtime = self.runtime(request)
        property_name = await _property_name(runtime)
        try:
            ready = await runtime.access.begin_tap(
                public_id=public_id,
                encrypted_picc=request.query.get("e", ""),
                mac=request.query.get("c", ""),
            )
            return _page(
                {
                    "mode": "unlock",
                    "tapSession": ready.tap_session,
                    "door": ready.door_name,
                    "property": property_name,
                    "action": ready.action,
                    "expiresInMs": TAP_SESSION_TTL_SECONDS * 1000,
                }
            )
        except Exception:  # noqa: BLE001 - opaque public response
            _LOGGER.debug("An NFC tap failed cryptographic or capability validation")
            return _page({"mode": "unavailable", "property": property_name})


class NfcTestTapView(_NfcView):
    url = "/api/homepass/nfc/test/{token}"
    name = "api:homepass:nfc:test_tap"

    async def get(self, request: web.Request, token: str) -> web.Response:
        runtime = self.runtime(request)
        property_name = await _property_name(runtime)
        try:
            ready = await runtime.access.begin_test_tap(raw_token=token)
            return _page(
                {
                    "mode": "unlock",
                    "tapSession": ready.tap_session,
                    "door": ready.door_name,
                    "property": property_name,
                    "action": ready.action,
                    "testMode": True,
                    "expiresInMs": TAP_SESSION_TTL_SECONDS * 1000,
                }
            )
        except Exception:  # noqa: BLE001 - opaque public response
            _LOGGER.debug("An NTAG216 test tap failed validation")
            return _page({"mode": "unavailable", "property": property_name})


class EnrollmentPageView(_NfcView):
    url = "/api/homepass/nfc/enroll/{token}"
    name = "api:homepass:nfc:enrollment_page"

    async def get(self, request: web.Request, token: str) -> web.Response:
        runtime = self.runtime(request)
        return _page(
            {"mode": "enroll", "inviteToken": token, "property": await _property_name(runtime)}
        )


class RegistrationOptionsView(_NfcView):
    url = "/api/homepass/nfc/passkey/register/options"
    name = "api:homepass:nfc:registration_options"

    async def post(self, request: web.Request) -> web.Response:
        runtime, data = self.runtime(request), await _body(request)
        try:
            return _json(
                await runtime.webauthn.begin_registration(
                    str(data["inviteToken"]), property_name=await _property_name(runtime)
                )
            )
        except Exception:
            return _json({"error": "This enrollment link is invalid or expired."}, 403)


class RegistrationCompleteView(_NfcView):
    url = "/api/homepass/nfc/passkey/register/complete"
    name = "api:homepass:nfc:registration_complete"

    async def post(self, request: web.Request) -> web.Response:
        runtime, data = self.runtime(request), await _body(request)
        try:
            await runtime.webauthn.finish_registration(
                str(data["ceremony"]), dict(data["credential"])
            )
            return _json({"ok": True})
        except Exception:
            return _json({"error": "Passkey enrollment could not be verified."}, 403)


class AuthenticationOptionsView(_NfcView):
    url = "/api/homepass/nfc/passkey/authenticate/options"
    name = "api:homepass:nfc:authentication_options"

    async def post(self, request: web.Request) -> web.Response:
        runtime, data = self.runtime(request), await _body(request)
        try:
            tap_session = str(data["tapSession"])
            runtime.access.validate_tap_session(tap_session)
            return _json(runtime.webauthn.begin_authentication(tap_session))
        except Exception:
            return _json({"error": "This NFC tap has expired. Please tap again."}, 403)


class AuthenticationCompleteView(_NfcView):
    url = "/api/homepass/nfc/passkey/authenticate/complete"
    name = "api:homepass:nfc:authentication_complete"

    async def post(self, request: web.Request) -> web.Response:
        runtime, data = self.runtime(request), await _body(request)
        try:
            identity = await runtime.webauthn.finish_authentication(
                str(data["ceremony"]), dict(data["credential"])
            )
            result = await runtime.access.operate(
                tap_session=identity.tap_session, person_id=identity.person_id
            )
            return _json(
                {
                    "allowed": result.allowed,
                    "door": result.door_name,
                    "message": result.message,
                    "action": result.action,
                    "testMode": result.test_mode,
                },
                200 if result.allowed else 403,
            )
        except Exception:
            _LOGGER.debug("An NFC passkey access attempt failed")
            return _json(
                {"allowed": False, "message": "Access could not be verified. Please tap again."},
                403,
            )


async def async_register_nfc_views(
    hass: HomeAssistant,
    access: NfcAccessService,
    webauthn: HomePassWebAuthnService,
    property_settings: PropertySettingsService,
) -> None:
    hass.data[_RUNTIME_KEY] = _Runtime(access, webauthn, property_settings)
    if hass.data.get(_REGISTERED_KEY):
        return
    if not hass.data.get(_STATIC_REGISTERED_KEY):
        await hass.http.async_register_static_paths(
            [StaticPathConfig(_STATIC_PATH, str(_FRONTEND), False)]
        )
        hass.data[_STATIC_REGISTERED_KEY] = True
    registered_names = hass.data.setdefault(_REGISTERED_VIEW_NAMES_KEY, set())
    for view in (
        NfcTapView,
        NfcTestTapView,
        EnrollmentPageView,
        RegistrationOptionsView,
        RegistrationCompleteView,
        AuthenticationOptionsView,
        AuthenticationCompleteView,
    ):
        if view.name in registered_names:
            continue
        hass.http.register_view(view(hass))
        registered_names.add(view.name)
    hass.data[_REGISTERED_KEY] = True


def async_unregister_nfc_views(hass: HomeAssistant) -> None:
    hass.data.pop(_RUNTIME_KEY, None)


__all__ = ["async_register_nfc_views", "async_unregister_nfc_views"]
