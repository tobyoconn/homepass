"""Tests for Door-associated HomePASS devices."""

from datetime import UTC, datetime
from uuid import UUID

import pytest

from custom_components.homepass.models import (
    PERMANENT_SCHEDULE_ID,
    AccessDevice,
    AccessDeviceIntegration,
    AccessDeviceSetupState,
    AccessDriver,
    AccessMetadata,
    AccessPointSynchronization,
    KeypadOperation,
    SynchronizationStatus,
    permanent_schedule,
)
from custom_components.homepass.services.access_management import _next_available_keypad_slot
from custom_components.homepass.storage import async_migrate_storage
from custom_components.homepass.vault import VaultCredentialId

ACCESS_POINT_ID = UUID("00000000-0000-4000-8000-000000000101")
ACCESS_DEVICE_ID = UUID("00000000-0000-4000-8000-000000000201")
NOW = datetime(2026, 8, 13, 12, 0, tzinfo=UTC)


def test_access_device_normalizes_and_round_trips() -> None:
    device = AccessDevice(
        id=ACCESS_DEVICE_ID,
        display_name="  Garage keypad  ",
        home_assistant_device_id="zha-device-id",
        access_point_id=ACCESS_POINT_ID,
        created_at=NOW,
        updated_at=NOW,
    )

    restored = AccessDevice.from_dict(device.to_dict())

    assert restored == device
    assert restored.display_name == "Garage keypad"
    assert restored.setup_state is AccessDeviceSetupState.PENDING_HARDWARE_TEST
    assert restored.button_actions["disarm"] is KeypadOperation.UNLOCK
    assert restored.button_actions["arm_all_zones"] is KeypadOperation.LOCK
    assert restored.button_actions["emergency"] is KeypadOperation.NONE


def test_access_device_rejects_incomplete_button_policy() -> None:
    device = AccessDevice(
        display_name="Garage keypad",
        home_assistant_device_id="zha-device-id",
        access_point_id=ACCESS_POINT_ID,
    )
    malformed = device.to_dict()
    del malformed["button_actions"]["emergency"]

    with pytest.raises(ValueError, match="record is invalid"):
        AccessDevice.from_dict(malformed)


def test_zigbee2mqtt_access_device_normalizes_and_round_trips() -> None:
    device = AccessDevice(
        id=ACCESS_DEVICE_ID,
        display_name="Garage keypad",
        home_assistant_device_id="mqtt-device-id",
        access_point_id=ACCESS_POINT_ID,
        integration=AccessDeviceIntegration.ZIGBEE2MQTT,
        zigbee_ieee_address="02:00:00:00:00:00:00:01",
        zigbee2mqtt_base_topic="/zigbee2mqtt/",
        zigbee2mqtt_friendly_name="garage/keypad",
        created_at=NOW,
        updated_at=NOW,
    )

    restored = AccessDevice.from_dict(device.to_dict())

    assert restored == device
    assert restored.zigbee_ieee_address == "0x0200000000000001"
    assert restored.zigbee2mqtt_state_topic == "zigbee2mqtt/garage/keypad"


def test_zigbee2mqtt_access_device_rejects_wildcard_topics() -> None:
    with pytest.raises(ValueError, match="friendly name is invalid"):
        AccessDevice(
            display_name="Garage keypad",
            home_assistant_device_id="mqtt-device-id",
            access_point_id=ACCESS_POINT_ID,
            integration=AccessDeviceIntegration.ZIGBEE2MQTT,
            zigbee_ieee_address="0200000000000001",
            zigbee2mqtt_base_topic="zigbee2mqtt",
            zigbee2mqtt_friendly_name="garage/#",
        )


def test_keypad_access_metadata_accepts_non_lock_door_controller() -> None:
    person_id = UUID("00000000-0000-4000-8000-000000000301")
    credential_id = VaultCredentialId(UUID("00000000-0000-4000-8000-000000000401"))
    metadata = AccessMetadata(
        person_id=person_id,
        access_point_id=ACCESS_POINT_ID,
        driver=AccessDriver.HOMEPASS_KEYPAD,
        lock_entity_id="cover.example_garage_door_1",
        slot=1,
        synchronization_status=SynchronizationStatus.SYNCHRONIZED,
        vault_credential_id=credential_id,
        created_at=NOW,
        updated_at=NOW,
    )

    assert AccessMetadata.from_dict(metadata.to_dict()) == metadata


def test_keypad_assignments_allocate_distinct_slots_for_multiple_people() -> None:
    """A second keypad user must not collide with the first user's logical slot."""
    first_person_id = UUID("00000000-0000-4000-8000-000000000301")
    second_person_id = UUID("00000000-0000-4000-8000-000000000302")
    other_access_point_id = UUID("00000000-0000-4000-8000-000000000102")

    existing = (
        AccessMetadata(
            person_id=first_person_id,
            access_point_id=ACCESS_POINT_ID,
            driver=AccessDriver.HOMEPASS_KEYPAD,
            lock_entity_id="cover.example_garage_door_1",
            slot=1,
            synchronization_status=SynchronizationStatus.SYNCHRONIZED,
            created_at=NOW,
            updated_at=NOW,
        ),
        AccessMetadata(
            person_id=second_person_id,
            access_point_id=other_access_point_id,
            driver=AccessDriver.HOMEPASS_KEYPAD,
            lock_entity_id="cover.example_garage_door_2",
            slot=2,
            synchronization_status=SynchronizationStatus.SYNCHRONIZED,
            created_at=NOW,
            updated_at=NOW,
        ),
    )

    assert _next_available_keypad_slot(existing, ACCESS_POINT_ID) == 2


@pytest.mark.asyncio
async def test_schema_17_migration_adds_empty_access_devices_collection() -> None:
    access_point = {
        "id": str(ACCESS_POINT_ID),
        "display_name": "Garage Door",
        "enabled": True,
        "created_at": NOW.isoformat(),
        "updated_at": NOW.isoformat(),
    }
    schema_17 = {
        "metadata": {"schema_version": 17},
        "data": {
            "people": {},
            "access_points": {str(ACCESS_POINT_ID): access_point},
            "access_metadata": {},
            "credential_metadata": {},
            "access_grants": {},
            "schedules": {str(PERMANENT_SCHEDULE_ID): permanent_schedule().to_dict()},
            "lifecycle_operations": {},
            "synchronization_statuses": {
                str(ACCESS_POINT_ID): AccessPointSynchronization(
                    ACCESS_POINT_ID,
                    SynchronizationStatus.UNKNOWN,
                    NOW,
                ).to_dict()
            },
            "synchronization_history": {},
            "activity_events": {},
            "properties": {},
            "settings": {
                "managed_access_points": {
                    str(ACCESS_POINT_ID): {
                        "discovery_key": None,
                        "managed": True,
                        "control_entity_id": "lock.garage_door",
                        "status_entity_id": None,
                        "control_profile": "lock",
                        "status_inverted": False,
                        "pulse_seconds": 1.0,
                        "pin_capable": True,
                        "nfc_capable": True,
                        "device_id": None,
                    }
                },
                "access_point_name_fallbacks": {},
            },
        },
    }

    migrated = await async_migrate_storage(schema_17)

    assert migrated["metadata"]["schema_version"] == 19
    assert migrated["data"]["access_devices"] == {}


@pytest.mark.asyncio
async def test_schema_18_migration_preserves_zha_access_device() -> None:
    device = AccessDevice(
        id=ACCESS_DEVICE_ID,
        display_name="Garage keypad",
        home_assistant_device_id="zha-device-id",
        access_point_id=ACCESS_POINT_ID,
        created_at=NOW,
        updated_at=NOW,
    ).to_dict()
    device.pop("zigbee_ieee_address")
    device.pop("zigbee2mqtt_base_topic")
    device.pop("zigbee2mqtt_friendly_name")
    schema_18 = {
        "metadata": {"schema_version": 18},
        "data": {
            "people": {},
            "access_points": {
                str(ACCESS_POINT_ID): {
                    "id": str(ACCESS_POINT_ID),
                    "display_name": "Garage Door",
                    "enabled": True,
                    "created_at": NOW.isoformat(),
                    "updated_at": NOW.isoformat(),
                }
            },
            "access_devices": {str(ACCESS_DEVICE_ID): device},
            "access_metadata": {},
            "credential_metadata": {},
            "access_grants": {},
            "schedules": {str(PERMANENT_SCHEDULE_ID): permanent_schedule().to_dict()},
            "lifecycle_operations": {},
            "synchronization_statuses": {},
            "synchronization_history": {},
            "activity_events": {},
            "properties": {},
            "settings": {
                "managed_access_points": {},
                "access_point_name_fallbacks": {},
            },
        },
    }

    migrated = await async_migrate_storage(schema_18)
    restored = AccessDevice.from_dict(migrated["data"]["access_devices"][str(ACCESS_DEVICE_ID)])

    assert migrated["metadata"]["schema_version"] == 19
    assert restored.integration is AccessDeviceIntegration.ZHA
    assert restored.zigbee_ieee_address is None
    assert restored.zigbee2mqtt_state_topic is None
