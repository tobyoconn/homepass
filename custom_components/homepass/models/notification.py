"""Canonical registry for Activity-driven homeowner notifications."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType

from .activity import ActivityAccessMethod, ActivityEvent, ActivityEventType, LockEventOrigin


class NotificationEvent(StrEnum):
    """Stable homeowner-selectable notification identifiers."""

    DOOR_PIN_UNLOCKED = "door_pin_unlocked"
    DOOR_THUMBTURN_UNLOCKED = "door_thumbturn_unlocked"
    DOOR_HOMEPASS_UNLOCKED = "door_homepass_unlocked"
    DOOR_LOCKED = "door_locked"
    DOOR_OPENED = "door_opened"
    DOOR_CLOSED = "door_closed"
    DOOR_LEFT_OPEN = "door_left_open"
    USER_ADDED = "user_added"
    USER_REMOVED = "user_removed"
    PIN_CREATED = "pin_created"
    PIN_CHANGED = "pin_changed"
    PIN_DELETED = "pin_deleted"
    ACCESS_GRANTED = "access_granted"
    ACCESS_REVOKED = "access_revoked"
    SCHEDULE_CHANGED = "schedule_changed"
    ACCESS_EXPIRES_SOON = "access_expires_soon"
    ACCESS_EXPIRED = "access_expired"
    PIN_SYNCHRONIZED = "pin_synchronized"
    PIN_VERIFICATION_PENDING = "pin_verification_pending"
    PIN_SYNCHRONIZATION_FAILED = "pin_synchronization_failed"
    SYNCHRONIZATION_RECOVERED = "synchronization_recovered"
    DOOR_OFFLINE = "door_offline"
    DOOR_BACK_ONLINE = "door_back_online"
    BATTERY_LOW = "battery_low"
    BATTERY_CRITICAL = "battery_critical"
    UNKNOWN_PIN_ATTEMPT = "unknown_pin_attempt"
    REPEATED_INVALID_PIN_ATTEMPTS = "repeated_invalid_pin_attempts"
    LOCK_TAMPER = "lock_tamper"


class NotificationCategory(StrEnum):
    """Stable Settings groups for notification choices."""

    DOOR_ACTIVITY = "door_activity"
    USERS_ACCESS = "users_access"
    SYNCHRONIZATION = "synchronization"
    DOOR_HEALTH = "door_health"
    SECURITY = "security"


@dataclass(frozen=True, slots=True)
class NotificationDefinition:
    """One registry definition shared by Settings and delivery."""

    event: NotificationEvent
    category: NotificationCategory
    title: str
    default_enabled: bool
    activity_events: tuple[ActivityEventType, ...]
    icon: str | None = None
    supported: bool = True


def _definition(
    event: NotificationEvent,
    category: NotificationCategory,
    title: str,
    default_enabled: bool,
    *activity_events: ActivityEventType,
    icon: str | None = None,
    supported: bool = True,
) -> NotificationDefinition:
    return NotificationDefinition(
        event,
        category,
        title,
        default_enabled,
        activity_events,
        icon,
        supported,
    )


NOTIFICATION_DEFINITIONS: Mapping[NotificationEvent, NotificationDefinition] = MappingProxyType(
    {
        definition.event: definition
        for definition in (
            _definition(
                NotificationEvent.DOOR_PIN_UNLOCKED,
                NotificationCategory.DOOR_ACTIVITY,
                "PIN unlock",
                True,
                ActivityEventType.DOOR_UNLOCKED,
                icon="mdi:lock-open-variant",
            ),
            _definition(
                NotificationEvent.DOOR_THUMBTURN_UNLOCKED,
                NotificationCategory.DOOR_ACTIVITY,
                "Thumb-turn unlock",
                False,
                ActivityEventType.DOOR_UNLOCKED,
                icon="mdi:lock-open-variant",
            ),
            _definition(
                NotificationEvent.DOOR_HOMEPASS_UNLOCKED,
                NotificationCategory.DOOR_ACTIVITY,
                "HomePASS unlock",
                True,
                ActivityEventType.DOOR_UNLOCKED,
                icon="mdi:lock-open-variant",
            ),
            _definition(
                NotificationEvent.DOOR_LOCKED,
                NotificationCategory.DOOR_ACTIVITY,
                "Door locked",
                True,
                ActivityEventType.DOOR_LOCKED,
                icon="mdi:lock",
            ),
            _definition(
                NotificationEvent.DOOR_OPENED,
                NotificationCategory.DOOR_ACTIVITY,
                "Door opened",
                False,
                ActivityEventType.DOOR_OPENED,
                icon="mdi:door-open",
            ),
            _definition(
                NotificationEvent.DOOR_CLOSED,
                NotificationCategory.DOOR_ACTIVITY,
                "Door closed",
                False,
                ActivityEventType.DOOR_CLOSED,
                icon="mdi:door-closed",
            ),
            _definition(
                NotificationEvent.DOOR_LEFT_OPEN,
                NotificationCategory.DOOR_ACTIVITY,
                "Door left open",
                True,
                ActivityEventType.DOOR_LEFT_OPEN,
                icon="mdi:door-open",
            ),
            _definition(
                NotificationEvent.USER_ADDED,
                NotificationCategory.USERS_ACCESS,
                "User added",
                True,
                ActivityEventType.PERSON_ADDED,
                icon="mdi:account-plus",
            ),
            _definition(
                NotificationEvent.USER_REMOVED,
                NotificationCategory.USERS_ACCESS,
                "User removed",
                True,
                ActivityEventType.PERSON_REMOVED,
                icon="mdi:account-minus",
            ),
            _definition(
                NotificationEvent.PIN_CREATED,
                NotificationCategory.USERS_ACCESS,
                "PIN created",
                True,
                ActivityEventType.CREDENTIAL_ADDED,
                icon="mdi:dialpad",
            ),
            _definition(
                NotificationEvent.PIN_CHANGED,
                NotificationCategory.USERS_ACCESS,
                "PIN changed",
                True,
                ActivityEventType.CREDENTIAL_UPDATED,
                icon="mdi:dialpad",
            ),
            _definition(
                NotificationEvent.PIN_DELETED,
                NotificationCategory.USERS_ACCESS,
                "PIN deleted",
                True,
                ActivityEventType.CREDENTIAL_REMOVED,
                icon="mdi:dialpad",
            ),
            _definition(
                NotificationEvent.ACCESS_GRANTED,
                NotificationCategory.USERS_ACCESS,
                "Access granted",
                True,
                ActivityEventType.ACCESS_GRANTED,
                icon="mdi:key-plus",
            ),
            _definition(
                NotificationEvent.ACCESS_REVOKED,
                NotificationCategory.USERS_ACCESS,
                "Access revoked",
                True,
                ActivityEventType.ACCESS_REVOKED,
                icon="mdi:key-minus",
            ),
            _definition(
                NotificationEvent.SCHEDULE_CHANGED,
                NotificationCategory.USERS_ACCESS,
                "Schedule changed",
                True,
                ActivityEventType.SCHEDULE_CHANGED,
                icon="mdi:calendar-clock",
            ),
            _definition(
                NotificationEvent.ACCESS_EXPIRES_SOON,
                NotificationCategory.USERS_ACCESS,
                "Access expires soon",
                True,
                ActivityEventType.ACCESS_EXPIRES_SOON,
                icon="mdi:calendar-alert",
            ),
            _definition(
                NotificationEvent.ACCESS_EXPIRED,
                NotificationCategory.USERS_ACCESS,
                "Access expired",
                True,
                ActivityEventType.ACCESS_EXPIRED,
                icon="mdi:calendar-remove",
            ),
            _definition(
                NotificationEvent.PIN_SYNCHRONIZED,
                NotificationCategory.SYNCHRONIZATION,
                "PIN synchronized",
                True,
                ActivityEventType.CREDENTIAL_ADDED,
                ActivityEventType.SYNCHRONIZATION_COMPLETED,
                icon="mdi:sync",
            ),
            _definition(
                NotificationEvent.PIN_VERIFICATION_PENDING,
                NotificationCategory.SYNCHRONIZATION,
                "PIN verification pending",
                True,
                ActivityEventType.CREDENTIAL_VERIFICATION_PENDING,
                icon="mdi:progress-clock",
            ),
            _definition(
                NotificationEvent.PIN_SYNCHRONIZATION_FAILED,
                NotificationCategory.SYNCHRONIZATION,
                "PIN synchronization failed",
                True,
                ActivityEventType.CREDENTIAL_VERIFICATION_FAILED,
                ActivityEventType.SYNCHRONIZATION_ATTENTION_REQUIRED,
                icon="mdi:sync-alert",
            ),
            _definition(
                NotificationEvent.SYNCHRONIZATION_RECOVERED,
                NotificationCategory.SYNCHRONIZATION,
                "Synchronization recovered",
                True,
                ActivityEventType.SYNCHRONIZATION_RECOVERED,
                icon="mdi:sync-circle",
            ),
            _definition(
                NotificationEvent.DOOR_OFFLINE,
                NotificationCategory.DOOR_HEALTH,
                "Door offline",
                True,
                ActivityEventType.DOOR_OFFLINE,
                icon="mdi:lan-disconnect",
            ),
            _definition(
                NotificationEvent.DOOR_BACK_ONLINE,
                NotificationCategory.DOOR_HEALTH,
                "Door back online",
                True,
                ActivityEventType.DOOR_ONLINE,
                icon="mdi:lan-connect",
            ),
            _definition(
                NotificationEvent.BATTERY_LOW,
                NotificationCategory.DOOR_HEALTH,
                "Battery low",
                True,
                ActivityEventType.BATTERY_LOW,
                icon="mdi:battery-low",
            ),
            _definition(
                NotificationEvent.BATTERY_CRITICAL,
                NotificationCategory.DOOR_HEALTH,
                "Battery critical",
                True,
                ActivityEventType.BATTERY_CRITICAL,
                icon="mdi:battery-alert",
            ),
            _definition(
                NotificationEvent.UNKNOWN_PIN_ATTEMPT,
                NotificationCategory.SECURITY,
                "Unknown PIN attempt",
                True,
                ActivityEventType.PIN_FAILED,
                icon="mdi:shield-alert",
            ),
            _definition(
                NotificationEvent.REPEATED_INVALID_PIN_ATTEMPTS,
                NotificationCategory.SECURITY,
                "Repeated invalid PIN attempts",
                True,
                ActivityEventType.PIN_FAILED,
                icon="mdi:shield-alert",
            ),
            _definition(
                NotificationEvent.LOCK_TAMPER,
                NotificationCategory.SECURITY,
                "Lock tamper",
                True,
                ActivityEventType.TAMPER_DETECTED,
                icon="mdi:alarm-light",
                supported=False,
            ),
        )
    }
)

CATEGORY_TITLES: Mapping[NotificationCategory, str] = MappingProxyType(
    {
        NotificationCategory.DOOR_ACTIVITY: "Door Activity",
        NotificationCategory.USERS_ACCESS: "Users & Access",
        NotificationCategory.SYNCHRONIZATION: "Synchronization",
        NotificationCategory.DOOR_HEALTH: "Door Health",
        NotificationCategory.SECURITY: "Security",
    }
)


def notification_event_for_activity(event: ActivityEvent) -> NotificationEvent | None:
    """Resolve one canonical notification without guessing beyond Activity evidence."""
    event_type = event.event_type
    if event_type is ActivityEventType.DOOR_UNLOCKED:
        method = event.access_method
        origin = event.lock_origin
        if method is ActivityAccessMethod.KEYPAD and origin in {
            LockEventOrigin.UNKNOWN,
            LockEventOrigin.HOMEPASS_KEYPAD,
        }:
            return NotificationEvent.DOOR_PIN_UNLOCKED
        if method is ActivityAccessMethod.MANUAL and origin is LockEventOrigin.PHYSICAL_AT_DOOR:
            return NotificationEvent.DOOR_THUMBTURN_UNLOCKED
        if method is ActivityAccessMethod.REMOTE and origin in {
            LockEventOrigin.HOMEPASS_MANUAL,
            LockEventOrigin.HOMEPASS_AUTOMATIC,
            LockEventOrigin.NFC_PASSKEY,
        }:
            return NotificationEvent.DOOR_HOMEPASS_UNLOCKED
        return None
    if event_type is ActivityEventType.CREDENTIAL_ADDED:
        return (
            NotificationEvent.PIN_SYNCHRONIZED
            if event.door_id is not None
            else NotificationEvent.PIN_CREATED
        )
    if event_type is ActivityEventType.CREDENTIAL_REMOVED:
        return NotificationEvent.PIN_DELETED if event.door_id is None else None
    if event_type is ActivityEventType.PIN_FAILED:
        attempts = event.attributes.get("attempt_count", 1)
        return (
            NotificationEvent.REPEATED_INVALID_PIN_ATTEMPTS
            if isinstance(attempts, int) and attempts > 1
            else NotificationEvent.UNKNOWN_PIN_ATTEMPT
        )
    for definition in NOTIFICATION_DEFINITIONS.values():
        if event_type in definition.activity_events:
            return definition.event
    return None


__all__ = [
    "CATEGORY_TITLES",
    "NOTIFICATION_DEFINITIONS",
    "NotificationCategory",
    "NotificationDefinition",
    "NotificationEvent",
    "notification_event_for_activity",
]
