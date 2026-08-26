"""Shared homeowner-facing presentation for canonical Activity Events."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TypedDict

from ..models import (
    ActivityAccessMethod,
    ActivityActorType,
    ActivityCategory,
    ActivityEvent,
    ActivityEventType,
    ActivityNavigationReference,
    ActivitySeverity,
    ActivitySource,
    LockEventOrigin,
)


class ActivityNavigationPresentationData(TypedDict):
    """Opaque navigation reference safe for a future frontend."""

    target: str
    id: str


class ActivityPresentationData(TypedDict):
    """Presentation-only recent Activity response."""

    title: str
    description: str
    severity: str
    category: str
    occurred_at: str
    actor: str | None
    person_name: str | None
    door_name: str | None
    navigation: list[ActivityNavigationPresentationData]


@dataclass(frozen=True, slots=True)
class ActivityPresentation:
    """One compact homeowner-facing Activity row."""

    title: str
    description: str
    severity: ActivitySeverity
    category: str
    occurred_at: datetime
    actor: str | None
    person_name: str | None
    door_name: str | None
    navigation: tuple[ActivityNavigationReference, ...]

    def to_dict(self) -> ActivityPresentationData:
        return {
            "title": self.title,
            "description": self.description,
            "severity": self.severity.value,
            "category": self.category,
            "occurred_at": self.occurred_at.isoformat(),
            "actor": self.actor,
            "person_name": self.person_name,
            "door_name": self.door_name,
            "navigation": [
                {"target": reference.kind.value, "id": str(reference.target_id)}
                for reference in self.navigation
            ],
        }


_CATEGORY_LABELS = {
    ActivityCategory.DOOR: "Door",
    ActivityCategory.ACCESS: "Access",
    ActivityCategory.SECURITY: "Security",
    ActivityCategory.CONNECTIVITY: "Connectivity",
    ActivityCategory.ADMINISTRATION: "Administration",
    ActivityCategory.SYNCHRONIZATION: "Synchronization",
    ActivityCategory.MAINTENANCE: "Maintenance",
}

_COPY: dict[ActivityEventType, tuple[str, str]] = {
    ActivityEventType.DOOR_OPENED: ("Door opened", "{door} opened."),
    ActivityEventType.DOOR_CLOSED: ("Door closed", "{door} closed."),
    ActivityEventType.PIN_FAILED: ("Access attempt failed", "Failed PIN attempt at {door}."),
    ActivityEventType.LOCK_JAMMED: ("Door needs attention", "Lock jam detected at {door}."),
    ActivityEventType.TAMPER_DETECTED: (
        "Door needs attention",
        "Tamper detection was reported at {door}.",
    ),
    ActivityEventType.DOOR_OFFLINE: ("Door offline", "{door} went offline."),
    ActivityEventType.DOOR_ONLINE: ("Door online", "{door} is back online."),
    ActivityEventType.DOOR_LEFT_OPEN: ("Door left open", "{door} has been left open."),
    ActivityEventType.PERSON_ADDED: ("User added", "{person} was added to HomePASS."),
    ActivityEventType.PERSON_UPDATED: ("User updated", "{person} was updated."),
    ActivityEventType.PERSON_ENABLED: ("User enabled", "{person} was enabled."),
    ActivityEventType.PERSON_DISABLED: ("User disabled", "{person} was disabled."),
    ActivityEventType.PERSON_REMOVED: ("User removed", "{person} was removed from HomePASS."),
    ActivityEventType.DOOR_ADDED: ("Door added", "{door} was added to HomePASS."),
    ActivityEventType.DOOR_UPDATED: ("Door updated", "{door} was updated."),
    ActivityEventType.DOOR_ENABLED: ("Door enabled", "{door} was enabled."),
    ActivityEventType.DOOR_DISABLED: ("Door disabled", "{door} was disabled."),
    ActivityEventType.DOOR_REMOVED: ("Door removed", "{door} was removed from HomePASS."),
    ActivityEventType.ACCESS_GRANTED: (
        "Access added",
        "{person} was given access to {door}.",
    ),
    ActivityEventType.ACCESS_REVOKED: (
        "Access removed",
        "{person}'s access to {door} was removed.",
    ),
    ActivityEventType.ACCESS_EXPIRES_SOON: (
        "Access expires soon",
        "{person}'s access to {door} expires soon.",
    ),
    ActivityEventType.ACCESS_EXPIRED: (
        "Access expired",
        "{person}'s access to {door} expired.",
    ),
    ActivityEventType.SCHEDULE_CREATED: ("Schedule added", "{schedule} was added."),
    ActivityEventType.SCHEDULE_UPDATED: ("Schedule updated", "{schedule} was updated."),
    ActivityEventType.SCHEDULE_REMOVED: ("Schedule removed", "{schedule} was removed."),
    ActivityEventType.SCHEDULE_CHANGED: (
        "Schedule changed",
        "{person}'s access schedule was changed.",
    ),
    ActivityEventType.CREDENTIAL_ADDED: (
        "Access code added",
        "An access code was added for {person}.",
    ),
    ActivityEventType.CREDENTIAL_UPDATED: (
        "Access code updated",
        "An access code was updated for {person}.",
    ),
    ActivityEventType.CREDENTIAL_REMOVED: (
        "Access code removed",
        "An access code was removed for {person}.",
    ),
    ActivityEventType.CREDENTIAL_VERIFICATION_FAILED: (
        "Access could not be verified",
        "HomePASS could not verify {person}'s access to {door}.",
    ),
    ActivityEventType.CREDENTIAL_VERIFICATION_PENDING: (
        "PIN verification pending",
        "HomePASS is waiting to verify {person}'s PIN at {door}.",
    ),
    ActivityEventType.SYNCHRONIZATION_COMPLETED: (
        "Synchronization completed",
        "HomePASS synchronized access with {door}.",
    ),
    ActivityEventType.SYNCHRONIZATION_ATTENTION_REQUIRED: (
        "Synchronization needs attention",
        "HomePASS could not confirm synchronization with {door}.",
    ),
    ActivityEventType.SYNCHRONIZATION_RECOVERED: (
        "Synchronization restored",
        "HomePASS and {door} are synchronized again.",
    ),
    ActivityEventType.CONFIGURATION_CHANGED: (
        "Configuration changed",
        "HomePASS configuration was changed.",
    ),
    ActivityEventType.CONFIGURATION_ATTENTION_REQUIRED: (
        "Configuration needs attention",
        "HomePASS configuration needs attention.",
    ),
    ActivityEventType.BATTERY_LOW: ("Battery low", "{door} battery is low."),
    ActivityEventType.BATTERY_CRITICAL: (
        "Battery critical",
        "{door} battery is critically low.",
    ),
}


def _actor_label(event: ActivityEvent) -> str | None:
    if (
        event.lock_origin in {LockEventOrigin.NFC_PASSKEY, LockEventOrigin.HOMEPASS_KEYPAD}
        and event.actor_type is ActivityActorType.PERSON
    ):
        return event.actor_name
    if event.lock_origin is not None:
        return None
    if event.actor_type is ActivityActorType.PERSON:
        return event.actor_name
    if event.actor_type is ActivityActorType.CREDENTIAL:
        return "Keypad user"
    if event.actor_type is ActivityActorType.MANUAL:
        return "Manual operation"
    if event.actor_type is ActivityActorType.REMOTE:
        return "Remote operation"
    if event.actor_type is ActivityActorType.SYSTEM:
        return "Home Assistant" if event.source is ActivitySource.HOME_ASSISTANT else "HomePASS"
    return None


def _lock_title(event: ActivityEvent, action: str) -> str:
    door = event.door_name or "Door"
    if event.lock_origin is LockEventOrigin.HOMEPASS_MANUAL:
        return f"{door} {action} from HomePASS"
    if event.lock_origin is LockEventOrigin.HOMEPASS_AUTOMATIC:
        return f"{door} {action} automatically by HomePASS"
    if event.lock_origin is LockEventOrigin.HOMEPASS_KEYPAD:
        if event.actor_name is not None:
            return f"{event.actor_name} {action} {door} with a PIN."
        return f"{door} {action} with a PIN."
    if event.lock_origin is LockEventOrigin.NFC_PASSKEY:
        return f"{door} {action} with HomePASS NFC"
    if event.lock_origin is LockEventOrigin.PHYSICAL_AT_DOOR:
        return f"{door} {action} at the door"
    return f"{door} {action}"


def _unlock_title(event: ActivityEvent) -> str:
    """Describe an unlock using only persisted authoritative method evidence."""
    door = event.door_name or "Door"
    actor = event.actor_name
    if event.access_method is None:
        return _lock_title(event, "unlocked")
    if event.access_method is ActivityAccessMethod.KEYPAD:
        if actor is not None:
            return f"{actor} unlocked {door} with a PIN."
        return f"{door} was unlocked with a PIN."
    if event.access_method is ActivityAccessMethod.FINGERPRINT:
        if actor is not None:
            return f"{actor} unlocked {door} with a fingerprint."
        return f"{door} was unlocked with a fingerprint."
    if event.access_method is ActivityAccessMethod.MANUAL:
        return f"{door} was unlocked manually."
    if event.access_method is ActivityAccessMethod.REMOTE:
        if event.lock_origin is LockEventOrigin.NFC_PASSKEY:
            if actor is not None:
                return f"{actor} unlocked {door} by NFC."
            return f"{door} was unlocked with HomePASS NFC."
        if actor is not None:
            return f"{actor} unlocked {door} remotely."
        if event.lock_origin is LockEventOrigin.HOMEPASS_MANUAL:
            return f"{door} was unlocked remotely from HomePASS."
        if event.lock_origin is LockEventOrigin.HOMEPASS_AUTOMATIC:
            return f"{door} was unlocked automatically by HomePASS."
        return f"{door} was unlocked remotely."
    return f"{door} was unlocked."


def present_activity(event: ActivityEvent) -> ActivityPresentation:
    """Map one canonical fact to shared sanitized homeowner presentation."""
    if not isinstance(event, ActivityEvent):
        raise TypeError("Activity presentation requires an ActivityEvent")
    if event.event_type is ActivityEventType.DOOR_LOCKED:
        title = _lock_title(event, "locked")
        description = ""
    elif event.event_type is ActivityEventType.DOOR_UNLOCKED:
        title = _unlock_title(event)
        description = ""
    elif event.event_type is ActivityEventType.DOOR_OPENED:
        door = event.door_name or "Door"
        title = (
            f"{event.actor_name} opened {door} with a PIN."
            if event.access_method is ActivityAccessMethod.KEYPAD and event.actor_name is not None
            else f"{door} opened"
        )
        description = ""
    elif event.event_type is ActivityEventType.DOOR_CLOSED:
        door = event.door_name or "Door"
        title = (
            f"{event.actor_name} closed {door} with a PIN."
            if event.access_method is ActivityAccessMethod.KEYPAD and event.actor_name is not None
            else f"{door} closed"
        )
        description = ""
    elif event.event_type in {
        ActivityEventType.PERSON_ADDED,
        ActivityEventType.PERSON_UPDATED,
        ActivityEventType.PERSON_ENABLED,
        ActivityEventType.PERSON_DISABLED,
        ActivityEventType.PERSON_REMOVED,
    }:
        action = {
            ActivityEventType.PERSON_ADDED: "added",
            ActivityEventType.PERSON_UPDATED: "updated",
            ActivityEventType.PERSON_ENABLED: "enabled",
            ActivityEventType.PERSON_DISABLED: "disabled",
            ActivityEventType.PERSON_REMOVED: "removed",
        }[event.event_type]
        title = f"{event.person_name or 'User'} {action}"
        description = {
            ActivityEventType.PERSON_ADDED: "Added to HomePASS",
            ActivityEventType.PERSON_REMOVED: "Removed from HomePASS",
        }.get(event.event_type, "")
    elif event.event_type is ActivityEventType.CREDENTIAL_ADDED and event.door_name:
        title = "PIN synchronized"
        description = (
            f"{event.person_name or 'User'}'s PIN was synchronized with {event.door_name}."
        )
    elif event.event_type is ActivityEventType.CREDENTIAL_UPDATED and event.door_name:
        title = "PIN updated"
        description = (
            f"{event.person_name or 'User'}'s PIN was updated and synchronized "
            f"with {event.door_name}."
        )
    elif event.event_type is ActivityEventType.CREDENTIAL_REMOVED and event.door_name:
        title = "PIN removed"
        description = f"{event.person_name or 'User'}'s PIN was removed from {event.door_name}."
    elif (
        event.event_type is ActivityEventType.SYNCHRONIZATION_ATTENTION_REQUIRED
        and event.person_name
    ):
        title = "Synchronization needs attention"
        description = (
            f"HomePASS could not synchronize {event.person_name}'s access "
            f"with {event.door_name or 'Door'}."
        )
    elif event.event_type is ActivityEventType.SCHEDULE_CHANGED and event.door_name:
        title = "Schedule changed"
        description = f"{event.person_name or 'User'}'s schedule for {event.door_name} was updated."
    else:
        title, template = _COPY[event.event_type]
        description = template.format(
            door=event.door_name or "Door",
            person=event.person_name or "User",
            schedule=event.attributes.get("schedule_name", "Schedule"),
        )
    return ActivityPresentation(
        title=title,
        description=description,
        severity=event.severity,
        category=_CATEGORY_LABELS[event.category],
        occurred_at=event.occurred_at,
        actor=_actor_label(event),
        person_name=event.person_name,
        door_name=event.door_name,
        navigation=event.navigation,
    )


__all__ = [
    "ActivityNavigationPresentationData",
    "ActivityPresentation",
    "ActivityPresentationData",
    "present_activity",
]
