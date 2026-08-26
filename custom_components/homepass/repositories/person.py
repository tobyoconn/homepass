"""Person repository for HomePASS."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import cast
from uuid import UUID

from ..exceptions import DuplicatePersonError, PersonNotFoundError, StorageError
from ..models import AccessGrant, AccessMetadata, Person
from ..storage import HomePassStorageData, HomePassStorageManager, StorageRecord
from .base import Repository


class PersonRepository(Repository[Person, UUID]):
    """Persist and retrieve immutable Person domain models."""

    def __init__(self, storage_manager: HomePassStorageManager) -> None:
        """Initialize the repository."""
        self._storage_manager = storage_manager
        self._lock = asyncio.Lock()

    async def get(self, entity_id: UUID) -> Person:
        """Return a person by UUID."""
        async with self._lock:
            _, people = await self._load_people()
            try:
                return people[entity_id]
            except KeyError as err:
                raise PersonNotFoundError(str(entity_id)) from err

    async def list_all(self) -> tuple[Person, ...]:
        """Return all people ordered by display name and UUID."""
        async with self._lock:
            _, people = await self._load_people()
            return tuple(
                sorted(
                    people.values(),
                    key=lambda person: (
                        person.display_name.casefold(),
                        str(person.person_id),
                    ),
                )
            )

    async def add(self, entity: Person) -> None:
        """Add a person when its UUID and display name are unique."""

        def mutate(storage: HomePassStorageData) -> None:
            people = self._deserialize_people(storage)
            self._ensure_unique(entity, people)
            storage["data"]["people"][str(entity.person_id)] = self._serialize(entity)

        await self._mutate(mutate)

    async def update(self, entity: Person) -> None:
        """Replace an existing person."""

        def mutate(storage: HomePassStorageData) -> None:
            people = self._deserialize_people(storage)
            if entity.person_id not in people:
                raise PersonNotFoundError(str(entity.person_id))
            self._ensure_unique(entity, people, exclude_id=entity.person_id)
            storage["data"]["people"][str(entity.person_id)] = self._serialize(entity)

        await self._mutate(mutate)

    async def remove(self, entity_id: UUID) -> None:
        """Remove a person and dependent local relationship records by UUID."""

        def mutate(storage: HomePassStorageData) -> None:
            self.remove_from_snapshot(storage, entity_id)

        await self._mutate(mutate)

    @classmethod
    def remove_from_snapshot(cls, storage: HomePassStorageData, entity_id: UUID) -> None:
        """Remove one Person cascade inside an existing shared transaction."""
        people = cls._deserialize_people(storage)
        if entity_id not in people:
            raise PersonNotFoundError(str(entity_id))
        grants = storage["data"]["access_grants"]
        for key, record in tuple(grants.items()):
            if AccessGrant.from_dict(record).person_id == entity_id:
                del grants[key]
        metadata_records = storage["data"]["access_metadata"]
        for key, record in tuple(metadata_records.items()):
            if AccessMetadata.from_dict(record).person_id == entity_id:
                del metadata_records[key]
        storage["data"].get("credential_metadata", {}).pop(str(entity_id), None)
        del storage["data"]["people"][str(entity_id)]

    async def exists(self, entity_id: UUID) -> bool:
        """Return whether a person exists for a UUID."""
        async with self._lock:
            _, people = await self._load_people()
            return entity_id in people

    async def _load_people(
        self,
    ) -> tuple[HomePassStorageData, dict[UUID, Person]]:
        """Load and deserialize the people collection."""
        try:
            storage = await self._storage_manager.async_load()
            return storage, self._deserialize_people(storage)
        except StorageError:
            raise
        except Exception as err:
            raise StorageError("Unable to load HomePASS people") from err

    async def _mutate(self, mutator: Callable[[HomePassStorageData], None]) -> None:
        """Run one repository mutation in the shared storage transaction."""
        try:
            async with self._lock:
                await self._storage_manager.async_transaction(mutator)
        except (DuplicatePersonError, PersonNotFoundError, StorageError):
            raise
        except Exception as err:
            raise StorageError("Unable to save HomePASS people") from err

    @staticmethod
    def _deserialize_people(storage: HomePassStorageData) -> dict[UUID, Person]:
        """Deserialize and validate Person records from one snapshot."""
        people: dict[UUID, Person] = {}
        for stored_id, record in storage["data"]["people"].items():
            person = Person.from_dict(record)
            if str(person.person_id) != stored_id:
                raise StorageError(f"Stored person identifier does not match record: {stored_id}")
            people[person.person_id] = person
        return people

    @staticmethod
    def _serialize(person: Person) -> StorageRecord:
        """Serialize a person for the storage collection."""
        return cast(StorageRecord, person.to_dict())

    @staticmethod
    def _ensure_unique(
        person: Person,
        people: dict[UUID, Person],
        *,
        exclude_id: UUID | None = None,
    ) -> None:
        """Ensure a person's UUID and normalized display name are unique."""
        if person.person_id in people and person.person_id != exclude_id:
            raise DuplicatePersonError(str(person.person_id))

        normalized_name = person.display_name.casefold()
        if any(
            existing.person_id != exclude_id and existing.display_name.casefold() == normalized_name
            for existing in people.values()
        ):
            raise DuplicatePersonError(person.display_name)
