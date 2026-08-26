"""Activity-driven notification formatting and delivery."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Protocol

from homeassistant.components.notify.const import (
    ATTR_MESSAGE,
    ATTR_TITLE,
    SERVICE_SEND_MESSAGE,
)
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant

from ..models import (
    NOTIFICATION_DEFINITIONS,
    ActivityActorType,
    ActivityEvent,
    LockEventOrigin,
    NotificationDefinition,
    NotificationEvent,
    notification_event_for_activity,
)
from ..notification_discovery import NotificationDevice
from .notification_preferences import NotificationPreferencesService

_LOGGER = logging.getLogger(__name__)
_NOTIFY_DOMAIN = "notify"


@dataclass(frozen=True, slots=True)
class NotificationMessage:
    """One sanitized delivery-channel-neutral notification."""

    title: str
    message: str
    icon: str | None


class NotificationDeliveryChannel(Protocol):
    """Deliver one notification without coupling Activity to a provider."""

    async def deliver(
        self,
        device: NotificationDevice,
        notification: NotificationMessage,
    ) -> None: ...


class HomeAssistantCompanionNotificationChannel:
    """Deliver through current Home Assistant Companion notify entities."""

    def __init__(self, hass: HomeAssistant) -> None:
        self._hass = hass

    async def deliver(
        self,
        device: NotificationDevice,
        notification: NotificationMessage,
    ) -> None:
        if device.target is None:
            raise ValueError("Notification device is no longer available")
        await self._hass.services.async_call(
            _NOTIFY_DOMAIN,
            SERVICE_SEND_MESSAGE,
            {
                ATTR_TITLE: notification.title,
                ATTR_MESSAGE: notification.message,
            },
            blocking=True,
            target={ATTR_ENTITY_ID: device.target},
        )


class NotificationEngine:
    """Translate newly persisted Activity facts into opted-in deliveries."""

    def __init__(
        self,
        preferences: NotificationPreferencesService,
        channel: NotificationDeliveryChannel,
    ) -> None:
        self._preferences = preferences
        self._channel = channel

    async def activity_recorded(self, activity: ActivityEvent) -> None:
        """Deliver at most one registry notification for one persisted Activity fact."""
        notification_event = notification_event_for_activity(activity)
        if notification_event is None:
            return
        definition = NOTIFICATION_DEFINITIONS[notification_event]
        if not definition.supported:
            return
        settings = await self._preferences.load()
        preferences = settings.preferences
        if not preferences.enabled or not preferences.event_enabled(notification_event):
            return
        selected = set(preferences.selected_device_ids)
        devices = tuple(device for device in settings.devices if device.identifier in selected)
        if not devices:
            return
        notification = format_notification(activity, definition)
        for device in devices:
            try:
                await self._channel.deliver(device, notification)
            except Exception:  # noqa: BLE001 - one device cannot block another
                _LOGGER.warning(
                    "HomePASS notification delivery failed for Companion device %s",
                    device.display_name,
                )


def format_notification(
    activity: ActivityEvent,
    definition: NotificationDefinition,
) -> NotificationMessage:
    """Format safe concise copy exclusively from canonical Activity snapshots."""
    door = activity.door_name or "Door"
    person = activity.person_name or "User"
    battery_percentage = activity.attributes.get("battery_percentage")
    battery_suffix = (
        f" ({battery_percentage}%)" if isinstance(battery_percentage, int) else ""
    )
    event = definition.event
    messages = {
        NotificationEvent.DOOR_PIN_UNLOCKED: (
            f"{activity.actor_name} unlocked {door} with a PIN."
            if activity.actor_type is ActivityActorType.PERSON and activity.actor_name is not None
            else f"{door} was unlocked with a PIN."
        ),
        NotificationEvent.DOOR_THUMBTURN_UNLOCKED: f"{door} was unlocked from inside.",
        NotificationEvent.DOOR_HOMEPASS_UNLOCKED: (
            f"{activity.actor_name} unlocked {door} by NFC."
            if activity.lock_origin is LockEventOrigin.NFC_PASSKEY
            and activity.actor_type is ActivityActorType.PERSON
            and activity.actor_name is not None
            else f"{door} was unlocked with HomePASS NFC."
            if activity.lock_origin is LockEventOrigin.NFC_PASSKEY
            else f"{activity.actor_name} unlocked {door} using HomePASS."
            if activity.actor_type is ActivityActorType.PERSON and activity.actor_name is not None
            else f"{door} was unlocked using HomePASS."
        ),
        NotificationEvent.DOOR_LOCKED: f"{door} was locked.",
        NotificationEvent.DOOR_OPENED: f"{door} was opened.",
        NotificationEvent.DOOR_CLOSED: f"{door} was closed.",
        NotificationEvent.DOOR_LEFT_OPEN: f"{door} has been left open.",
        NotificationEvent.USER_ADDED: f"{person} was added.",
        NotificationEvent.USER_REMOVED: f"{person} was removed.",
        NotificationEvent.PIN_CREATED: f"PIN created for {person}.",
        NotificationEvent.PIN_CHANGED: f"PIN changed for {person}.",
        NotificationEvent.PIN_DELETED: f"PIN deleted for {person}.",
        NotificationEvent.ACCESS_GRANTED: f"{door} access granted to {person}.",
        NotificationEvent.ACCESS_REVOKED: f"{door} access revoked from {person}.",
        NotificationEvent.SCHEDULE_CHANGED: f"Schedule changed for {person}.",
        NotificationEvent.ACCESS_EXPIRES_SOON: f"{person}'s access to {door} expires soon.",
        NotificationEvent.ACCESS_EXPIRED: f"{person}'s access to {door} has expired.",
        NotificationEvent.PIN_SYNCHRONIZED: f"{person} PIN synchronized with {door}.",
        NotificationEvent.PIN_VERIFICATION_PENDING: (
            f"PIN verification pending for {person} at {door}."
        ),
        NotificationEvent.PIN_SYNCHRONIZATION_FAILED: (
            f"Unable to synchronize {person} with {door}."
        ),
        NotificationEvent.SYNCHRONIZATION_RECOVERED: (
            f"Synchronization recovered for {person} at {door}."
        ),
        NotificationEvent.DOOR_OFFLINE: f"{door} is offline.",
        NotificationEvent.DOOR_BACK_ONLINE: f"{door} is back online.",
        NotificationEvent.BATTERY_LOW: f"{door} battery is low{battery_suffix}.",
        NotificationEvent.BATTERY_CRITICAL: (
            f"{door} battery is critically low{battery_suffix}."
        ),
        NotificationEvent.UNKNOWN_PIN_ATTEMPT: f"Unknown PIN entered at {door}.",
        NotificationEvent.REPEATED_INVALID_PIN_ATTEMPTS: (
            f"Repeated invalid PIN attempts at {door}."
        ),
        NotificationEvent.LOCK_TAMPER: f"Tamper detection was reported at {door}.",
    }
    return NotificationMessage(definition.title, messages[event], definition.icon)


__all__ = [
    "HomeAssistantCompanionNotificationChannel",
    "NotificationDeliveryChannel",
    "NotificationEngine",
    "NotificationMessage",
    "format_notification",
]

