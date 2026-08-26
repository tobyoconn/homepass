"""Application service for presentation-ready Door Details access policy."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import NotRequired, TypedDict
from uuid import UUID

from ..models import AccessPoint, AuthorizationDecision
from .authorization import AuthorizationService
from .authorization_presentation import (
    AuthorizationPolicySeverity,
    authorization_explanation,
    authorization_severity,
)
from .synchronization_history import (
    SynchronizationHistoryPresentation,
    SynchronizationHistoryPresentationData,
    SynchronizationHistoryService,
)
from .synchronization_presentation import (
    SynchronizationPresentation,
    SynchronizationPresentationData,
)
from .synchronization_status import SynchronizationStatusService


class DoorAccessPersonData(TypedDict):
    """Serialized allowed Person row."""

    person_id: str
    display_name: str
    synchronization: NotRequired[SynchronizationPresentationData]


class DoorDeniedPersonData(DoorAccessPersonData):
    """Serialized No Access Person row with a homeowner-facing explanation."""

    explanation: str


class DoorTemporarilyUnavailablePersonData(DoorDeniedPersonData):
    """Serialized temporary denial with a presentation-only severity."""

    severity: AuthorizationPolicySeverity


class DoorAccessDetailsData(TypedDict):
    """Serialized Door Details policy response."""

    current_access: list[DoorAccessPersonData]
    temporarily_unavailable: list[DoorTemporarilyUnavailablePersonData]
    no_access: list[DoorDeniedPersonData]
    synchronization_history: list[SynchronizationHistoryPresentationData]


@dataclass(frozen=True, slots=True)
class DoorAccessPerson:
    """One Person currently authorized for a Door."""

    person_id: UUID
    display_name: str
    synchronization: SynchronizationPresentation | None = None

    def to_dict(self) -> DoorAccessPersonData:
        """Serialize the safe presentation row."""
        data: DoorAccessPersonData = {
            "person_id": str(self.person_id),
            "display_name": self.display_name,
        }
        if self.synchronization is not None:
            data["synchronization"] = self.synchronization.to_dict()
        return data


@dataclass(frozen=True, slots=True)
class DoorDeniedPerson:
    """One Person without an Access Grant for this Door."""

    person_id: UUID
    display_name: str
    explanation: str

    def to_dict(self) -> DoorDeniedPersonData:
        """Serialize the safe presentation row."""
        return {
            "person_id": str(self.person_id),
            "display_name": self.display_name,
            "explanation": self.explanation,
        }


@dataclass(frozen=True, slots=True)
class DoorTemporarilyUnavailablePerson:
    """One temporarily denied Person with friendly presentation metadata."""

    person_id: UUID
    display_name: str
    explanation: str
    severity: AuthorizationPolicySeverity
    synchronization: SynchronizationPresentation | None = None

    def to_dict(self) -> DoorTemporarilyUnavailablePersonData:
        """Serialize the safe temporary-denial row."""
        data: DoorTemporarilyUnavailablePersonData = {
            "person_id": str(self.person_id),
            "display_name": self.display_name,
            "explanation": self.explanation,
            "severity": self.severity,
        }
        if self.synchronization is not None:
            data["synchronization"] = self.synchronization.to_dict()
        return data


@dataclass(frozen=True, slots=True)
class DoorAccessDetails:
    """Door policy grouped for direct presentation."""

    current_access: tuple[DoorAccessPerson, ...]
    temporarily_unavailable: tuple[DoorTemporarilyUnavailablePerson, ...]
    no_access: tuple[DoorDeniedPerson, ...]
    synchronization_history: tuple[SynchronizationHistoryPresentation, ...] = ()

    def to_dict(self) -> DoorAccessDetailsData:
        """Serialize all three presentation groups."""
        return {
            "current_access": [person.to_dict() for person in self.current_access],
            "temporarily_unavailable": [
                person.to_dict() for person in self.temporarily_unavailable
            ],
            "no_access": [person.to_dict() for person in self.no_access],
            "synchronization_history": [event.to_dict() for event in self.synchronization_history],
        }


class DoorDetailsService:
    """Build a single-snapshot, presentation-ready policy view for one Door."""

    def __init__(
        self,
        authorization_service: AuthorizationService,
        synchronization_status_service: SynchronizationStatusService | None = None,
        synchronization_history_service: SynchronizationHistoryService | None = None,
    ) -> None:
        """Initialize with the existing authorization application boundary."""
        self._authorization_service = authorization_service
        self._synchronization_status_service = synchronization_status_service
        self._synchronization_history_service = synchronization_history_service

    async def get_door_details(
        self,
        *,
        access_point: AccessPoint,
        instant_utc: datetime,
    ) -> DoorAccessDetails:
        """Group every Person's decision for one Door and evaluation instant."""
        results = await self._authorization_service.authorize_people_for_access_point(
            access_point=access_point,
            instant_utc=instant_utc,
        )
        presentations = (
            await self._synchronization_status_service.relationship_presentations()
            if self._synchronization_status_service is not None
            else {}
        )
        ordered = sorted(
            results,
            key=lambda item: (item.person.display_name.casefold(), str(item.person.person_id)),
        )
        current_access: list[DoorAccessPerson] = []
        temporarily_unavailable: list[DoorTemporarilyUnavailablePerson] = []
        no_access: list[DoorDeniedPerson] = []
        for result in ordered:
            if result.decision is AuthorizationDecision.ALLOWED:
                current_access.append(
                    DoorAccessPerson(
                        result.person.person_id,
                        result.person.display_name,
                        presentations.get((result.person.person_id, access_point.id)),
                    )
                )
                continue
            if result.decision is AuthorizationDecision.NO_GRANT:
                no_access.append(
                    DoorDeniedPerson(
                        result.person.person_id,
                        result.person.display_name,
                        authorization_explanation(result.decision),
                    )
                )
                continue
            temporarily_unavailable.append(
                DoorTemporarilyUnavailablePerson(
                    result.person.person_id,
                    result.person.display_name,
                    authorization_explanation(result.decision),
                    authorization_severity(result.decision),
                    presentations.get((result.person.person_id, access_point.id)),
                )
            )
        return DoorAccessDetails(
            tuple(current_access),
            tuple(temporarily_unavailable),
            tuple(no_access),
            (
                await self._synchronization_history_service.for_access_point(access_point.id)
                if self._synchronization_history_service is not None
                else ()
            ),
        )


__all__ = [
    "DoorAccessDetails",
    "DoorAccessPerson",
    "DoorDeniedPerson",
    "DoorTemporarilyUnavailablePerson",
    "DoorDetailsService",
]
