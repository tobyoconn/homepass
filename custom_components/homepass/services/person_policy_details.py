"""Application service for presentation-ready Person Details access policy."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import NotRequired, TypedDict
from uuid import UUID

from ..models import AuthorizationDecision
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


class PersonAccessDoorData(TypedDict):
    """Serialized allowed Access Point row."""

    access_point_id: str
    display_name: str
    synchronization: NotRequired[SynchronizationPresentationData]


class PersonDeniedDoorData(PersonAccessDoorData):
    """Serialized denied Access Point row."""

    explanation: str


class PersonTemporarilyUnavailableDoorData(PersonDeniedDoorData):
    """Serialized temporary denial with presentation severity."""

    severity: AuthorizationPolicySeverity


class PersonPolicyDetailsData(TypedDict):
    """Serialized Person Details policy response."""

    current_access: list[PersonAccessDoorData]
    temporarily_unavailable: list[PersonTemporarilyUnavailableDoorData]
    no_access: list[PersonDeniedDoorData]
    synchronization_history: list[SynchronizationHistoryPresentationData]


@dataclass(frozen=True, slots=True)
class PersonAccessDoor:
    """One Access Point currently authorized for the selected Person."""

    access_point_id: UUID
    display_name: str
    synchronization: SynchronizationPresentation | None = None

    def to_dict(self) -> PersonAccessDoorData:
        """Serialize one allowed Access Point row."""
        data: PersonAccessDoorData = {
            "access_point_id": str(self.access_point_id),
            "display_name": self.display_name,
        }
        if self.synchronization is not None:
            data["synchronization"] = self.synchronization.to_dict()
        return data


@dataclass(frozen=True, slots=True)
class PersonDeniedDoor:
    """One Access Point without an Access Grant for the selected Person."""

    access_point_id: UUID
    display_name: str
    explanation: str

    def to_dict(self) -> PersonDeniedDoorData:
        """Serialize one denied Access Point row."""
        return {
            "access_point_id": str(self.access_point_id),
            "display_name": self.display_name,
            "explanation": self.explanation,
        }


@dataclass(frozen=True, slots=True)
class PersonTemporarilyUnavailableDoor:
    """One temporarily denied Access Point with presentation metadata."""

    access_point_id: UUID
    display_name: str
    explanation: str
    severity: AuthorizationPolicySeverity
    synchronization: SynchronizationPresentation | None = None

    def to_dict(self) -> PersonTemporarilyUnavailableDoorData:
        """Serialize one temporary-denial Access Point row."""
        data: PersonTemporarilyUnavailableDoorData = {
            "access_point_id": str(self.access_point_id),
            "display_name": self.display_name,
            "explanation": self.explanation,
            "severity": self.severity,
        }
        if self.synchronization is not None:
            data["synchronization"] = self.synchronization.to_dict()
        return data


@dataclass(frozen=True, slots=True)
class PersonPolicyDetails:
    """Access Point policy grouped for direct Person Details presentation."""

    current_access: tuple[PersonAccessDoor, ...]
    temporarily_unavailable: tuple[PersonTemporarilyUnavailableDoor, ...]
    no_access: tuple[PersonDeniedDoor, ...]
    synchronization_history: tuple[SynchronizationHistoryPresentation, ...] = ()

    def to_dict(self) -> PersonPolicyDetailsData:
        """Serialize all three presentation groups."""
        return {
            "current_access": [door.to_dict() for door in self.current_access],
            "temporarily_unavailable": [door.to_dict() for door in self.temporarily_unavailable],
            "no_access": [door.to_dict() for door in self.no_access],
            "synchronization_history": [event.to_dict() for event in self.synchronization_history],
        }


class PersonPolicyDetailsService:
    """Build a single-snapshot policy view for one Person and all durable doors."""

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

    async def get_person_policy_details(
        self,
        *,
        person_id: UUID,
        instant_utc: datetime,
    ) -> PersonPolicyDetails:
        """Group one Person's decision for every durable Access Point."""
        results = await self._authorization_service.authorize_person_for_access_points(
            person_id=person_id,
            instant_utc=instant_utc,
        )
        presentations = (
            await self._synchronization_status_service.relationship_presentations()
            if self._synchronization_status_service is not None
            else {}
        )
        ordered = sorted(
            results,
            key=lambda item: (
                item.access_point.display_name.casefold(),
                str(item.access_point.id),
            ),
        )
        current_access: list[PersonAccessDoor] = []
        temporarily_unavailable: list[PersonTemporarilyUnavailableDoor] = []
        no_access: list[PersonDeniedDoor] = []
        for result in ordered:
            access_point = result.access_point
            if result.decision is AuthorizationDecision.ALLOWED:
                current_access.append(
                    PersonAccessDoor(
                        access_point.id,
                        access_point.display_name,
                        presentations.get((person_id, access_point.id)),
                    )
                )
                continue
            if result.decision is AuthorizationDecision.NO_GRANT:
                no_access.append(
                    PersonDeniedDoor(
                        access_point.id,
                        access_point.display_name,
                        authorization_explanation(result.decision),
                    )
                )
                continue
            temporarily_unavailable.append(
                PersonTemporarilyUnavailableDoor(
                    access_point.id,
                    access_point.display_name,
                    authorization_explanation(result.decision),
                    authorization_severity(result.decision),
                    presentations.get((person_id, access_point.id)),
                )
            )
        return PersonPolicyDetails(
            tuple(current_access),
            tuple(temporarily_unavailable),
            tuple(no_access),
            (
                await self._synchronization_history_service.for_person(person_id)
                if self._synchronization_history_service is not None
                else ()
            ),
        )


__all__ = [
    "PersonAccessDoor",
    "PersonDeniedDoor",
    "PersonPolicyDetails",
    "PersonPolicyDetailsService",
    "PersonTemporarilyUnavailableDoor",
]
