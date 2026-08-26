"""Home Assistant panel registration for HomePASS."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from typing import Final

from homeassistant.components import frontend, panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

from .const import DOMAIN, NAME

PANEL_URL_PATH: Final = DOMAIN
PANEL_STATIC_PATH: Final = "/homepass_static"
PANEL_MODULE_PATH: Final = "/homepass_static/homepass-panel.js"

_DATA_STATIC_REGISTERED: Final = f"{DOMAIN}_panel_static_registered"
_FRONTEND_DIRECTORY = Path(__file__).parent / "frontend"
_PANEL_FILE = _FRONTEND_DIRECTORY / "homepass-panel.js"
_MARK_FILE = _FRONTEND_DIRECTORY / "assets" / "homepass-mark-concept-1.png"
_DOOR_STATUS_ICON_FILES = tuple(
    _FRONTEND_DIRECTORY / "assets" / "icons" / filename
    for filename in (
        "door_closed_locked.svg",
        "door_closed_unlocked.svg",
        "door_lock_only_locked.svg",
        "door_lock_only_unlocked.svg",
        "door_open_locked.svg",
        "door_open_unlocked.svg",
        "door_unknown.svg",
    )
)
_PANEL_ASSET_VERSION: Final = sha256(
    b"".join(asset.read_bytes() for asset in (_PANEL_FILE, _MARK_FILE, *_DOOR_STATUS_ICON_FILES))
).hexdigest()[:12]
PANEL_WEB_COMPONENT: Final = f"homepass-panel-{_PANEL_ASSET_VERSION}"
PANEL_MODULE_URL: Final = f"{PANEL_MODULE_PATH}?version={_PANEL_ASSET_VERSION}"


async def async_register_homepass_panel(hass: HomeAssistant) -> None:
    """Register the HomePASS frontend asset and sidebar panel."""
    if not hass.data.get(_DATA_STATIC_REGISTERED):
        await hass.http.async_register_static_paths(
            [StaticPathConfig(PANEL_STATIC_PATH, str(_FRONTEND_DIRECTORY), True)]
        )
        hass.data[_DATA_STATIC_REGISTERED] = True

    await panel_custom.async_register_panel(
        hass,
        frontend_url_path=PANEL_URL_PATH,
        webcomponent_name=PANEL_WEB_COMPONENT,
        sidebar_title=NAME,
        sidebar_icon="mdi:account-key",
        module_url=PANEL_MODULE_URL,
        require_admin=False,
    )


def async_unregister_homepass_panel(hass: HomeAssistant) -> None:
    """Remove the HomePASS sidebar panel."""
    frontend.async_remove_panel(hass, PANEL_URL_PATH)
