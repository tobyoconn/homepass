"""Generic repository contract for HomePASS."""

from abc import ABC, abstractmethod


class Repository[EntityT, IdT](ABC):
    """Define asynchronous persistence operations for a domain entity."""

    @abstractmethod
    async def get(self, entity_id: IdT) -> EntityT:
        """Return the entity identified by ``entity_id``.

        Concrete repositories raise the appropriate HomePASS domain exception when the
        entity does not exist.
        """
        raise NotImplementedError

    @abstractmethod
    async def list_all(self) -> tuple[EntityT, ...]:
        """Return all entities in a deterministic order."""
        raise NotImplementedError

    @abstractmethod
    async def add(self, entity: EntityT) -> None:
        """Add a new entity.

        Concrete repositories raise the appropriate HomePASS domain exception when the
        entity conflicts with existing domain data.
        """
        raise NotImplementedError

    @abstractmethod
    async def update(self, entity: EntityT) -> None:
        """Replace the persisted state of an existing entity."""
        raise NotImplementedError

    @abstractmethod
    async def remove(self, entity_id: IdT) -> None:
        """Remove the entity identified by ``entity_id``."""
        raise NotImplementedError

    @abstractmethod
    async def exists(self, entity_id: IdT) -> bool:
        """Return whether an entity exists for ``entity_id``."""
        raise NotImplementedError
