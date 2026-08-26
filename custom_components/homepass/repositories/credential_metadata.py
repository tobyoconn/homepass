"""Repository for person-scoped non-secret credential metadata."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import replace
from typing import cast
from uuid import UUID

from ..exceptions import CredentialAuthorityConflictError, StorageError
from ..models import AccessGrant, AccessMetadata
from ..storage import HomePassStorageData, HomePassStorageManager, StorageRecord
from ..vault import CredentialMetadata, VaultCredentialId


class CredentialMetadataRepository:
    """Persist at most one current credential relationship per Person."""

    def __init__(self, storage_manager: HomePassStorageManager) -> None:
        self._storage_manager = storage_manager
        self._lock = asyncio.Lock()

    async def get_for_person(self, person_id: UUID) -> CredentialMetadata | None:
        """Return a Person's current credential relationship, if present."""
        try:
            async with self._lock:
                storage = await self._storage_manager.async_load()
                record = storage["data"]["credential_metadata"].get(str(person_id))
                return None if record is None else CredentialMetadata.from_dict(record)
        except StorageError:
            raise
        except Exception as err:
            raise StorageError("Unable to load HomePASS Credential Metadata") from err

    async def list_enabled(self) -> tuple[CredentialMetadata, ...]:
        """Return enabled credential relationships without exposing any secret."""
        try:
            async with self._lock:
                storage = await self._storage_manager.async_load()
                credentials = tuple(
                    CredentialMetadata.from_dict(record)
                    for record in storage["data"]["credential_metadata"].values()
                )
                return tuple(
                    sorted(
                        (item for item in credentials if item.enabled),
                        key=lambda item: str(item.person_id),
                    )
                )
        except StorageError:
            raise
        except Exception as err:
            raise StorageError("Unable to load HomePASS Credential Metadata") from err

    async def resolve_for_provisioning(self, person_id: UUID) -> CredentialMetadata | None:
        """Resolve one unambiguous Person authority from a single storage snapshot."""
        try:
            async with self._lock:
                storage = await self._storage_manager.async_load()
                return self._resolve_for_provisioning(storage, person_id)
        except CredentialAuthorityConflictError:
            raise
        except StorageError:
            raise
        except Exception as err:
            raise StorageError("Unable to resolve HomePASS credential authority") from err

    async def upsert(self, metadata: CredentialMetadata) -> CredentialMetadata:
        """Create or replace current metadata while preserving creation time."""

        def mutate(storage: HomePassStorageData) -> CredentialMetadata:
            records = storage["data"]["credential_metadata"]
            existing_record = records.get(str(metadata.person_id))
            next_metadata = metadata
            if existing_record is not None:
                existing = CredentialMetadata.from_dict(existing_record)
                if existing.credential_id != metadata.credential_id:
                    raise ValueError(
                        "Person credential authority requires the replacement workflow"
                    )
                next_metadata = replace(metadata, created_at=existing.created_at)
            if any(
                identifier != str(metadata.person_id)
                and CredentialMetadata.from_dict(record).credential_id == metadata.credential_id
                for identifier, record in records.items()
            ):
                raise ValueError("Credential is already assigned to another Person")
            records[str(metadata.person_id)] = cast("StorageRecord", next_metadata.to_dict())
            self._validate_authority_claim(storage, next_metadata)
            return next_metadata

        return await self._mutate(mutate)

    async def remove(self, person_id: UUID) -> None:
        """Remove one Person's relationship metadata, if present."""

        def mutate(storage: HomePassStorageData) -> None:
            storage["data"]["credential_metadata"].pop(str(person_id), None)

        await self._mutate(mutate)

    async def _mutate[ResultT](self, mutator: Callable[[HomePassStorageData], ResultT]) -> ResultT:
        try:
            async with self._lock:
                return await self._storage_manager.async_transaction(mutator)
        except CredentialAuthorityConflictError:
            raise
        except StorageError:
            raise
        except Exception as err:
            raise StorageError("Unable to save HomePASS Credential Metadata") from err

    @staticmethod
    def resolve_for_provisioning_from_snapshot(
        storage: HomePassStorageData,
        person_id: UUID,
    ) -> CredentialMetadata | None:
        """Resolve credential authority from a caller-owned consistent snapshot."""
        return CredentialMetadataRepository._resolve_for_provisioning(storage, person_id)

    @staticmethod
    def _resolve_for_provisioning(
        storage: HomePassStorageData,
        person_id: UUID,
    ) -> CredentialMetadata | None:
        """Resolve authority only when every relationship and owner agrees."""
        grants = {
            grant.access_point_id: grant
            for record in storage["data"].get("access_grants", {}).values()
            if (grant := AccessGrant.from_dict(record)).person_id == person_id
        }
        metadata = {
            item.access_point_id: item
            for record in storage["data"].get("access_metadata", {}).values()
            if (item := AccessMetadata.from_dict(record)).person_id == person_id
        }
        if set(grants) != set(metadata):
            raise CredentialAuthorityConflictError()
        referenced_ids: set[VaultCredentialId] = set()
        for access_point_id, grant in grants.items():
            synchronized = metadata[access_point_id]
            credential_id = synchronized.vault_credential_id
            if credential_id is None or grant.credential_id != credential_id.value:
                raise CredentialAuthorityConflictError()
            referenced_ids.add(credential_id)

        record = storage["data"]["credential_metadata"].get(str(person_id))
        if record is None:
            if grants or metadata:
                raise CredentialAuthorityConflictError()
            return None
        authority = CredentialMetadata.from_dict(record)
        if authority.person_id != person_id or (
            referenced_ids and referenced_ids != {authority.credential_id}
        ):
            raise CredentialAuthorityConflictError()
        CredentialMetadataRepository._validate_authority_claim(storage, authority)
        return authority

    @staticmethod
    def _validate_authority_claim(
        storage: HomePassStorageData,
        authority: CredentialMetadata,
    ) -> None:
        """Require one claim to agree with every persisted credential reference."""
        for record in storage["data"].get("access_grants", {}).values():
            grant = AccessGrant.from_dict(record)
            if grant.person_id == authority.person_id:
                if grant.credential_id != authority.credential_id.value:
                    raise CredentialAuthorityConflictError()
            elif grant.credential_id == authority.credential_id.value:
                raise CredentialAuthorityConflictError()
        for record in storage["data"].get("access_metadata", {}).values():
            metadata = AccessMetadata.from_dict(record)
            if metadata.vault_credential_id is None:
                if metadata.person_id == authority.person_id:
                    raise CredentialAuthorityConflictError()
                continue
            if metadata.person_id == authority.person_id:
                if metadata.vault_credential_id != authority.credential_id:
                    raise CredentialAuthorityConflictError()
            elif metadata.vault_credential_id == authority.credential_id:
                raise CredentialAuthorityConflictError()
        for identifier, record in storage["data"]["credential_metadata"].items():
            credential = CredentialMetadata.from_dict(record)
            if identifier != str(authority.person_id) and (
                credential.credential_id == authority.credential_id
            ):
                raise CredentialAuthorityConflictError()


__all__ = ["CredentialMetadataRepository"]
