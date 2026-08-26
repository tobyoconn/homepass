"""Home Assistant actions for HomePASS Settings."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

import voluptuous as vol
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    SupportsResponse,
    callback,
)
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError, Unauthorized

from .const import (
    ATTR_PREFERENCES,
    ATTR_SETTINGS,
    CONF_NFC_PUBLIC_ORIGIN,
    DOMAIN,
    SERVICE_CONFIGURE_NFC,
    SERVICE_GET_NOTIFICATION_PREFERENCES,
    SERVICE_GET_PROPERTY_SETTINGS,
    SERVICE_SAVE_NOTIFICATION_PREFERENCES,
    SERVICE_SAVE_PROPERTY_SETTINGS,
)
from .models import PropertySettingsValidationError
from .nfc.webauthn_service import normalize_public_origin

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import ServiceResponse

    from .services import NotificationPreferencesService, PropertySettingsService

SETTINGS_ACTIONS = (
    SERVICE_GET_NOTIFICATION_PREFERENCES,
    SERVICE_SAVE_NOTIFICATION_PREFERENCES,
    SERVICE_GET_PROPERTY_SETTINGS,
    SERVICE_SAVE_PROPERTY_SETTINGS,
    SERVICE_CONFIGURE_NFC,
)


@callback
def async_register_settings_actions(
    hass: HomeAssistant,
    notification_service: NotificationPreferencesService,
    property_service: PropertySettingsService,
    entry: ConfigEntry,
) -> None:
    """Register presentation-safe Settings actions."""

    async def handle_get(_call: ServiceCall) -> ServiceResponse:
        try:
            settings = await notification_service.load()
        except (HomeAssistantError, KeyError, TypeError, ValueError):
            raise HomeAssistantError("Notification settings are unavailable") from None
        return cast("ServiceResponse", settings.to_dict())

    async def handle_save(call: ServiceCall) -> ServiceResponse:
        try:
            settings = await notification_service.save(call.data[ATTR_PREFERENCES])
        except (HomeAssistantError, KeyError, TypeError, ValueError):
            raise HomeAssistantError("Notification settings could not be saved") from None
        return cast("ServiceResponse", settings.to_dict())

    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_NOTIFICATION_PREFERENCES,
        handle_get,
        schema=vol.Schema({}),
        supports_response=SupportsResponse.ONLY,
    )

    async def handle_get_property(_call: ServiceCall) -> ServiceResponse:
        try:
            settings = await property_service.load()
        except (HomeAssistantError, KeyError, TypeError, ValueError):
            raise HomeAssistantError("Property Settings are unavailable") from None
        return cast("ServiceResponse", settings.to_dict())

    async def handle_save_property(call: ServiceCall) -> ServiceResponse:
        try:
            settings = await property_service.save(call.data[ATTR_SETTINGS])
        except PropertySettingsValidationError as err:
            return cast(
                "ServiceResponse",
                {
                    "settings": None,
                    "error": {"code": err.code, "message": err.user_message},
                },
            )
        except (HomeAssistantError, KeyError, TypeError, ValueError):
            raise HomeAssistantError("Property Settings could not be saved") from None
        return cast("ServiceResponse", settings.to_dict())

    async def handle_configure_nfc(call: ServiceCall) -> ServiceResponse:
        """Save the NFC-only prerequisite without exposing unrelated providers."""
        if call.context.user_id is None:
            raise Unauthorized(context=call.context)
        user = await hass.auth.async_get_user(call.context.user_id)
        if user is None or not user.is_admin:
            raise Unauthorized(context=call.context)
        try:
            public_origin = normalize_public_origin(str(call.data[CONF_NFC_PUBLIC_ORIGIN]))
        except (KeyError, TypeError, ValueError) as err:
            raise ServiceValidationError(
                "Enter a bare HTTPS address without a path, query, or sign-in details"
            ) from err
        options = {**entry.options, CONF_NFC_PUBLIC_ORIGIN: public_origin}
        hass.config_entries.async_update_entry(entry, options=options)
        return cast(
            "ServiceResponse",
            {"public_origin": public_origin, "reload_pending": True},
        )

    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_PROPERTY_SETTINGS,
        handle_get_property,
        schema=vol.Schema({}),
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SAVE_PROPERTY_SETTINGS,
        handle_save_property,
        schema=vol.Schema({vol.Required(ATTR_SETTINGS): dict}),
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SAVE_NOTIFICATION_PREFERENCES,
        handle_save,
        schema=vol.Schema({vol.Required(ATTR_PREFERENCES): dict}),
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_CONFIGURE_NFC,
        handle_configure_nfc,
        schema=vol.Schema({vol.Required(CONF_NFC_PUBLIC_ORIGIN): str}),
        supports_response=SupportsResponse.ONLY,
    )


@callback
def async_unregister_settings_actions(hass: HomeAssistant) -> None:
    """Remove Settings actions."""
    for action in SETTINGS_ACTIONS:
        hass.services.async_remove(DOMAIN, action)


__all__ = [
    "SETTINGS_ACTIONS",
    "async_register_settings_actions",
    "async_unregister_settings_actions",
]
