"""Canonical recording and reading boundaries for HomePASS Activity."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import NotRequired, TypedDict
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from ..models import (
    NOTIFICATION_DEFINITIONS,
    ActivityAccessMethod,
    ActivityActorType,
    ActivityAttributeValue,
    ActivityEvent,
    ActivityEventType,
    ActivityNavigationReference,
    ActivityOutcome,
    ActivitySource,
    NotificationEvent,
    activity_event_definition,
    notification_event_for_activity,
)
from ..repositories.activity import ACTIVITY_RETENTION_LIMIT, ActivityRepository
from .activity_presentation import ActivityPresentation, present_activity

_LOGGER = logging.getLogger(__name__)
_DEFAULT_RECENT_LIMIT = 20
_MAX_RECENT_LIMIT = 100


class ActivityFilterOptionData(TypedDict):
    """One homeowner-facing Activity event filter option."""

    id: str
    title: str
    subgroup: NotRequired[str]


class ActivityFilterGroupData(TypedDict):
    """One homeowner-facing group of Activity event filter options."""

    id: str
    title: str
    options: list[ActivityFilterOptionData]


class ActivityFilterEvent(StrEnum):
    """Stable Dashboard Activity filter values independent of delivery preferences."""

    PIN_UNLOCK = "pin_unlock"
    FINGERPRINT_UNLOCK = "fingerprint_unlock"
    MANUAL_UNLOCK = "manual_unlock"
    REMOTE_UNLOCK = "remote_unlock"
    UNKNOWN_UNLOCK = "unknown_unlock_method"
    DOOR_LOCKED = "door_locked"
    DOOR_OPENED = "door_opened"
    DOOR_CLOSED = "door_closed"
    USER_ADDED = "user_added"
    USER_REMOVED = "user_removed"
    PIN_CREATED = "pin_created"
    PIN_CHANGED = "pin_changed"
    PIN_DELETED = "pin_deleted"
    ACCESS_GRANTED = "access_granted"
    ACCESS_REVOKED = "access_revoked"
    SCHEDULE_CHANGED = "schedule_changed"
    PIN_SYNCHRONIZED = "pin_synchronized"
    PIN_VERIFICATION_PENDING = "pin_verification_pending"
    PIN_SYNCHRONIZATION_FAILED = "pin_synchronization_failed"
    SYNCHRONIZATION_RECOVERED = "synchronization_recovered"
    UNKNOWN_PIN_ATTEMPT = "unknown_pin_attempt"
    REPEATED_INVALID_PIN_ATTEMPTS = "repeated_invalid_pin_attempts"


_UNLOCK_FILTER_TITLES = {
    ActivityFilterEvent.PIN_UNLOCK: "PIN unlock",
    ActivityFilterEvent.FINGERPRINT_UNLOCK: "Fingerprint unlock",
    ActivityFilterEvent.MANUAL_UNLOCK: "Manual unlock",
    ActivityFilterEvent.REMOTE_UNLOCK: "Remote unlock",
    ActivityFilterEvent.UNKNOWN_UNLOCK: "Unknown unlock method",
}

_ACTIVITY_FILTER_GROUPS: tuple[tuple[str, str, tuple[ActivityFilterEvent, ...]], ...] = (
    (
        "door_activity",
        "Door Activity",
        (
            ActivityFilterEvent.PIN_UNLOCK,
            ActivityFilterEvent.FINGERPRINT_UNLOCK,
            ActivityFilterEvent.MANUAL_UNLOCK,
            ActivityFilterEvent.REMOTE_UNLOCK,
            ActivityFilterEvent.UNKNOWN_UNLOCK,
            ActivityFilterEvent.DOOR_LOCKED,
            ActivityFilterEvent.DOOR_OPENED,
            ActivityFilterEvent.DOOR_CLOSED,
        ),
    ),
    (
        "user_access",
        "User & Access",
        (
            ActivityFilterEvent.USER_ADDED,
            ActivityFilterEvent.USER_REMOVED,
            ActivityFilterEvent.PIN_CREATED,
            ActivityFilterEvent.PIN_CHANGED,
            ActivityFilterEvent.PIN_DELETED,
            ActivityFilterEvent.ACCESS_GRANTED,
            ActivityFilterEvent.ACCESS_REVOKED,
            ActivityFilterEvent.SCHEDULE_CHANGED,
        ),
    ),
    (
        "synchronization",
        "Synchronization",
        (
            ActivityFilterEvent.PIN_SYNCHRONIZED,
            ActivityFilterEvent.PIN_VERIFICATION_PENDING,
            ActivityFilterEvent.PIN_SYNCHRONIZATION_FAILED,
            ActivityFilterEvent.SYNCHRONIZATION_RECOVERED,
        ),
    ),
    (
        "security",
        "Security",
        (
            ActivityFilterEvent.UNKNOWN_PIN_ATTEMPT,
            ActivityFilterEvent.REPEATED_INVALID_PIN_ATTEMPTS,
        ),
    ),
)

ACTIVITY_FILTER_EVENTS = frozenset(
    event for _group_id, _title, events in _ACTIVITY_FILTER_GROUPS for event in events
)


def activity_filter_groups() -> tuple[ActivityFilterGroupData, ...]:
    """Return the canonical homeowner-facing filter catalog."""
    return tuple(
        {
            "id": group_id,
            "title": title,
            "options": [_activity_filter_option(event) for event in events],
        }
        for group_id, title, events in _ACTIVITY_FILTER_GROUPS
    )


def _activity_filter_option(event: ActivityFilterEvent) -> ActivityFilterOptionData:
    title = _UNLOCK_FILTER_TITLES.get(event)
    if title is None:
        title = NOTIFICATION_DEFINITIONS[NotificationEvent(event.value)].title
    option: ActivityFilterOptionData = {
        "id": event.value,
        "title": title,
    }
    if event in _UNLOCK_FILTER_TITLES:
        option["subgroup"] = "Unlocks"
    return option


def activity_filter_event_for(event: ActivityEvent) -> ActivityFilterEvent | None:
    """Map one stored fact to one exact Dashboard filter value."""
    if event.event_type is ActivityEventType.DOOR_UNLOCKED:
        return {
            ActivityAccessMethod.KEYPAD: ActivityFilterEvent.PIN_UNLOCK,
            ActivityAccessMethod.FINGERPRINT: ActivityFilterEvent.FINGERPRINT_UNLOCK,
            ActivityAccessMethod.MANUAL: ActivityFilterEvent.MANUAL_UNLOCK,
            ActivityAccessMethod.REMOTE: ActivityFilterEvent.REMOTE_UNLOCK,
            ActivityAccessMethod.UNKNOWN: ActivityFilterEvent.UNKNOWN_UNLOCK,
            None: ActivityFilterEvent.UNKNOWN_UNLOCK,
        }[event.access_method]
    notification_event = notification_event_for_activity(event)
    if notification_event is None:
        return None
    try:
        return ActivityFilterEvent(notification_event.value)
    except ValueError:
        return None


@dataclass(frozen=True, slots=True)
class ActivityFilter:
    """Typed AND filter applied to canonical Activity Events before presentation."""

    event_types: frozenset[ActivityFilterEvent] | None = None
    door_id: UUID | None = None
    person_id: UUID | None = None

    def __post_init__(self) -> None:
        if self.event_types is not None:
            if not isinstance(self.event_types, frozenset) or not all(
                isinstance(event, ActivityFilterEvent) for event in self.event_types
            ):
                raise TypeError("Activity event filters must be canonical values")
            if not self.event_types <= ACTIVITY_FILTER_EVENTS:
                raise ValueError("Activity event filter is not supported")
        if self.door_id is not None and not isinstance(self.door_id, UUID):
            raise TypeError("Activity Door filter must be a UUID")
        if self.person_id is not None and not isinstance(self.person_id, UUID):
            raise TypeError("Activity User filter must be a UUID")

    @property
    def active(self) -> bool:
        """Return whether any filter group differs from its default."""
        return (
            self.event_types is not None or self.door_id is not None or self.person_id is not None
        )

    def matches(self, event: ActivityEvent) -> bool:
        """Match one canonical fact without inferring identity from display text."""
        if self.event_types is not None:
            filter_event = activity_filter_event_for(event)
            if filter_event not in self.event_types:
                return False
        if self.door_id is not None and event.door_id != self.door_id:
            return False
        if self.person_id is not None:
            explicit_subject = event.person_id == self.person_id
            explicit_actor = (
                event.actor_type is ActivityActorType.PERSON and event.actor_id == self.person_id
            )
            if not explicit_subject and not explicit_actor:
                return False
        return True


def _utcnow() -> datetime:
    return datetime.now(UTC)


type ActivitySubscriber = Callable[[ActivityEvent], Awaitable[None]]


class ActivityPublisher:
    """Publish newly persisted facts without coupling producers to consumers."""

    def __init__(self, subscribers: Sequence[ActivitySubscriber] = ()) -> None:
        self._subscribers = tuple(subscribers)

    async def publish(self, event: ActivityEvent) -> None:
        """Notify every subscriber after persistence and isolate subscriber failures."""
        for subscriber in self._subscribers:
            try:
                await subscriber(event)
            except Exception:  # noqa: BLE001 - subscribers cannot roll back durable facts
                _LOGGER.warning("An Activity post-record subscriber failed")


@dataclass(frozen=True, slots=True)
class ActivityEventProposal:
    """Structured canonical proposal accepted by the single recording boundary."""

    event_type: ActivityEventType
    occurred_at: datetime
    source: ActivitySource
    actor_type: ActivityActorType
    door_id: UUID | None = None
    person_id: UUID | None = None
    actor_id: UUID | None = None
    access_method: ActivityAccessMethod | None = None
    outcome: ActivityOutcome | None = None
    attributes: Mapping[str, ActivityAttributeValue] = field(default_factory=dict)
    navigation: tuple[ActivityNavigationReference, ...] = ()
    correlation_id: UUID | None = None
    source_event_key: str | None = None
    event_id: UUID | None = None
    door_name: str | None = None
    person_name: str | None = None
    actor_name: str | None = None


class ActivityService:
    """The sole application-layer boundary allowed to record Activity Events."""

    def __init__(
        self,
        repository: ActivityRepository,
        publisher: ActivityPublisher,
        *,
        clock: Callable[[], datetime] = _utcnow,
    ) -> None:
        self._repository = repository
        self._publisher = publisher
        self._clock = clock

    async def record(self, proposal: ActivityEventProposal) -> ActivityEvent:
        """Validate, sanitize, persist once, then publish one immutable fact."""
        if not isinstance(proposal, ActivityEventProposal):
            raise TypeError("ActivityService.record requires an ActivityEventProposal")
        if not isinstance(proposal.event_type, ActivityEventType):
            raise TypeError("Activity event type is invalid")
        if not isinstance(proposal.source, ActivitySource):
            raise TypeError("Activity source is invalid")
        duplicate_identity = self._duplicate_identity(proposal.source, proposal.source_event_key)
        definition = activity_event_definition(proposal.event_type)
        event = ActivityEvent(
            event_id=proposal.event_id or uuid4(),
            occurred_at=proposal.occurred_at,
            recorded_at=self._clock(),
            event_type=proposal.event_type,
            category=definition.category,
            severity=definition.default_severity,
            source=proposal.source,
            actor_type=proposal.actor_type,
            door_id=proposal.door_id,
            person_id=proposal.person_id,
            actor_id=proposal.actor_id,
            access_method=proposal.access_method,
            outcome=proposal.outcome,
            attributes=dict(proposal.attributes),
            navigation=proposal.navigation,
            correlation_id=proposal.correlation_id,
            deduplication_key=duplicate_identity,
            door_name=proposal.door_name,
            person_name=proposal.person_name,
            actor_name=proposal.actor_name,
        )
        result = await self._repository.append(event)
        if result.recorded:
            await self._publisher.publish(result.event)
        return result.event

    @staticmethod
    def _duplicate_identity(source: ActivitySource, source_event_key: str | None) -> UUID | None:
        if source_event_key is None:
            return None
        if not isinstance(source_event_key, str):
            raise TypeError("Activity source event key must be a string")
        normalized = source_event_key.strip()
        if (
            not normalized
            or len(normalized) > 200
            or any(ord(character) < 32 for character in normalized)
        ):
            raise ValueError("Activity source event key is invalid")
        return uuid5(NAMESPACE_URL, f"homepass:activity:{source.value}:{normalized}")


class ActivityReadService:
    """Return recent Activity as presentation-only homeowner data."""

    def __init__(self, repository: ActivityRepository) -> None:
        self._repository = repository

    async def list_recent(
        self,
        limit: int = _DEFAULT_RECENT_LIMIT,
        activity_filter: ActivityFilter | None = None,
    ) -> tuple[ActivityPresentation, ...]:
        if isinstance(limit, bool) or not isinstance(limit, int):
            raise TypeError("Activity limit must be an integer")
        if not 1 <= limit <= _MAX_RECENT_LIMIT:
            raise ValueError(f"Activity limit must be between 1 and {_MAX_RECENT_LIMIT}")
        selected_filter = activity_filter or ActivityFilter()
        if not isinstance(selected_filter, ActivityFilter):
            raise TypeError("Activity filter must be an ActivityFilter")
        repository_limit = ACTIVITY_RETENTION_LIMIT if selected_filter.active else limit
        events = await self._repository.list_events(
            limit=repository_limit,
            newest_first=True,
        )
        return tuple(present_activity(event) for event in events if selected_filter.matches(event))[
            :limit
        ]


__all__ = [
    "ACTIVITY_FILTER_EVENTS",
    "ActivityEventProposal",
    "ActivityFilter",
    "ActivityFilterEvent",
    "ActivityFilterGroupData",
    "ActivityPublisher",
    "ActivityReadService",
    "ActivityService",
    "ActivitySubscriber",
    "activity_filter_event_for",
    "activity_filter_groups",
]
