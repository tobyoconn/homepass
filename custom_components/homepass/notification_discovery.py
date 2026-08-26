"""Read-only discovery of Home Assistant Companion App notification targets."""

from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from typing import Protocol

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er


@dataclass(frozen=True, slots=True)
class NotificationDevice:
    """One safe, stable Companion App notification destination."""

    identifier: str
    display_name: str
    target: str | None = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if not self.identifier.startswith("mobile_app:"):
            raise ValueError("Companion notification identifier is invalid")
        if not self.display_name.strip():
            raise ValueError("Companion notification name is required")
        if self.target is not None and not self.target.startswith("notify."):
            raise ValueError("Companion notification target is invalid")


class NotificationDeviceDiscovery(Protocol):
    """Discover current notification destinations without changing HA state."""

    async def async_discover(self) -> tuple[NotificationDevice, ...]: ...


class HomeAssistantNotificationDeviceDiscovery:
    """Discover notify entities created by the Home Assistant Companion integration."""

    def __init__(self, hass: HomeAssistant) -> None:
        self._hass = hass

    async def async_discover(self) -> tuple[NotificationDevice, ...]:
        """Return enabled Companion App notify entities with stable opaque IDs."""
        entity_registry = er.async_get(self._hass)
        device_registry = dr.async_get(self._hass)
        devices: dict[str, NotificationDevice] = {}
        for entry in entity_registry.entities.values():
            if (
                entry.domain != "notify"
                or entry.platform != "mobile_app"
                or entry.disabled_by is not None
            ):
                continue
            identifier = self._identifier(entry.unique_id)
            display_name = self._display_name(entry, device_registry)
            devices[identifier] = NotificationDevice(identifier, display_name, entry.entity_id)
        return tuple(
            sorted(
                devices.values(),
                key=lambda device: (device.display_name.casefold(), device.identifier),
            )
        )

    @staticmethod
    def _identifier(unique_id: str) -> str:
        """Create a stable non-rendered selection ID without exposing HA identifiers."""
        digest = sha256(unique_id.encode("utf-8")).hexdigest()[:32]
        return f"mobile_app:{digest}"

    @staticmethod
    def _display_name(
        entry: er.RegistryEntry,
        registry: dr.DeviceRegistry,
    ) -> str:
        """Resolve the latest homeowner-facing device name."""
        if entry.device_id is not None and (device := registry.async_get(entry.device_id)):
            if device.name_by_user and device.name_by_user.strip():
                return device.name_by_user.strip()
            if device.name and device.name.strip():
                return device.name.strip()
        for candidate in (entry.name, entry.original_name):
            if candidate and candidate.strip():
                return candidate.strip()
        return "Companion device"


__all__ = [
    "HomeAssistantNotificationDeviceDiscovery",
    "NotificationDevice",
    "NotificationDeviceDiscovery",
]
