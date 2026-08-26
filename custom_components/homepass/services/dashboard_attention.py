"""Presentation-ready synchronization attention for the HomePASS dashboard."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypedDict
from uuid import UUID

from ..models import (
    AccessPoint,
    AccessPointSynchronization,
    Person,
    SynchronizationStatus,
)
from ..storage import HomePassStorageData, HomePassStorageManager
from .synchronization_presentation import (
    SynchronizationPresentation,
    SynchronizationPresentationData,
    SynchronizationSeverity,
)
from .synchronization_status import SynchronizationStatusService

_ACTIONABLE_STATUSES = {
    SynchronizationStatus.RETRY_REQUIRED,
    SynchronizationStatus.MANUAL_ATTENTION_REQUIRED,
    SynchronizationStatus.UNKNOWN,
}
_SEVERITY_ORDER: dict[SynchronizationSeverity, int] = {
    "error": 0,
    "warning": 1,
    "info": 2,
    "success": 3,
}


class DashboardAttentionItemData(TypedDict):
    """Serialized actionable relationship with opaque navigation identifiers."""

    person_id: str
    access_point_id: str
    person_name: str
    door_name: str
    synchronization: SynchronizationPresentationData


class DashboardAttentionSummaryData(TypedDict):
    """Serialized dashboard synchronization-attention response."""

    items: list[DashboardAttentionItemData]


@dataclass(frozen=True, slots=True)
class DashboardAttentionItem:
    """One homeowner-actionable synchronization relationship."""

    person_id: UUID
    access_point_id: UUID
    person_name: str
    door_name: str
    synchronization: SynchronizationPresentation

    def to_dict(self) -> DashboardAttentionItemData:
        """Serialize friendly fields and opaque navigation identifiers."""
        return {
            "person_id": str(self.person_id),
            "access_point_id": str(self.access_point_id),
            "person_name": self.person_name,
            "door_name": self.door_name,
            "synchronization": self.synchronization.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class DashboardAttentionSummary:
    """Actionable synchronization items for the dashboard."""

    items: tuple[DashboardAttentionItem, ...]

    def to_dict(self) -> DashboardAttentionSummaryData:
        """Serialize the complete presentation-only aggregate."""
        return {"items": [item.to_dict() for item in self.items]}


class DashboardAttentionService:
    """Build synchronization attention from one isolated HomePASS snapshot."""

    def __init__(
        self,
        storage: HomePassStorageManager,
        synchronization_status_service: SynchronizationStatusService,
    ) -> None:
        """Initialize the shared snapshot and synchronization boundaries."""
        self._storage = storage
        self._synchronization_status_service = synchronization_status_service

    async def get_dashboard_attention(self) -> DashboardAttentionSummary:
        """Return only relationships whose synchronization needs homeowner attention."""
        snapshot = await self._storage.async_load()
        people = self._people(snapshot)
        access_points = self._access_points(snapshot)
        managed_ids = set(
            SynchronizationStatusService.managed_access_point_ids_from_snapshot(snapshot)
        )
        canonical_ids = SynchronizationStatusService.canonical_records_from_snapshot(
            snapshot
        ).keys()
        if not managed_ids <= access_points.keys() or not managed_ids <= canonical_ids:
            raise ValueError("Dashboard synchronization context is unavailable")

        relationships = self._synchronization_status_service.relationship_records_from_snapshot(
            snapshot
        )
        items: list[DashboardAttentionItem] = []
        for (person_id, access_point_id), record in relationships.items():
            if access_point_id not in managed_ids:
                continue
            person = people.get(person_id)
            access_point = access_points.get(access_point_id)
            if person is None or access_point is None:
                raise ValueError("Dashboard synchronization relationship is unavailable")
            if record.status not in _ACTIONABLE_STATUSES:
                continue
            items.append(
                DashboardAttentionItem(
                    person_id,
                    access_point_id,
                    person.display_name,
                    access_point.display_name,
                    self._relationship_presentation(snapshot, person_id, access_point_id, record),
                )
            )

        return DashboardAttentionSummary(
            tuple(
                sorted(
                    items,
                    key=lambda item: (
                        _SEVERITY_ORDER[item.synchronization.severity],
                        item.door_name.casefold(),
                        item.person_name.casefold(),
                        str(item.access_point_id),
                        str(item.person_id),
                    ),
                )
            )
        )

    @staticmethod
    def _relationship_presentation(
        snapshot: HomePassStorageData,
        person_id: UUID,
        access_point_id: UUID,
        record: AccessPointSynchronization,
    ) -> SynchronizationPresentation:
        """Reuse the shared relationship presentation without policy duplication."""
        return SynchronizationStatusService.relationship_presentation_from_snapshot(
            snapshot,
            (person_id, access_point_id),
            record,
        )

    @staticmethod
    def _people(snapshot: HomePassStorageData) -> dict[UUID, Person]:
        """Load and validate durable People from the supplied snapshot."""
        people: dict[UUID, Person] = {}
        for stored_id, raw_person in snapshot["data"]["people"].items():
            person = Person.from_dict(raw_person)
            if stored_id != str(person.person_id):
                raise ValueError("Stored Person identifier does not match its record")
            people[person.person_id] = person
        return people

    @staticmethod
    def _access_points(snapshot: HomePassStorageData) -> dict[UUID, AccessPoint]:
        """Load and validate durable Access Points from the supplied snapshot."""
        access_points: dict[UUID, AccessPoint] = {}
        for stored_id, raw_access_point in snapshot["data"]["access_points"].items():
            access_point = AccessPoint.from_dict(raw_access_point)
            if stored_id != str(access_point.id):
                raise ValueError("Stored Access Point identifier does not match its record")
            access_points[access_point.id] = access_point
        return access_points


__all__ = [
    "DashboardAttentionItem",
    "DashboardAttentionService",
    "DashboardAttentionSummary",
]
