"""NFC setup discovers Cloud only on request and preserves an established origin."""

from unittest.mock import AsyncMock, Mock

import pytest
from homeassistant.core import Context, HomeAssistant
from homeassistant.exceptions import ServiceValidationError, Unauthorized
from homeassistant.helpers.network import NoURLAvailableError
from pytest_homeassistant_custom_component.common import MockConfigEntry, MockUser

from custom_components.homepass import settings_actions
from custom_components.homepass.const import (
    CONF_NFC_PUBLIC_ORIGIN,
    CONF_NUKI_ENABLED,
    DOMAIN,
    SERVICE_CONFIGURE_NFC,
)


@pytest.fixture
async def nfc_setup(hass: HomeAssistant, mock_config_entry: MockConfigEntry, monkeypatch):
    """Load the actual integration and watch its option-update reload listener."""
    mock_config_entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(mock_config_entry, options={CONF_NUKI_ENABLED: False})
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    reload_entry = AsyncMock(return_value=True)
    monkeypatch.setattr(hass.config_entries, "async_reload", reload_entry)
    return mock_config_entry, reload_entry


async def configure(hass, user, data=None):
    return await hass.services.async_call(
        DOMAIN,
        SERVICE_CONFIGURE_NFC,
        data or {},
        blocking=True,
        return_response=True,
        context=Context(user_id=user.id if user else None),
    )


async def test_discovers_cloud_saves_once_and_preserves_other_options(
    hass, hass_admin_user, nfc_setup, monkeypatch
):
    entry, reload_entry = nfc_setup
    lookup = Mock(return_value="https://Example.ui.nabu.casa/")
    monkeypatch.setattr(settings_actions, "get_url", lookup)
    # Merely loading HomePASS does not enable NFC.
    assert CONF_NFC_PUBLIC_ORIGIN not in entry.options
    lookup.assert_not_called()

    response = await configure(hass, hass_admin_user)
    await hass.async_block_till_done()
    assert response == {"public_origin": "https://example.ui.nabu.casa", "reload_pending": True}
    lookup.assert_called_once_with(
        hass, require_cloud=True, require_ssl=True, allow_internal=False, allow_ip=False
    )
    assert entry.options == {
        CONF_NUKI_ENABLED: False,
        CONF_NFC_PUBLIC_ORIGIN: "https://example.ui.nabu.casa",
    }
    reload_entry.assert_awaited_once_with(entry.entry_id)

    # Retrying after a Cloud domain change must not replace tags' or passkeys' origin.
    lookup.return_value = "https://changed.ui.nabu.casa"
    again = await configure(hass, hass_admin_user)
    await hass.async_block_till_done()
    assert again == {"public_origin": response["public_origin"], "reload_pending": False}
    assert lookup.call_count == 1
    assert reload_entry.await_count == 1


async def test_saved_custom_origin_is_used_without_cloud_lookup(
    hass, hass_admin_user, nfc_setup, monkeypatch
):
    entry, reload_entry = nfc_setup
    hass.config_entries.async_update_entry(
        entry, options={**entry.options, CONF_NFC_PUBLIC_ORIGIN: "https://access.example.com"}
    )
    await hass.async_block_till_done()
    reload_entry.reset_mock()
    lookup = Mock(side_effect=AssertionError("A saved origin must not need Cloud"))
    monkeypatch.setattr(settings_actions, "get_url", lookup)
    response = await configure(hass, hass_admin_user)
    await hass.async_block_till_done()
    assert response == {"public_origin": "https://access.example.com", "reload_pending": False}
    reload_entry.assert_not_awaited()


async def test_cloud_absent_does_not_use_local_or_other_external_url(
    hass, hass_admin_user, nfc_setup
):
    entry, reload_entry = nfc_setup
    hass.config.internal_url = "http://homeassistant.local:8123"
    hass.config.external_url = "https://access.example.com"
    # Exercise the real HA URL helper with no Cloud integration loaded.
    response = await configure(hass, hass_admin_user)
    await hass.async_block_till_done()
    assert response == {
        "public_origin": None,
        "reload_pending": False,
        "reason": "cloud_unavailable",
    }
    assert entry.options == {CONF_NUKI_ENABLED: False}
    reload_entry.assert_not_awaited()


async def test_cloud_unavailable_can_be_retried(hass, hass_admin_user, nfc_setup, monkeypatch):
    entry, reload_entry = nfc_setup
    lookup = Mock(side_effect=[NoURLAvailableError(), "https://example.ui.nabu.casa"])
    monkeypatch.setattr(settings_actions, "get_url", lookup)
    assert (await configure(hass, hass_admin_user))["reason"] == "cloud_unavailable"
    assert CONF_NFC_PUBLIC_ORIGIN not in entry.options
    assert (await configure(hass, hass_admin_user))["reload_pending"] is True
    await hass.async_block_till_done()
    reload_entry.assert_awaited_once()


@pytest.mark.parametrize("admin", [False, None])
async def test_automatic_setup_requires_an_administrator(hass, nfc_setup, monkeypatch, admin):
    entry, reload_entry = nfc_setup
    user = MockUser().add_to_hass(hass) if admin is False else None
    lookup = Mock()
    monkeypatch.setattr(settings_actions, "get_url", lookup)
    with pytest.raises(Unauthorized):
        await configure(hass, user)
    lookup.assert_not_called()
    reload_entry.assert_not_awaited()
    assert CONF_NFC_PUBLIC_ORIGIN not in entry.options


@pytest.mark.parametrize(
    "origin", ["", "http://example.ui.nabu.casa", "https://example.ui.nabu.casa/path"]
)
async def test_invalid_manual_origin_never_triggers_discovery(
    hass, hass_admin_user, nfc_setup, monkeypatch, origin
):
    lookup = Mock()
    monkeypatch.setattr(settings_actions, "get_url", lookup)
    with pytest.raises(ServiceValidationError):
        await configure(hass, hass_admin_user, {CONF_NFC_PUBLIC_ORIGIN: origin})
    lookup.assert_not_called()
    assert CONF_NFC_PUBLIC_ORIGIN not in nfc_setup[0].options
