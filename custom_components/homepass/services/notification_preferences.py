"""Application service for notification settings without notification delivery."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import TypedDict

from ..models.notification import CATEGORY_TITLES, NOTIFICATION_DEFINITIONS
from ..models.notification_preferences import (
    NOTIFICATION_PREFERENCES_VERSION,
    NotificationPreferences,
)
from ..notification_discovery import NotificationDevice, NotificationDeviceDiscovery
from ..repositories.notification_preferences import NotificationPreferencesRepository


class NotificationDevicePresentationData(TypedDict):
    """Presentation-safe discovered notification device."""

    id: str
    display_name: str
    selected: bool
    available: bool


class NotificationPreferencesPresentationData(TypedDict):
    """Presentation-safe notification preferences."""

    enabled: bool
    selected_device_ids: list[str]
    events: dict[str, bool]


class NotificationDefinitionPresentationData(TypedDict):
    """One shared registry definition safe for Settings rendering."""

    id: str
    category: str
    category_title: str
    title: str
    default_enabled: bool
    supported: bool


class NotificationSettingsData(TypedDict):
    """Complete Settings action response."""

    preferences: NotificationPreferencesPresentationData
    devices: list[NotificationDevicePresentationData]
    definitions: list[NotificationDefinitionPresentationData]
    event_support: dict[str, bool]


@dataclass(frozen=True, slots=True)
class NotificationSettings:
    """Complete immutable Settings presentation."""

    preferences: NotificationPreferences
    devices: tuple[NotificationDevice, ...]

    def to_dict(self) -> NotificationSettingsData:
        selected = set(self.preferences.selected_device_ids)
        discovered = {device.identifier for device in self.devices}
        device_presentations: list[NotificationDevicePresentationData] = [
            {
                "id": device.identifier,
                "display_name": device.display_name,
                "selected": device.identifier in selected,
                "available": True,
            }
            for device in self.devices
        ]
        unavailable = sorted(selected - discovered)
        for index, identifier in enumerate(unavailable, start=1):
            suffix = f" {index}" if len(unavailable) > 1 else ""
            device_presentations.append(
                {
                    "id": identifier,
                    "display_name": f"Previously selected Companion device{suffix}",
                    "selected": True,
                    "available": False,
                }
            )
        return {
            "preferences": {
                "enabled": self.preferences.enabled,
                "selected_device_ids": list(self.preferences.selected_device_ids),
                "events": {event.value: enabled for event, enabled in self.preferences.events},
            },
            "devices": device_presentations,
            "definitions": [
                {
                    "id": definition.event.value,
                    "category": definition.category.value,
                    "category_title": CATEGORY_TITLES[definition.category],
                    "title": definition.title,
                    "default_enabled": definition.default_enabled,
                    "supported": definition.supported,
                }
                for definition in NOTIFICATION_DEFINITIONS.values()
            ],
            "event_support": {
                definition.event.value: definition.supported
                for definition in NOTIFICATION_DEFINITIONS.values()
            },
        }


class NotificationPreferencesService:
    """Own validation, discovery, initialization, and persistence of preferences."""

    def __init__(
        self,
        repository: NotificationPreferencesRepository,
        discovery: NotificationDeviceDiscovery,
    ) -> None:
        self._repository = repository
        self._discovery = discovery
        self._preferences: NotificationPreferences | None = None
        self._lock = asyncio.Lock()

    async def initialize(self) -> NotificationPreferences:
        """Restore durable preferences once before notification delivery is available."""
        async with self._lock:
            return await self._initialize_locked()

    async def _initialize_locked(
        self,
        devices: tuple[NotificationDevice, ...] | None = None,
    ) -> NotificationPreferences:
        """Load or create preferences while the service initialization lock is held."""
        if self._preferences is not None:
            return self._preferences
        preferences = await self._repository.get()
        if preferences is None:
            if devices is None:
                devices = await self._discovery.async_discover()
            preferences = await self._repository.save(
                NotificationPreferences.defaults(tuple(device.identifier for device in devices))
            )
        self._preferences = preferences
        return preferences

    async def load(self) -> NotificationSettings:
        """Return restored preferences and a separate current device discovery view."""
        preferences = await self.initialize()
        devices = await self._discovery.async_discover()
        return NotificationSettings(preferences, devices)

    async def save(self, raw_preferences: object) -> NotificationSettings:
        """Validate and persist a complete preference document, then rediscover names."""
        async with self._lock:
            devices = await self._discovery.async_discover()
            current = await self._initialize_locked(devices)
            preferences = self._parse_action_preferences(raw_preferences)
            known = {device.identifier for device in devices} | set(current.selected_device_ids)
            if not set(preferences.selected_device_ids) <= known:
                raise ValueError("Notification device selection is not recognized")
            saved = await self._repository.save(preferences)
            self._preferences = saved
        return NotificationSettings(saved, devices)

    @staticmethod
    def _parse_action_preferences(raw: object) -> NotificationPreferences:
        """Parse the action shape while preserving the durable schema version internally."""
        if not isinstance(raw, dict) or set(raw) != {
            "enabled",
            "selected_device_ids",
            "events",
        }:
            raise ValueError("Notification preferences are invalid")
        return NotificationPreferences.from_dict(
            {
                "version": NOTIFICATION_PREFERENCES_VERSION,
                "enabled": raw["enabled"],
                "selected_device_ids": raw["selected_device_ids"],
                "events": raw["events"],
            }
        )


__all__ = [
    "NotificationPreferencesService",
    "NotificationSettings",
    "NotificationSettingsData",
]
