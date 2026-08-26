"""Persistent HomePASS registry repository."""

from __future__ import annotations

import asyncio
from uuid import UUID

from homeassistant.core import HomeAssistant

from .exceptions import DuplicatePersonError
from .exceptions import PersonNotFoundError as DomainPersonNotFoundError
from .models import Person
from .repositories.person import PersonRepository
from .storage import HomePassStorageManager


class PersonAlreadyExistsError(ValueError):
    """Raised when a duplicate normalized person name is added."""


class PersonNotFoundError(KeyError):
    """Raised when a person does not exist."""


class HomePassRepository:
    """Versioned repository for non-secret HomePASS metadata."""

    def __init__(self, hass: HomeAssistant) -> None:
        self._repository = PersonRepository(HomePassStorageManager(hass))
        self._people: dict[UUID, Person] = {}
        self._lock = asyncio.Lock()

    async def async_load(self) -> None:
        """Load registry data."""
        self._people = {person.person_id: person for person in await self._repository.list_all()}

    async def async_create_person(self, *, name: str, notes: str | None = None) -> Person:
        """Create and persist a person."""
        async with self._lock:
            person = Person(display_name=name, notes=notes)
            try:
                await self._repository.add(person)
            except DuplicatePersonError as err:
                raise PersonAlreadyExistsError(name) from err
            self._people[person.person_id] = person
            return person

    async def async_delete_person(self, person_id: UUID) -> None:
        """Delete a person and persist the change."""
        async with self._lock:
            try:
                await self._repository.remove(person_id)
            except DomainPersonNotFoundError as err:
                raise PersonNotFoundError(str(person_id)) from err
            del self._people[person_id]

    def list_people(self) -> tuple[Person, ...]:
        """Return people sorted for deterministic UI and tests."""
        return tuple(
            sorted(
                self._people.values(),
                key=lambda person: person.display_name.casefold(),
            )
        )

    def get_person(self, person_id: UUID) -> Person:
        """Return one person."""
        try:
            return self._people[person_id]
        except KeyError as err:
            raise PersonNotFoundError(str(person_id)) from err
