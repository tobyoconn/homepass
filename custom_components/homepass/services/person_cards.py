"""One-snapshot User card presentation summaries."""

from __future__ import annotations

from typing import cast
from uuid import UUID

from ..models import Person
from ..storage import HomePassStorageManager


class PersonCardService:
    """Build PIN-safe User card data from one isolated storage snapshot."""

    def __init__(self, storage: HomePassStorageManager) -> None:
        self._storage = storage

    async def list_cards(self) -> tuple[dict[str, object], ...]:
        snapshot = await self._storage.async_load()
        people = sorted(
            (Person.from_dict(record) for record in snapshot["data"]["people"].values()),
            key=lambda person: (person.display_name.casefold(), str(person.person_id)),
        )
        access_counts: dict[str, int] = {}
        for record in snapshot["data"]["access_grants"].values():
            person_id = record.get("person_id")
            if isinstance(person_id, str):
                access_counts[person_id] = access_counts.get(person_id, 0) + 1
        credential_people = set(snapshot["data"]["credential_metadata"])
        cards: list[dict[str, object]] = []
        for person in people:
            card = cast(dict[str, object], dict(person.to_dict()))
            person_id = str(person.person_id)
            card["access_count"] = access_counts.get(person_id, 0)
            card["credential_stored"] = person_id in credential_people
            cards.append(card)
        return tuple(cards)

    async def credential_stored(self, person_id: UUID) -> bool:
        """Return only whether one Person has a current stored credential."""
        snapshot = await self._storage.async_load()
        return str(person_id) in snapshot["data"]["credential_metadata"]


__all__ = ["PersonCardService"]
