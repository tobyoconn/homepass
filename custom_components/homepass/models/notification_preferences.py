"""Durable notification preferences without notification delivery behavior."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TypedDict

from .notification import NOTIFICATION_DEFINITIONS, NotificationEvent

NOTIFICATION_PREFERENCES_VERSION = 2
MAX_NOTIFICATION_DEVICES = 128
_DEVICE_ID_PATTERN = re.compile(r"mobile_app:[A-Za-z0-9_-]{1,128}")
_LEGACY_DOOR_UNLOCKED_EVENT = "door_unlocked"
_UNLOCK_NOTIFICATION_EVENTS = (
    NotificationEvent.DOOR_PIN_UNLOCKED,
    NotificationEvent.DOOR_THUMBTURN_UNLOCKED,
    NotificationEvent.DOOR_HOMEPASS_UNLOCKED,
)
_LEGACY_NOTIFICATION_EVENT_IDS = (
    {event.value for event in NotificationEvent}
    - {event.value for event in _UNLOCK_NOTIFICATION_EVENTS}
) | {_LEGACY_DOOR_UNLOCKED_EVENT}


DEFAULT_NOTIFICATION_EVENTS: dict[NotificationEvent, bool] = {
    event: definition.default_enabled for event, definition in NOTIFICATION_DEFINITIONS.items()
}


class NotificationPreferencesData(TypedDict):
    """Serialized notification preference payload."""

    version: int
    enabled: bool
    selected_device_ids: list[str]
    events: dict[str, bool]


@dataclass(frozen=True, slots=True)
class NotificationPreferences:
    """Immutable installation-wide notification preferences."""

    enabled: bool
    selected_device_ids: tuple[str, ...]
    events: tuple[tuple[NotificationEvent, bool], ...]
    version: int = NOTIFICATION_PREFERENCES_VERSION

    def __post_init__(self) -> None:
        """Validate the complete preference record strictly."""
        if isinstance(self.version, bool) or self.version != NOTIFICATION_PREFERENCES_VERSION:
            raise ValueError("Unsupported notification preferences version")
        if not isinstance(self.enabled, bool):
            raise TypeError("Notification enabled preference must be a bool")
        if (
            not isinstance(self.selected_device_ids, tuple)
            or len(self.selected_device_ids) > MAX_NOTIFICATION_DEVICES
            or len(set(self.selected_device_ids)) != len(self.selected_device_ids)
            or any(
                not isinstance(identifier, str) or _DEVICE_ID_PATTERN.fullmatch(identifier) is None
                for identifier in self.selected_device_ids
            )
        ):
            raise ValueError("Notification device selections are invalid")
        if not isinstance(self.events, tuple):
            raise TypeError("Notification event preferences must be a tuple")
        event_map: dict[NotificationEvent, bool] = {}
        for item in self.events:
            if (
                not isinstance(item, tuple)
                or len(item) != 2
                or not isinstance(item[0], NotificationEvent)
                or not isinstance(item[1], bool)
                or item[0] in event_map
            ):
                raise ValueError("Notification event preferences are invalid")
            event_map[item[0]] = item[1]
        if set(event_map) != set(NotificationEvent):
            raise ValueError("Notification event preferences must contain every event")
        if tuple(event_map) != tuple(NotificationEvent):
            raise ValueError("Notification event preferences must use canonical order")

    @classmethod
    def defaults(
        cls,
        selected_device_ids: tuple[str, ...] = (),
    ) -> NotificationPreferences:
        """Create homeowner-friendly defaults with discovered devices selected."""
        return cls(
            True,
            tuple(sorted(selected_device_ids)),
            tuple(DEFAULT_NOTIFICATION_EVENTS.items()),
        )

    @classmethod
    def from_dict(cls, data: object) -> NotificationPreferences:
        """Deserialize one strict, independently versioned preference record."""
        if not isinstance(data, dict) or set(data) != {
            "version",
            "enabled",
            "selected_device_ids",
            "events",
        }:
            raise ValueError("Notification preferences contain unexpected fields")
        raw_devices = data["selected_device_ids"]
        raw_events = data["events"]
        version = data["version"]
        enabled = data["enabled"]
        if (
            isinstance(version, bool)
            or not isinstance(version, int)
            or not isinstance(enabled, bool)
            or not isinstance(raw_devices, list)
            or not all(isinstance(identifier, str) for identifier in raw_devices)
            or not isinstance(raw_events, dict)
            or not all(isinstance(key, str) for key in raw_events)
        ):
            raise ValueError("Notification preferences contain invalid collections")
        if set(raw_events) != {event.value for event in NotificationEvent}:
            raise ValueError("Notification preferences contain an unsupported event")
        events = tuple((event, raw_events[event.value]) for event in NotificationEvent)
        return cls(
            enabled,
            tuple(raw_devices),
            events,
            version,
        )

    @classmethod
    def migrate_dict(cls, data: object) -> NotificationPreferences:
        """Migrate legacy unlock choices and repair deterministic missing fields."""
        if not isinstance(data, dict):
            raise ValueError("Notification preferences must be an object")
        expected = {"version", "enabled", "selected_device_ids", "events"}
        if not set(data) <= expected:
            raise ValueError("Notification preferences contain unexpected fields")

        version = data.get("version", 1)
        enabled = data.get("enabled", True)
        raw_devices = data.get("selected_device_ids", [])
        raw_events = data.get("events", {})
        if (
            isinstance(version, bool)
            or not isinstance(version, int)
            or not isinstance(enabled, bool)
            or not isinstance(raw_devices, list)
            or not all(isinstance(identifier, str) for identifier in raw_devices)
            or not isinstance(raw_events, dict)
            or not all(isinstance(key, str) for key in raw_events)
            or version not in {1, NOTIFICATION_PREFERENCES_VERSION}
        ):
            raise ValueError("Notification preferences contain invalid collections")

        allowed_events = (
            _LEGACY_NOTIFICATION_EVENT_IDS
            if version == 1
            else {event.value for event in NotificationEvent}
        )
        if not set(raw_events) <= allowed_events:
            raise ValueError("Notification preferences contain an unsupported event")

        migrated_events = dict(raw_events)
        if version == 1:
            legacy_enabled = migrated_events.pop(_LEGACY_DOOR_UNLOCKED_EVENT, True)
            if not isinstance(legacy_enabled, bool):
                raise ValueError("Notification event preferences must be Boolean")
            for event in _UNLOCK_NOTIFICATION_EVENTS:
                migrated_events[event.value] = legacy_enabled

        events: list[tuple[NotificationEvent, bool]] = []
        for event in NotificationEvent:
            value = migrated_events.get(event.value, DEFAULT_NOTIFICATION_EVENTS[event])
            if not isinstance(value, bool):
                raise ValueError("Notification event preferences must be Boolean")
            events.append((event, value))
        return cls(enabled, tuple(raw_devices), tuple(events))

    def to_dict(self) -> NotificationPreferencesData:
        """Serialize deterministically for durable storage."""
        return {
            "version": self.version,
            "enabled": self.enabled,
            "selected_device_ids": list(self.selected_device_ids),
            "events": {event.value: self.event_enabled(event) for event in NotificationEvent},
        }

    def event_enabled(self, event: NotificationEvent) -> bool:
        """Return the stored preference for one known event."""
        return dict(self.events)[event]


__all__ = [
    "DEFAULT_NOTIFICATION_EVENTS",
    "MAX_NOTIFICATION_DEVICES",
    "NOTIFICATION_PREFERENCES_VERSION",
    "NotificationEvent",
    "NotificationPreferences",
    "NotificationPreferencesData",
]
