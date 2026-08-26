"""Fail-closed attribution for physical Activity credential evidence."""

from __future__ import annotations

from collections.abc import Mapping
from uuid import UUID

from ..exceptions import CredentialAuthorityConflictError
from ..models import (
    AccessDriver,
    AccessGrant,
    AccessMetadata,
    AccessPoint,
    Person,
    SynchronizationStatus,
)
from ..repositories.credential_metadata import CredentialMetadataRepository
from ..storage import HomePassStorageManager
from ..vault import AccessMethod


class ActivityKeypadAttributionService:
    """Resolve one reported lock slot to one unambiguous persisted Person."""

    def __init__(self, storage: HomePassStorageManager) -> None:
        self._storage = storage

    async def resolve_person(self, access_point_id: UUID, slot: int) -> Person | None:
        """Return the exact slot owner from one snapshot, or fail closed."""
        if not isinstance(access_point_id, UUID):
            raise TypeError("Activity Access Point identity must be a UUID")
        if isinstance(slot, bool) or not isinstance(slot, int) or slot < 1:
            raise ValueError("Activity credential slot must be a positive integer")

        snapshot = await self._storage.async_load()
        try:
            data = snapshot["data"]
            access_point = AccessPoint.from_dict(data["access_points"][str(access_point_id)])
            enrollments = data["settings"]["managed_access_points"]
            if not isinstance(enrollments, Mapping):
                return None
            enrollment = enrollments.get(str(access_point_id))
            if (
                access_point.id != access_point_id
                or not isinstance(enrollment, Mapping)
                or enrollment.get("managed") is not True
            ):
                return None

            all_metadata = tuple(
                AccessMetadata.from_dict(record) for record in data["access_metadata"].values()
            )
            matching_metadata = tuple(
                metadata
                for metadata in all_metadata
                if metadata.access_point_id == access_point_id
                and metadata.slot == slot
                and metadata.driver in {AccessDriver.ZWAVE_JS, AccessDriver.NUKI}
            )
            if len(matching_metadata) != 1:
                return None
            metadata = matching_metadata[0]
            if metadata.synchronization_status is not SynchronizationStatus.SYNCHRONIZED:
                return None

            stored_person = data["people"].get(str(metadata.person_id))
            if stored_person is None:
                return None
            person = Person.from_dict(stored_person)
            if person.person_id != metadata.person_id:
                return None

            all_grants = tuple(
                AccessGrant.from_dict(record) for record in data["access_grants"].values()
            )
            matching_grants = tuple(
                grant
                for grant in all_grants
                if grant.person_id == person.person_id and grant.access_point_id == access_point_id
            )
            if len(matching_grants) != 1 or metadata.vault_credential_id is None:
                return None
            grant = matching_grants[0]
            if (
                grant.synchronization_status is not SynchronizationStatus.SYNCHRONIZED
                or grant.credential_id != metadata.vault_credential_id.value
            ):
                return None

            credential = CredentialMetadataRepository.resolve_for_provisioning_from_snapshot(
                snapshot,
                person.person_id,
            )
            if (
                credential is None
                or credential.person_id != person.person_id
                or credential.access_method is not AccessMethod.PIN
                or credential.credential_id != metadata.vault_credential_id
            ):
                return None
        except (CredentialAuthorityConflictError, KeyError, TypeError, ValueError):
            return None
        return person


__all__ = ["ActivityKeypadAttributionService"]
