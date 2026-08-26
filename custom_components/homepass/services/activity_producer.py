"""Failure-isolated Activity producer for completed HomePASS operations."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from datetime import datetime
from uuid import UUID

from ..models import (
    AccessPoint,
    ActivityActorType,
    ActivityAttributeValue,
    ActivityEvent,
    ActivityEventType,
    ActivityNavigationKind,
    ActivityNavigationReference,
    ActivityOutcome,
    ActivitySource,
    Person,
)
from .activity import ActivityEventProposal, ActivityService

_LOGGER = logging.getLogger(__name__)


class ActivityProducer:
    """Record HomePASS-owned facts without affecting the primary operation."""

    def __init__(self, activity_service: ActivityService) -> None:
        self._activity_service = activity_service

    async def record(
        self,
        event_type: ActivityEventType,
        *,
        occurred_at: datetime,
        source_event_key: str,
        person: Person | None = None,
        access_point: AccessPoint | None = None,
        attributes: Mapping[str, ActivityAttributeValue] | None = None,
        correlation_id: UUID | None = None,
        outcome: ActivityOutcome | None = None,
    ) -> ActivityEvent | None:
        """Delegate one canonical fact and safely isolate Activity failures."""
        navigation: list[ActivityNavigationReference] = []
        if person is not None:
            navigation.append(
                ActivityNavigationReference(ActivityNavigationKind.PERSON, person.person_id)
            )
        if access_point is not None:
            navigation.append(
                ActivityNavigationReference(ActivityNavigationKind.DOOR, access_point.id)
            )
        try:
            return await self._activity_service.record(
                ActivityEventProposal(
                    event_type=event_type,
                    occurred_at=occurred_at,
                    source=ActivitySource.HOME_PASS,
                    actor_type=ActivityActorType.SYSTEM,
                    person_id=None if person is None else person.person_id,
                    person_name=None if person is None else person.display_name,
                    door_id=None if access_point is None else access_point.id,
                    door_name=None if access_point is None else access_point.display_name,
                    attributes={} if attributes is None else attributes,
                    navigation=tuple(navigation),
                    correlation_id=correlation_id,
                    source_event_key=source_event_key,
                    outcome=outcome,
                )
            )
        except Exception:  # noqa: BLE001 - Activity cannot roll back a completed operation
            _LOGGER.error("A completed HomePASS operation could not be recorded in Activity")
            return None


__all__ = ["ActivityProducer"]
