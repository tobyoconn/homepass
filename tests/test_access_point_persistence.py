"""Door behaviour remains readable across real repository writes and reloads."""

from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from custom_components.homepass.access_point_state import HomeAssistantAccessPointStateResolver
from custom_components.homepass.exceptions import StorageError
from custom_components.homepass.models import AccessPoint
from custom_components.homepass.repositories.access_point import AccessPointRepository
from custom_components.homepass.repositories.access_point_enrollment import (
    AccessPointEnrollmentRepository,
)
from custom_components.homepass.services.access_point import (
    AccessPointEnrollment,
    AccessPointService,
    AccessPointTarget,
)
from custom_components.homepass.storage import HomePassStorageManager


@pytest.mark.parametrize("manual", [False, True])
@pytest.mark.parametrize("enabled,entry", [(False, "unlock"), (True, "unlock"), (True, "open")])
async def test_legacy_door_behaviour_save_list_and_reload(hass, manual, enabled, entry):
    """A settings save must not hide a previously enrolled door or lose its binding."""
    door = AccessPoint(display_name="Example Door")
    target = AccessPointTarget(door, "lock.example", discovery_key="example-lock")
    enrollment = AccessPointEnrollment(
        door.id,
        target.discovery_key,
        control_entity_id="lock.example" if manual else None,
        status_entity_id="binary_sensor.example_door" if manual else None,
        nfc_capable=True,
    )
    hass.states.async_set("lock.example", "locked", {"supported_features": 1})
    storage = HomePassStorageManager(hass)
    enrollments = AccessPointEnrollmentRepository(storage)
    await enrollments.upsert(enrollment, door)

    def seed_legacy_record(snapshot):
        record = snapshot["data"]["access_points"][str(door.id)]
        record.pop("open_enabled")
        record.pop("entry_action")

    await storage.async_transaction(seed_legacy_record)

    def service_for(manager):
        return AccessPointService(
            targets=(target,),
            target_discovery=SimpleNamespace(discover_targets=AsyncMock(return_value=(target,))),
            enrollment_store=AccessPointEnrollmentRepository(manager),
            policy_store=AccessPointRepository(manager),
            state_resolver=HomeAssistantAccessPointStateResolver(hass),
        )

    service = service_for(storage)
    assert (await service.list_access_point_summaries())[0].access_point == door
    saved = await service.update_open_policy(door.id, open_enabled=enabled, entry_action=entry)

    for manager in (storage, HomePassStorageManager(hass)):
        reloaded_service = service_for(manager)
        summaries = await reloaded_service.list_access_point_summaries()
        assert len(summaries) == 1
        assert summaries[0].access_point == saved.access_point
        assert summaries[0].access_point.id == door.id
        assert summaries[0].access_point.created_at == door.created_at
        assert summaries[0].access_point.display_name == door.display_name
        assert summaries[0].access_point.open_enabled is enabled
        assert summaries[0].access_point.entry_action == entry
        assert await AccessPointEnrollmentRepository(manager).list_all() == (enrollment,)
        assert (await reloaded_service.get_target(door.id)).lock_entity_id == "lock.example"

    # Existing affected records must also support another policy update after recovery.
    restored_service = service_for(HomePassStorageManager(hass))
    await restored_service.update_open_policy(door.id, open_enabled=False, entry_action="unlock")
    assert (await restored_service.list_access_points())[0].open_enabled is False


@pytest.mark.parametrize("enabled,entry", [(False, "unlock"), (True, "unlock"), (True, "open")])
async def test_newly_enrolled_door_is_readable_after_restart(hass, enabled, entry):
    """Onboarding writes the same policy shape as settings and must survive a reload."""
    door = AccessPoint(display_name="Example Door")
    target = AccessPointTarget(door, "lock.example", discovery_key="example-lock")
    hass.states.async_set("lock.example", "locked", {"supported_features": 1})
    storage = HomePassStorageManager(hass)
    service = AccessPointService(
        targets=(target,),
        target_discovery=SimpleNamespace(discover_targets=AsyncMock(return_value=(target,))),
        enrollment_store=AccessPointEnrollmentRepository(storage),
        policy_store=AccessPointRepository(storage),
        state_resolver=HomeAssistantAccessPointStateResolver(hass),
    )
    await service.enroll_access_point(door.id, open_enabled=enabled, entry_action=entry)

    repository = AccessPointRepository(HomePassStorageManager(hass))
    expected = replace(door, open_enabled=enabled, entry_action=entry)
    assert await repository.get(door.id) == expected
    assert await repository.list_all() == (expected,)
    assert (await service.list_access_point_summaries())[0].access_point == expected


@pytest.mark.parametrize(
    "change",
    [
        {"unexpected": True},
        {"open_enabled": "true"},
        {"entry_action": "invalid"},
        {"open_enabled": False, "entry_action": "open"},
    ],
)
def test_repository_still_rejects_invalid_policy_records(change):
    door = AccessPoint(display_name="Example Door", open_enabled=True, entry_action="open")
    with pytest.raises(StorageError, match="invalid"):
        AccessPointRepository._deserialize(str(door.id), {**door.to_dict(), **change})


@pytest.mark.parametrize("missing", ["open_enabled", "entry_action", "display_name"])
def test_repository_rejects_incomplete_policy_records(missing):
    door = AccessPoint(display_name="Example Door", open_enabled=True, entry_action="open")
    record = door.to_dict()
    record.pop(missing)
    with pytest.raises(StorageError, match="invalid"):
        AccessPointRepository._deserialize(str(door.id), record)
