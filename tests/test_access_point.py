"""Tests for managed Door binding updates."""

from dataclasses import replace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from custom_components.homepass.access_point_actions import UPDATE_ACCESS_POINT_SCHEMA
from custom_components.homepass.models import AccessDriver, AccessPoint
from custom_components.homepass.services import (
    AccessPointAvailability,
    AccessPointEnrollment,
    AccessPointService,
    AccessPointState,
    AccessPointTarget,
)


async def test_update_access_point_status_preserves_control_binding() -> None:
    """Changing a contact sensor does not recreate or replace its Door."""
    access_point = AccessPoint(display_name="Computer Room")
    enrollment = AccessPointEnrollment(
        access_point_id=access_point.id,
        discovery_key="manual:lock.computer_room",
        control_entity_id="lock.computer_room",
        status_entity_id=None,
        control_profile="lock",
        pin_capable=False,
        nfc_capable=True,
        device_id="matter-device",
    )
    enrollment_store = AsyncMock()
    enrollment_store.list_all.return_value = (enrollment,)
    policy_store = AsyncMock()
    policy_store.get.return_value = access_point
    state_resolver = AsyncMock()
    state_resolver.resolve_state.return_value = AccessPointState(
        AccessPointAvailability.AVAILABLE,
        lock_state="locked",
        door_state="closed",
        lock_entity_id="lock.computer_room",
        door_entity_id="binary_sensor.computer_room_door",
    )
    service = AccessPointService(
        enrollment_store=enrollment_store,
        policy_store=policy_store,
        state_resolver=state_resolver,
    )

    summary = await service.update_access_point_status(
        access_point.id,
        status_entity_id="binary_sensor.computer_room_door",
        status_inverted=True,
    )

    updated = replace(
        enrollment,
        status_entity_id="binary_sensor.computer_room_door",
        status_inverted=True,
    )
    enrollment_store.upsert.assert_awaited_once_with(
        updated,
        access_point,
        expected_policy_updated_at=access_point.updated_at,
    )
    target = state_resolver.resolve_state.await_args.args[0]
    assert target.control_entity_id == "lock.computer_room"
    assert target.status_entity_id == "binary_sensor.computer_room_door"
    capabilities = summary.to_dict()["capabilities"]
    assert isinstance(capabilities, dict)
    assert capabilities["status_editable"] is True


async def test_pulse_door_cannot_lose_required_status_sensor() -> None:
    """Removing confirmation from a toggle Door is rejected safely."""
    access_point = AccessPoint(display_name="Garage")
    enrollment_store = AsyncMock()
    enrollment_store.list_all.return_value = (
        AccessPointEnrollment(
            access_point_id=access_point.id,
            discovery_key="manual:switch.garage",
            control_entity_id="switch.garage",
            status_entity_id="binary_sensor.garage_door",
            control_profile="garage_toggle",
            device_id="relay-device",
        ),
    )
    policy_store = AsyncMock()
    service = AccessPointService(
        enrollment_store=enrollment_store,
        policy_store=policy_store,
    )

    with pytest.raises(ValueError, match="requires an open/closed status entity"):
        await service.update_access_point_status(
            access_point.id,
            status_entity_id=None,
            status_inverted=False,
        )

    policy_store.get.assert_not_awaited()
    enrollment_store.upsert.assert_not_awaited()


def test_update_access_point_schema_accepts_sensor_only_update_and_clear() -> None:
    """Home Assistant callers can change or clear a sensor without renaming the Door."""
    access_point_id = str(uuid4())

    selected = UPDATE_ACCESS_POINT_SCHEMA(
        {
            "access_point_id": access_point_id,
            "status_entity_id": "binary_sensor.computer_room_door",
            "status_inverted": False,
        }
    )
    cleared = UPDATE_ACCESS_POINT_SCHEMA(
        {
            "access_point_id": access_point_id,
            "status_entity_id": None,
            "status_inverted": False,
        }
    )

    assert selected["status_entity_id"] == "binary_sensor.computer_room_door"
    assert cleared["status_entity_id"] is None


async def test_manual_matter_door_inherits_live_nuki_pin_capability() -> None:
    """A manually named Door still uses its discovered Nuki provider adapter."""
    access_point = AccessPoint(display_name="Computer Room")
    enrollment = AccessPointEnrollment(
        access_point_id=access_point.id,
        discovery_key="manual:lock.computer_room",
        control_entity_id="lock.computer_room",
        pin_capable=False,
        nfc_capable=True,
    )
    enrollment_store = AsyncMock()
    enrollment_store.list_all.return_value = (enrollment,)
    policy_store = AsyncMock()
    policy_store.list_all.return_value = (access_point,)
    discovery = AsyncMock()
    discovery.discover_targets.return_value = (
        AccessPointTarget(
            AccessPoint(display_name="Nuki Smart Lock"),
            "lock.computer_room",
            driver=AccessDriver.NUKI,
            pin_capable=True,
        ),
    )
    service = AccessPointService(
        target_discovery=discovery,
        enrollment_store=enrollment_store,
        policy_store=policy_store,
    )

    target = await service.get_target(access_point.id)

    assert target.driver is AccessDriver.NUKI
    assert target.pin_capable is True
    assert target.access_point.display_name == "Computer Room"
