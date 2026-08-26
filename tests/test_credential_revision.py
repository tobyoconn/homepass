"""Regression tests for PIN credential revision handling."""

from datetime import UTC, datetime
from typing import cast
from unittest.mock import AsyncMock
from uuid import uuid4

from custom_components.homepass.drivers import (
    CredentialReplacementRequest,
    CredentialReplacementRequestResult,
    CredentialReplacementRequestStatus,
    CredentialReplacementVerificationResult,
    CredentialReplacementVerificationStatus,
)
from custom_components.homepass.models import (
    AccessDriver,
    AccessGrant,
    AccessMetadata,
    LifecycleOperation,
    LifecyclePayloadValue,
    Person,
    SynchronizationStatus,
)
from custom_components.homepass.services.access_metadata import AccessMetadataService
from custom_components.homepass.services.credential_replacement import (
    CredentialReplacementLifecycleService,
)
from custom_components.homepass.storage import HomePassStorageData
from custom_components.homepass.vault import CredentialMetadata, VaultCredentialId


class _ExactReadbackDriver:
    """Minimal driver that confirms the current Nuki PIN without changing it."""

    def __init__(self) -> None:
        self.requests: list[CredentialReplacementRequest] = []

    def supports_exact_pin_readback(self, _target_device: str) -> bool:
        return True

    def supports_pin_replacement(self, _target_device: str) -> bool:
        return True

    async def async_request_credential_replacement(
        self,
        request: CredentialReplacementRequest,
    ) -> CredentialReplacementRequestResult:
        self.requests.append(request)
        return CredentialReplacementRequestResult(CredentialReplacementRequestStatus.ACCEPTED)

    async def async_verify_credential_replacement(
        self,
        request: CredentialReplacementRequest,
    ) -> CredentialReplacementVerificationResult:
        self.requests.append(request)
        return CredentialReplacementVerificationResult(
            CredentialReplacementVerificationStatus.REPLACEMENT_CONFIRMED
        )


async def test_record_provisioning_persists_current_vault_revision() -> None:
    """New access metadata must not reset an already-replaced PIN to revision one."""
    repository = AsyncMock()
    repository.upsert.side_effect = lambda metadata: metadata
    grant_repository = AsyncMock()
    credential_repository = AsyncMock()
    service = AccessMetadataService(
        repository,
        grant_repository,
        credential_metadata_repository=credential_repository,
    )

    saved = await service.record_provisioning(
        uuid4(),
        uuid4(),
        "lock.front_door",
        4,
        "verified",
        VaultCredentialId.new(),
        AccessDriver.NUKI,
        credential_revision=3,
    )

    assert saved.credential_revision == 3
    assert repository.upsert.await_args.args[0].credential_revision == 3


async def test_candidate_validation_does_not_require_access_revision_match() -> None:
    """Typing a replacement PIN compares only with the authoritative Vault PIN."""
    person = Person("Test")
    credential_id = VaultCredentialId.new()
    authority = CredentialMetadata(credential_id=credential_id, person_id=person.person_id)
    storage = AsyncMock()
    storage.async_load.return_value = {
        "data": {
            "people": {str(person.person_id): person.to_dict()},
            "credential_metadata": {str(person.person_id): authority.to_dict()},
        }
    }
    vault = AsyncMock()
    vault.retrieve.return_value = "345678"
    service = CredentialReplacementLifecycleService(
        storage,
        AsyncMock(),
        vault,
        lambda _driver: None,
    )

    assert await service.validate_pin_candidate(person.person_id, "456789") is True
    assert await service.validate_pin_candidate(person.person_id, "345678") is False


async def test_replacement_accepts_verified_legacy_revision_mismatch() -> None:
    """A read-back-confirmed PIN can repair metadata created with revision one."""
    now = datetime.now(UTC)
    person = Person("Test", created_at=now, updated_at=now)
    access_point_id = uuid4()
    credential_id = VaultCredentialId.new()
    grant = AccessGrant(
        person_id=person.person_id,
        credential_id=credential_id.value,
        access_point_id=access_point_id,
        synchronization_status=SynchronizationStatus.SYNCHRONIZED,
        created_at=now,
        updated_at=now,
    )
    metadata = AccessMetadata(
        person_id=person.person_id,
        access_point_id=access_point_id,
        driver=AccessDriver.NUKI,
        lock_entity_id="lock.front_door",
        slot=8193,
        synchronization_status=SynchronizationStatus.SYNCHRONIZED,
        vault_credential_id=credential_id,
        credential_revision=1,
        created_at=now,
        updated_at=now,
    )
    authority = CredentialMetadata(
        credential_id=credential_id,
        person_id=person.person_id,
        created_at=now,
        updated_at=now,
    )
    key = f"{person.person_id}:{access_point_id}"
    snapshot = cast(
        HomePassStorageData,
        {
            "data": {
                "people": {str(person.person_id): person.to_dict()},
                "access_grants": {key: grant.to_dict()},
                "access_metadata": {key: metadata.to_dict()},
                "credential_metadata": {str(person.person_id): authority.to_dict()},
            }
        },
    )
    storage = AsyncMock()
    storage.async_load.return_value = snapshot
    vault = AsyncMock()
    vault.revision.return_value = 2
    vault.retrieve.return_value = "345678"
    driver = _ExactReadbackDriver()
    service = CredentialReplacementLifecycleService(
        storage,
        AsyncMock(),
        vault,
        lambda selected: driver if selected is AccessDriver.NUKI else None,
    )

    context = await service._capture_context(person.person_id)
    targets = cast(list[LifecyclePayloadValue], context["targets"])
    target = cast(dict[str, LifecyclePayloadValue], targets[0])
    assert target["expected_credential_revision"] == 1
    assert context["expected_vault_revision"] == 2
    assert len(driver.requests) == 1

    operation = LifecycleOperation(
        operation_type=service.OPERATION_TYPE,
        payload=context,
    )
    service._validate_snapshot(snapshot, operation)
