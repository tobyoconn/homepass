"""Tests for guided User setup."""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from homeassistant.core import HomeAssistant

from custom_components.homepass.models import AccessPoint
from custom_components.homepass.repositories import (
    AccessPointEnrollmentRepository,
    CredentialMetadataRepository,
)
from custom_components.homepass.services import AccessPointEnrollment, UserSetupService
from custom_components.homepass.storage import HomePassStorageManager
from custom_components.homepass.user_setup_actions import CREATE_USER_SCHEMA
from custom_components.homepass.vault import VaultCredentialId


async def test_create_user_without_pin_stores_no_credential(hass: HomeAssistant) -> None:
    """A User can exist without any credential or initial Door assignment."""
    storage = HomePassStorageManager(hass)
    vault = AsyncMock()
    service = UserSetupService(
        storage,
        AsyncMock(),
        AsyncMock(),
        vault,
        CredentialMetadataRepository(storage),
    )
    request_id = uuid4()

    result = await service.create_user(
        request_id=request_id,
        display_name="NFC Guest",
        description=None,
        notes=None,
        enabled=True,
        pin=None,
        access_point_ids=(),
    )

    assert result.status == "completed"
    assert result.assignments == ()
    snapshot = await storage.async_load()
    assert str(result.person.person_id) in snapshot["data"]["people"]
    assert str(result.person.person_id) not in snapshot["data"]["credential_metadata"]
    vault.store.assert_not_awaited()

    repeated = await service.create_user(
        request_id=request_id,
        display_name="NFC Guest",
        description=None,
        notes=None,
        enabled=True,
        pin=None,
        access_point_ids=(),
    )
    assert repeated.person == result.person
    assert repeated.repeated is True


async def test_create_user_requires_pin_for_initial_keypad_access(
    hass: HomeAssistant,
) -> None:
    """Initial keypad provisioning cannot proceed without a PIN."""
    storage = HomePassStorageManager(hass)
    service = UserSetupService(
        storage,
        AsyncMock(),
        AsyncMock(),
        AsyncMock(),
        CredentialMetadataRepository(storage),
    )

    with pytest.raises(ValueError, match="PIN.*keypad Door access"):
        await service.create_user(
            request_id=uuid4(),
            display_name="Guest",
            description=None,
            notes=None,
            enabled=True,
            pin=None,
            access_point_ids=(uuid4(),),
        )


async def test_create_user_with_pin_preserves_existing_credential_flow(
    hass: HomeAssistant,
) -> None:
    """Providing a PIN still creates the Person's encrypted credential relationship."""
    storage = HomePassStorageManager(hass)
    vault = AsyncMock()
    credential_id = VaultCredentialId.new()
    vault.store.return_value = credential_id
    service = UserSetupService(
        storage,
        AsyncMock(),
        AsyncMock(),
        vault,
        CredentialMetadataRepository(storage),
    )

    result = await service.create_user(
        request_id=uuid4(),
        display_name="Keypad Guest",
        description=None,
        notes=None,
        enabled=True,
        pin="2468",
        access_point_ids=(),
    )

    vault.store.assert_awaited_once_with("2468")
    snapshot = await storage.async_load()
    credential = snapshot["data"]["credential_metadata"][str(result.person.person_id)]
    assert credential["credential_id"] == str(credential_id)


def test_create_user_action_schema_accepts_omitted_pin() -> None:
    """Home Assistant callers may create credential-free Users."""
    validated = CREATE_USER_SCHEMA(
        {
            "request_id": str(uuid4()),
            "display_name": "NFC Guest",
            "access_point_ids": [],
            "schedule": {"mode": "permanent"},
        }
    )

    assert "pin" not in validated
    assert validated["enabled"] is True


def test_add_user_frontend_presents_pin_as_optional() -> None:
    """The guided form must not imply that every User needs a PIN."""
    source = "custom_components/homepass/frontend/homepass-panel.js"
    with open(source, encoding="utf-8") as panel:
        content = panel.read()

    assert '"PIN (optional)"' in content
    assert "Leave blank for NFC or app-only users." in content
    assert "...(form.pin ? { pin: form.pin } : {})" in content


async def test_user_setup_options_keep_non_pin_doors_visible(
    hass: HomeAssistant,
) -> None:
    """App/NFC-capable Doors remain visible without becoming PIN assignments."""
    storage = HomePassStorageManager(hass)
    access_point = AccessPoint(display_name="Computer Room")
    await AccessPointEnrollmentRepository(storage).upsert(
        AccessPointEnrollment(
            access_point_id=access_point.id,
            discovery_key="manual:lock.computer_room",
            control_entity_id="lock.computer_room",
            pin_capable=False,
            nfc_capable=True,
            device_id="matter-device",
        ),
        access_point,
    )
    service = UserSetupService(
        storage,
        AsyncMock(),
        AsyncMock(),
        AsyncMock(),
        CredentialMetadataRepository(storage),
    )

    options = await service.get_options()

    assert options.access_points == (
        {
            "access_point_id": str(access_point.id),
            "display_name": "Computer Room",
            "enabled": True,
            "eligible": False,
            "pin_capable": False,
            "nfc_capable": True,
        },
    )


async def test_user_setup_options_use_live_provider_capability(
    hass: HomeAssistant,
) -> None:
    """The access editor sees Nuki PIN support for a manually named Matter Door."""
    storage = HomePassStorageManager(hass)
    access_point = AccessPoint(display_name="Computer Room")
    await AccessPointEnrollmentRepository(storage).upsert(
        AccessPointEnrollment(
            access_point_id=access_point.id,
            discovery_key="manual:lock.computer_room",
            control_entity_id="lock.computer_room",
            pin_capable=False,
            nfc_capable=True,
        ),
        access_point,
    )
    access_point_service = AsyncMock()
    access_point_service.list_access_point_summaries.return_value = (
        type(
            "Summary",
            (),
            {"access_point": access_point, "pin_capable": True, "nfc_capable": True},
        )(),
    )
    service = UserSetupService(
        storage,
        access_point_service,
        AsyncMock(),
        AsyncMock(),
        CredentialMetadataRepository(storage),
    )

    options = await service.get_options()

    assert options.access_points[0]["pin_capable"] is True
    assert options.access_points[0]["eligible"] is True


def test_add_user_frontend_explains_non_pin_doors() -> None:
    """The Add User form explains why a managed Door is not a PIN choice."""
    source = "custom_components/homepass/frontend/homepass-panel.js"
    with open(source, encoding="utf-8") as panel:
        content = panel.read()

    assert "Other HomePASS doors" in content
    assert "NFC access can be added after this user is created and enrolled." in content
