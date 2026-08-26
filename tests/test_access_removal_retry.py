"""Regression tests for safe recovery of an unconfirmed access removal."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from custom_components.homepass.models import (
    AccessDriver,
    AccessMetadata,
    SynchronizationStatus,
)
from custom_components.homepass.services.access_management import AccessManagementService
from custom_components.homepass.services.zwave_sync import (
    DriverCommandResult,
    DriverCommandStatus,
)
from custom_components.homepass.vault import VaultCredentialId


def _metadata() -> AccessMetadata:
    now = datetime.now(UTC)
    return AccessMetadata(
        person_id=uuid4(),
        access_point_id=uuid4(),
        driver=AccessDriver.ZWAVE_JS,
        lock_entity_id="lock.front_door",
        slot=7,
        synchronization_status=SynchronizationStatus.RETRY_REQUIRED,
        vault_credential_id=VaultCredentialId(uuid4()),
        created_at=now,
        updated_at=now,
    )


def _service(metadata: AccessMetadata) -> tuple[AccessManagementService, AsyncMock, AsyncMock]:
    driver = AsyncMock()
    metadata_service = AsyncMock()
    pending = AccessMetadata(
        person_id=metadata.person_id,
        access_point_id=metadata.access_point_id,
        driver=metadata.driver,
        lock_entity_id=metadata.lock_entity_id,
        slot=metadata.slot,
        synchronization_status=SynchronizationStatus.PENDING,
        vault_credential_id=metadata.vault_credential_id,
        created_at=metadata.created_at,
        updated_at=metadata.updated_at,
    )
    metadata_service.list_for_person.return_value = (metadata,)
    metadata_service.update_synchronization_status.return_value = pending
    vault = AsyncMock()
    vault.retrieve.return_value = "2468"
    service = AccessManagementService(
        AsyncMock(),
        AsyncMock(),
        driver,
        metadata_service,
        vault,
    )
    service._verify_removal = AsyncMock()  # type: ignore[method-assign]
    return service, driver, metadata_service


@pytest.mark.asyncio
async def test_retry_resends_clear_after_exact_ownership_confirmation() -> None:
    metadata = _metadata()
    service, driver, metadata_service = _service(metadata)
    driver.verify_pin_removed.return_value = False
    driver.verify_pin.return_value = "verified"
    driver.request_remove_pin.return_value = DriverCommandResult(DriverCommandStatus.ACCEPTED)

    await service.retry_removal_verification(
        metadata.person_id,
        metadata.access_point_id,
        expected_updated_at=metadata.updated_at,
    )

    driver.verify_pin.assert_awaited_once_with("lock.front_door", 7, "2468")
    driver.request_remove_pin.assert_awaited_once_with("lock.front_door", 7)
    metadata_service.update_synchronization_status.assert_awaited_once_with(
        metadata,
        SynchronizationStatus.PENDING,
    )
    service._verify_removal.assert_awaited_once()  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_retry_never_clears_a_slot_owned_by_a_different_credential() -> None:
    metadata = _metadata()
    service, driver, metadata_service = _service(metadata)
    driver.verify_pin_removed.return_value = False
    driver.verify_pin.return_value = "failed"

    with pytest.raises(ValueError, match="no longer contains"):
        await service.retry_removal_verification(
            metadata.person_id,
            metadata.access_point_id,
            expected_updated_at=metadata.updated_at,
        )

    driver.request_remove_pin.assert_not_awaited()
    metadata_service.update_synchronization_status.assert_awaited_once_with(
        metadata,
        SynchronizationStatus.MANUAL_ATTENTION_REQUIRED,
    )
    service._verify_removal.assert_not_awaited()  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_retry_stays_read_only_when_slot_ownership_is_inconclusive() -> None:
    metadata = _metadata()
    service, driver, metadata_service = _service(metadata)
    driver.verify_pin_removed.return_value = False
    driver.verify_pin.return_value = "inconclusive"

    await service.retry_removal_verification(
        metadata.person_id,
        metadata.access_point_id,
        expected_updated_at=metadata.updated_at,
    )

    driver.request_remove_pin.assert_not_awaited()
    metadata_service.update_synchronization_status.assert_awaited_once_with(
        metadata,
        SynchronizationStatus.PENDING,
    )
    service._verify_removal.assert_awaited_once()  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_verified_nuki_removal_forgets_fingerprint_attribution() -> None:
    """Physical Nuki deletion invalidates its linked fingerprint before local cleanup."""
    metadata = _metadata()
    metadata = AccessMetadata(
        person_id=metadata.person_id,
        access_point_id=metadata.access_point_id,
        driver=AccessDriver.NUKI,
        lock_entity_id=metadata.lock_entity_id,
        slot=metadata.slot,
        synchronization_status=SynchronizationStatus.PENDING,
        vault_credential_id=metadata.vault_credential_id,
        created_at=metadata.created_at,
        updated_at=metadata.updated_at,
    )
    metadata_service = AsyncMock()
    metadata_service.list_all.return_value = (metadata,)
    metadata_service.list_for_person.return_value = ()
    fingerprint_access_removed = AsyncMock()
    service = AccessManagementService(
        AsyncMock(),
        AsyncMock(),
        AsyncMock(),
        metadata_service,
        AsyncMock(),
        access_removed_observer=fingerprint_access_removed,
    )

    await service._finalize_verified_removal(uuid4(), metadata)  # noqa: SLF001

    fingerprint_access_removed.assert_awaited_once_with(
        metadata.person_id, metadata.access_point_id
    )
    metadata_service.remove_grant.assert_awaited_once_with(
        metadata.person_id, metadata.access_point_id
    )
    metadata_service.remove_synchronization_metadata.assert_awaited_once_with(
        metadata.person_id, metadata.access_point_id
    )
