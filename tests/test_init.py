"""Tests for HomePASS config-entry setup."""

import logging
from unittest.mock import AsyncMock

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import Context, HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry, MockUser

from custom_components.homepass.const import (
    CONF_NFC_PUBLIC_ORIGIN,
    CONF_NUKI_ENABLED,
    DOMAIN,
    SERVICE_CONFIGURE_NFC,
    SERVICE_PING,
)


async def test_setup_and_unload_entry(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test setting up and unloading a HomePASS config entry."""
    mock_config_entry.add_to_hass(hass)

    with caplog.at_level(logging.DEBUG, logger=f"custom_components.{DOMAIN}"):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        assert mock_config_entry.state is ConfigEntryState.LOADED
        assert f"Setting up HomePASS config entry {mock_config_entry.entry_id}" in caplog.text
        assert hass.services.has_service(DOMAIN, SERVICE_PING)

        caplog.clear()
        await hass.services.async_call(DOMAIN, SERVICE_PING, blocking=True)
        assert (
            f"custom_components.{DOMAIN}",
            logging.INFO,
            "HomePASS ping service called",
        ) in caplog.record_tuples

        assert await hass.config_entries.async_unload(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        assert mock_config_entry.state is ConfigEntryState.NOT_LOADED
        assert not hass.services.has_service(DOMAIN, SERVICE_PING)
        assert f"Unloading HomePASS config entry {mock_config_entry.entry_id}" in caplog.text


async def test_configure_nfc_action_updates_only_nfc_and_reloads(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    hass_admin_user: MockUser,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The focused NFC action preserves unrelated provider options."""
    mock_config_entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(mock_config_entry, options={CONF_NUKI_ENABLED: False})
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    reload_entry = AsyncMock(return_value=True)
    monkeypatch.setattr(hass.config_entries, "async_reload", reload_entry)

    response = await hass.services.async_call(
        DOMAIN,
        SERVICE_CONFIGURE_NFC,
        {CONF_NFC_PUBLIC_ORIGIN: "https://Example.ui.nabu.casa/"},
        blocking=True,
        return_response=True,
        context=Context(user_id=hass_admin_user.id),
    )
    await hass.async_block_till_done()

    assert response == {
        "public_origin": "https://example.ui.nabu.casa",
        "reload_pending": True,
    }
    assert mock_config_entry.options == {
        CONF_NUKI_ENABLED: False,
        CONF_NFC_PUBLIC_ORIGIN: "https://example.ui.nabu.casa",
    }
    reload_entry.assert_awaited_once_with(mock_config_entry.entry_id)
