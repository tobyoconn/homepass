"""Application service for non-secret access synchronization metadata."""

from contextlib import suppress
from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID

from ..models import (
    AccessDriver,
    AccessGrant,
    AccessMetadata,
    SynchronizationHistoryEventType,
    SynchronizationStatus,
)
from ..repositories.access_grant import AccessGrantRepository
from ..repositories.access_metadata import AccessMetadataRepository
from ..repositories.credential_metadata import CredentialMetadataRepository
from ..vault import AccessMethod, CredentialMetadata, VaultCredentialId
from .synchronization_history import SynchronizationHistoryService
from .synchronization_status import SynchronizationStatusService
from .zwave_sync import VerificationStatus


class AccessMetadataService:
    """Record and query persisted access relationships."""

    def __init__(
        self,
        repository: AccessMetadataRepository,
        grant_repository: AccessGrantRepository,
        synchronization_status_service: SynchronizationStatusService | None = None,
        synchronization_history_service: SynchronizationHistoryService | None = None,
        credential_metadata_repository: CredentialMetadataRepository | None = None,
    ) -> None:
        """Initialize the service."""
        self._repository = repository
        self._grant_repository = grant_repository
        self._synchronization_status_service = synchronization_status_service
        self._synchronization_history_service = synchronization_history_service
        self._credential_metadata_repository = credential_metadata_repository

    async def record_provisioning(
        self,
        person_id: UUID,
        access_point_id: UUID,
        lock_entity_id: str,
        slot: int,
        verification_status: VerificationStatus,
        vault_credential_id: VaultCredentialId,
        driver: AccessDriver = AccessDriver.ZWAVE_JS,
        *,
        credential_revision: int = 1,
    ) -> AccessMetadata:
        """Persist the non-secret result of an accepted provisioning operation."""
        if verification_status not in {"verified", "inconclusive"}:
            raise ValueError("Only accepted provisioning results may create access metadata")
        now = datetime.now(UTC)
        synchronization_status = (
            SynchronizationStatus.SYNCHRONIZED
            if verification_status == "verified"
            else SynchronizationStatus.UNKNOWN
        )
        metadata = AccessMetadata(
            person_id=person_id,
            access_point_id=access_point_id,
            driver=driver,
            lock_entity_id=lock_entity_id,
            slot=slot,
            synchronization_status=synchronization_status,
            vault_credential_id=vault_credential_id,
            credential_revision=credential_revision,
            created_at=now,
            updated_at=now,
        )
        saved = await self._repository.upsert(metadata)
        try:
            await self._grant_repository.upsert_inheriting_person_schedule(
                AccessGrant(
                    person_id=person_id,
                    credential_id=vault_credential_id.value,
                    access_point_id=access_point_id,
                    created_at=saved.created_at,
                    updated_at=saved.updated_at,
                    synchronization_status=synchronization_status,
                )
            )
            if self._credential_metadata_repository is not None:
                # Publish authority before evaluating synchronized ownership so
                # the integrity check observes one complete relationship.
                await self._credential_metadata_repository.upsert(
                    CredentialMetadata(
                        credential_id=vault_credential_id,
                        person_id=person_id,
                        access_method=AccessMethod.PIN,
                        enabled=True,
                        created_at=saved.created_at,
                        updated_at=saved.updated_at,
                    )
                )
            await self._recompute(access_point_id)
            if self._synchronization_history_service is not None:
                await self._synchronization_history_service.record(
                    SynchronizationHistoryEventType.PROVISIONING_COMPLETED,
                    person_id,
                    access_point_id,
                )
                await self._synchronization_history_service.record(
                    (
                        SynchronizationHistoryEventType.VERIFICATION_SUCCEEDED
                        if verification_status == "verified"
                        else SynchronizationHistoryEventType.VERIFICATION_PENDING
                    ),
                    person_id,
                    access_point_id,
                )
        except Exception:
            await self._compensate_failed_provisioning(
                person_id, access_point_id, vault_credential_id
            )
            raise
        return saved

    async def release_orphaned_person_credential(
        self,
        person_id: UUID,
        credential_id: VaultCredentialId,
    ) -> bool:
        """Remove an exact Person credential authority only when no access refers to it."""
        metadata = await self._repository.list_for_person(person_id)
        grants = await self._grant_repository.list_for_person(person_id)
        if any(record.vault_credential_id == credential_id for record in metadata) or any(
            grant.credential_id == credential_id.value for grant in grants
        ):
            return False
        if self._credential_metadata_repository is None:
            return True
        credential = await self._credential_metadata_repository.get_for_person(person_id)
        if credential is None:
            return True
        if credential.credential_id != credential_id:
            return False
        await self._credential_metadata_repository.remove(person_id)
        return await self._credential_metadata_repository.get_for_person(person_id) is None

    async def list_for_person(self, person_id: UUID) -> tuple[AccessMetadata, ...]:
        """Return all persisted access relationships for one Person."""
        return await self._repository.list_for_person(person_id)

    async def list_all(self) -> tuple[AccessMetadata, ...]:
        """Return every persisted synchronization record."""
        return await self._repository.list_all()

    async def has_access(self, person_id: UUID, access_point_id: UUID) -> bool:
        """Return whether one active Person-to-Access-Point relationship exists."""
        return any(
            metadata.access_point_id == access_point_id
            for metadata in await self._repository.list_for_person(person_id)
        )

    async def remove_access(self, person_id: UUID, access_point_id: UUID) -> None:
        """Delete one owned relationship and its Access Grant."""
        await self._grant_repository.remove(person_id, access_point_id)
        await self._repository.remove(person_id, access_point_id)
        await self._record_synchronized(access_point_id)

    async def remove_grant(self, person_id: UUID, access_point_id: UUID) -> None:
        """Delete only the Access Grant for a verified physical removal."""
        await self._grant_repository.remove(person_id, access_point_id)
        await self._recompute(access_point_id)

    async def remove_synchronization_metadata(self, person_id: UUID, access_point_id: UUID) -> None:
        """Delete only synchronization metadata after grant cleanup."""
        await self._repository.remove(person_id, access_point_id)
        await self._record_synchronized(access_point_id)

    async def update_synchronization_status(
        self,
        metadata: AccessMetadata,
        status: SynchronizationStatus,
    ) -> AccessMetadata:
        """Persist one synchronization state consistently across relationship records."""
        now = datetime.now(UTC)
        updated = await self._repository.upsert(
            replace(metadata, synchronization_status=status, updated_at=now)
        )
        grants = await self._grant_repository.list_for_person(metadata.person_id)
        for grant in grants:
            if grant.access_point_id == metadata.access_point_id:
                await self._grant_repository.upsert(
                    replace(grant, synchronization_status=status, updated_at=now)
                )
                break
        await self._recompute(metadata.access_point_id)
        if (
            self._synchronization_history_service is not None
            and status is not metadata.synchronization_status
        ):
            event_type = {
                SynchronizationStatus.RETRY_REQUIRED: (
                    SynchronizationHistoryEventType.RETRY_REQUIRED
                ),
                SynchronizationStatus.MANUAL_ATTENTION_REQUIRED: (
                    SynchronizationHistoryEventType.MANUAL_ATTENTION_REQUIRED
                ),
                SynchronizationStatus.SYNCHRONIZED: (
                    SynchronizationHistoryEventType.SYNCHRONIZATION_RESTORED
                ),
            }.get(status)
            if event_type is not None:
                await self._synchronization_history_service.record(
                    event_type, metadata.person_id, metadata.access_point_id
                )
        return updated

    async def list_grants_for_person(self, person_id: UUID) -> tuple[AccessGrant, ...]:
        """Return persisted Access Grants for one Person."""
        return await self._grant_repository.list_for_person(person_id)

    async def _recompute(self, access_point_id: UUID) -> None:
        """Recompute only when the canonical status service is configured."""
        if self._synchronization_status_service is not None:
            await self._synchronization_status_service.recompute(access_point_id)

    async def _record_synchronized(self, access_point_id: UUID) -> None:
        """Record the verified empty desired/device state after confirmed removal."""
        if self._synchronization_status_service is not None:
            await self._synchronization_status_service.record_synchronized(access_point_id)

    async def _compensate_failed_provisioning(
        self,
        person_id: UUID,
        access_point_id: UUID,
        credential_id: VaultCredentialId,
    ) -> None:
        """Best-effort remove core references created by an incomplete provisioning write."""
        try:
            await self._grant_repository.remove(person_id, access_point_id)
        except Exception:  # noqa: BLE001 - preserve both records when compensation is unsafe
            return
        try:
            await self._repository.remove(person_id, access_point_id)
        except Exception:  # noqa: BLE001 - the surviving metadata protects its Vault secret
            return
        with suppress(Exception):
            await self.release_orphaned_person_credential(person_id, credential_id)
        with suppress(Exception):
            await self._recompute(access_point_id)
