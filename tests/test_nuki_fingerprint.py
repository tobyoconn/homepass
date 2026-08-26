"""Nuki fingerprint guidance, persistence, and audit attribution tests."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, cast

import pytest

from custom_components.homepass.models import (
    AccessDriver,
    AccessGrant,
    AccessMetadata,
    AccessPoint,
    ActivityAccessMethod,
    Person,
    SynchronizationStatus,
)
from custom_components.homepass.providers import ProviderAuditEvent
from custom_components.homepass.repositories import (
    AccessPointEnrollmentRepository,
    ActivityRepository,
    CredentialMetadataRepository,
)
from custom_components.homepass.repositories.person import PersonRepository
from custom_components.homepass.services import (
    AccessPointEnrollment,
    ActivityFilterEvent,
    ActivityKeypadAttributionService,
    ActivityPublisher,
    ActivityService,
    NukiFingerprintService,
    present_activity,
)
from custom_components.homepass.services.activity import activity_filter_event_for
from custom_components.homepass.storage import HomePassStorageData, HomePassStorageManager
from custom_components.homepass.vault import CredentialMetadata, VaultCredentialId

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


async def _build_service(
    hass: HomeAssistant,
) -> tuple[
    NukiFingerprintService,
    HomePassStorageManager,
    ActivityRepository,
    Person,
    AccessPoint,
]:
    storage = HomePassStorageManager(hass)
    person = Person(display_name="Alex")
    door = AccessPoint(display_name="Front Door")
    credential_id = VaultCredentialId.new()
    await PersonRepository(storage).add(person)
    await AccessPointEnrollmentRepository(storage).upsert(
        AccessPointEnrollment(
            access_point_id=door.id,
            discovery_key="home_assistant:lock.front_door",
            control_entity_id="lock.front_door",
            pin_capable=True,
            nfc_capable=True,
            device_id="nuki-matter-device",
        ),
        door,
    )
    await CredentialMetadataRepository(storage).upsert(
        CredentialMetadata(credential_id=credential_id, person_id=person.person_id)
    )
    grant = AccessGrant(
        person_id=person.person_id,
        credential_id=credential_id.value,
        access_point_id=door.id,
        synchronization_status=SynchronizationStatus.SYNCHRONIZED,
    )
    metadata = AccessMetadata(
        person_id=person.person_id,
        access_point_id=door.id,
        driver=AccessDriver.NUKI,
        lock_entity_id="lock.front_door",
        slot=17,
        synchronization_status=SynchronizationStatus.SYNCHRONIZED,
        vault_credential_id=credential_id,
    )

    def link(snapshot: HomePassStorageData) -> None:
        key = f"{person.person_id}:{door.id}"
        snapshot["data"]["access_grants"][key] = cast("dict[str, object]", grant.to_dict())
        snapshot["data"]["access_metadata"][key] = cast("dict[str, object]", metadata.to_dict())

    await storage.async_transaction(link)
    activity_repository = ActivityRepository(storage)
    activity_service = ActivityService(activity_repository, ActivityPublisher())
    attribution = ActivityKeypadAttributionService(storage)
    return (
        NukiFingerprintService(storage, activity_service, attribution),
        storage,
        activity_repository,
        person,
        door,
    )


async def test_guided_enrollment_stores_relationship_but_no_biometric_data(
    hass: HomeAssistant,
) -> None:
    """The Nuki app owns the scan while HomePASS persists only attribution state."""
    service, storage, _activity, person, door = await _build_service(hass)

    initial = await service.status_for_person(person.person_id)
    started = await service.start(person.person_id, door.id)
    completed = await service.mark_nuki_app_complete(person.person_id, door.id)

    assert initial["doors"][0]["status"] == "not_started"
    assert started["doors"][0]["status"] == "awaiting_nuki_app"
    assert completed["doors"][0]["status"] == "enrolled_unverified"
    assert completed["fingerprint_data_stored"] is False
    snapshot = await storage.async_load()
    stored = snapshot["data"]["settings"]["nuki_fingerprint_enrollments"]
    serialized = repr(stored).casefold()
    assert "authorization_external_id" in serialized
    assert "17" in serialized
    assert "template" not in serialized
    assert "biometric" not in serialized
    assert "fingerprint_data" not in serialized


async def test_storage_summary_is_explicitly_not_a_complete_lock_inventory(
    hass: HomeAssistant,
) -> None:
    """Status reports known links while remaining honest about unknown fingerprints."""
    service, _storage, _activity, person, door = await _build_service(hass)
    await service.start(person.person_id, door.id)

    result = await service.storage_summary("lock.front_door")

    assert result["linked_count"] == 1
    assert result["complete_lock_inventory_available"] is False
    assert result["entries"] == [
        {
            "person_name": "Alex",
            "door_name": "Front Door",
            "nuki_id": "17",
            "status": "awaiting_nuki_app",
        }
    ]


async def test_matching_fingerprint_event_confirms_owner_and_records_activity(
    hass: HomeAssistant,
) -> None:
    """A matching Nuki auth ID is sufficient evidence for named fingerprint Activity."""
    service, _storage, activity_repository, person, door = await _build_service(hass)
    await service.start(person.person_id, door.id)
    await service.mark_nuki_app_complete(person.person_id, door.id)
    event = ProviderAuditEvent(
        external_id="log-41",
        occurred_at=datetime.now(UTC) + timedelta(seconds=1),
        action="unlock",
        outcome="success",
        authorization_external_id="17",
        authorization_name="Display names are not trusted",
        source="fingerprint",
    )

    assert await service.observe_provider_event(door.id, event) is True
    status = await service.status_for_person(person.person_id)
    assert status["doors"][0]["status"] == "confirmed"
    activities = await activity_repository.list_events()
    assert len(activities) == 1
    assert activities[0].person_id == person.person_id
    assert activities[0].actor_id == person.person_id
    assert activities[0].access_method is ActivityAccessMethod.FINGERPRINT
    assert present_activity(activities[0]).title == ("Alex unlocked Front Door with a fingerprint.")
    assert activity_filter_event_for(activities[0]) is ActivityFilterEvent.FINGERPRINT_UNLOCK

    assert await service.observe_provider_event(door.id, event) is True
    assert len(await activity_repository.list_events()) == 1


async def test_nonmatching_or_nonfingerprint_events_fail_closed(
    hass: HomeAssistant,
) -> None:
    """Names and near-matching events never substitute for the persisted auth ID."""
    service, _storage, activity_repository, person, door = await _build_service(hass)
    await service.start(person.person_id, door.id)
    for event in (
        ProviderAuditEvent(
            "log-wrong",
            datetime.now(UTC),
            "unlock",
            "success",
            "18",
            person.display_name,
            "fingerprint",
        ),
        ProviderAuditEvent(
            "log-pin",
            datetime.now(UTC),
            "unlock",
            "success",
            "17",
            person.display_name,
            "keypad",
        ),
        ProviderAuditEvent(
            "log-failed",
            datetime.now(UTC),
            "unlock",
            "failed",
            "17",
            person.display_name,
            "fingerprint",
        ),
    ):
        assert await service.observe_provider_event(door.id, event) is False
    assert await activity_repository.list_events() == ()
    status = await service.status_for_person(person.person_id)
    assert status["doors"][0]["status"] == "awaiting_nuki_app"


async def test_unsynchronized_nuki_relationship_is_not_eligible(
    hass: HomeAssistant,
) -> None:
    """Fingerprint setup is hidden when the PIN relationship is not confirmed."""
    service, storage, _activity, person, door = await _build_service(hass)

    def make_pending(snapshot: HomePassStorageData) -> None:
        key = f"{person.person_id}:{door.id}"
        metadata = AccessMetadata.from_dict(snapshot["data"]["access_metadata"][key])
        snapshot["data"]["access_metadata"][key] = cast(
            "dict[str, object]",
            replace(
                metadata,
                synchronization_status=SynchronizationStatus.PENDING,
                updated_at=datetime.now(UTC),
            ).to_dict(),
        )

    await storage.async_transaction(make_pending)

    status = await service.status_for_person(person.person_id)
    assert status["doors"] == []


async def test_removing_nuki_access_forgets_the_fingerprint_link(
    hass: HomeAssistant,
) -> None:
    """A deleted keypad authorization cannot retain fingerprint attribution."""
    service, storage, _activity, person, door = await _build_service(hass)
    await service.start(person.person_id, door.id)

    await service.remove_access_link(person.person_id, door.id)

    snapshot = await storage.async_load()
    records = snapshot["data"]["settings"]["nuki_fingerprint_enrollments"]
    assert f"{person.person_id}:{door.id}" not in records
    status = await service.status_for_person(person.person_id)
    assert status["doors"][0]["status"] == "not_started"


async def test_recreated_nuki_authorization_does_not_inherit_stale_fingerprint_status(
    hass: HomeAssistant,
) -> None:
    """Upgrades self-heal links left behind by an older access removal."""
    service, storage, _activity, person, door = await _build_service(hass)
    await service.start(person.person_id, door.id)
    await service.mark_nuki_app_complete(person.person_id, door.id)

    def replace_authorization(snapshot: HomePassStorageData) -> None:
        key = f"{person.person_id}:{door.id}"
        metadata = AccessMetadata.from_dict(snapshot["data"]["access_metadata"][key])
        now = datetime.now(UTC)
        snapshot["data"]["access_metadata"][key] = cast(
            "dict[str, object]",
            replace(metadata, created_at=now, updated_at=now).to_dict(),
        )

    await storage.async_transaction(replace_authorization)

    status = await service.status_for_person(person.person_id)
    assert status["doors"][0]["status"] == "not_started"
    assert (await service.storage_summary("lock.front_door"))["linked_count"] == 0

    with pytest.raises(ValueError, match="Start fingerprint setup"):
        await service.mark_nuki_app_complete(person.person_id, door.id)

    started = await service.start(person.person_id, door.id)
    assert started["doors"][0]["status"] == "awaiting_nuki_app"
    snapshot = await storage.async_load()
    stored = snapshot["data"]["settings"]["nuki_fingerprint_enrollments"]
    assert stored[f"{person.person_id}:{door.id}"]["authorization_external_id"] == "17"
