"""Nuki fingerprint status action behavior."""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from homeassistant.core import Context, HomeAssistant
from homeassistant.exceptions import ServiceValidationError

from custom_components.homepass.const import DOMAIN, SERVICE_GET_NUKI_FINGERPRINT_STATUS
from custom_components.homepass.nuki_fingerprint_actions import (
    async_register_nuki_fingerprint_actions,
    async_unregister_nuki_fingerprint_actions,
)


async def _status(hass: HomeAssistant, user_id: str, person_id: str, *, refresh: bool):
    return await hass.services.async_call(
        DOMAIN,
        SERVICE_GET_NUKI_FINGERPRINT_STATUS,
        {"person_id": person_id, "refresh_from_lock": refresh},
        blocking=True,
        return_response=True,
        context=Context(user_id=user_id),
    )


async def test_status_refresh_reads_nuki_before_returning(
    hass: HomeAssistant, hass_admin_user
) -> None:
    """An explicit UI refresh retrieves and processes fresh lock activity."""
    person_id = str(uuid4())
    fingerprint = AsyncMock()
    fingerprint.status_for_person.return_value = {
        "person_id": person_id,
        "fingerprint_data_stored": False,
        "doors": [],
    }
    audit = AsyncMock()
    async_register_nuki_fingerprint_actions(hass, fingerprint, audit)

    try:
        response = await _status(hass, hass_admin_user.id, person_id, refresh=True)
    finally:
        async_unregister_nuki_fingerprint_actions(hass)

    assert response["person_id"] == person_id
    audit.async_refresh.assert_awaited_once_with()
    fingerprint.status_for_person.assert_awaited_once()


async def test_passive_status_load_does_not_open_bluetooth_connection(
    hass: HomeAssistant, hass_admin_user
) -> None:
    """Opening a User remains fast and reads only HomePASS's saved status."""
    person_id = str(uuid4())
    fingerprint = AsyncMock()
    fingerprint.status_for_person.return_value = {"person_id": person_id, "doors": []}
    audit = AsyncMock()
    async_register_nuki_fingerprint_actions(hass, fingerprint, audit)

    try:
        await _status(hass, hass_admin_user.id, person_id, refresh=False)
    finally:
        async_unregister_nuki_fingerprint_actions(hass)

    audit.async_refresh.assert_not_awaited()


async def test_status_refresh_reports_bluetooth_failure_safely(
    hass: HomeAssistant, hass_admin_user
) -> None:
    """A failed explicit read gives useful guidance without provider internals."""
    person_id = str(uuid4())
    fingerprint = AsyncMock()
    audit = AsyncMock()
    audit.async_refresh.side_effect = RuntimeError("sensitive provider detail")
    async_register_nuki_fingerprint_actions(hass, fingerprint, audit)

    try:
        with pytest.raises(ServiceValidationError, match="over Bluetooth") as caught:
            await _status(hass, hass_admin_user.id, person_id, refresh=True)
    finally:
        async_unregister_nuki_fingerprint_actions(hass)

    assert "sensitive provider detail" not in str(caught.value)
    fingerprint.status_for_person.assert_not_awaited()
