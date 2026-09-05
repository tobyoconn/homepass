"""Discover supported Home Assistant devices without owning their pairing."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .battery import resolve_device_battery
from .models import AccessDeviceIntegration, AccessDeviceKind

if TYPE_CHECKING:
    from collections.abc import Collection

    from homeassistant.core import HomeAssistant


@dataclass(frozen=True, slots=True)
class DiscoveredAccessDevice:
    """Presentation-safe compatible Home Assistant device."""

    home_assistant_device_id: str
    display_name: str
    manufacturer: str
    model: str
    kind: AccessDeviceKind
    integration: AccessDeviceIntegration
    available: bool
    battery_percentage: int | None = None
    battery_status: str | None = None
    battery_entity_id: str | None = None
    zigbee_ieee_address: str | None = None
    zigbee2mqtt_base_topic: str | None = None
    zigbee2mqtt_friendly_name: str | None = None

    def to_dict(self) -> dict[str, object]:
        data: dict[str, object] = {
            "home_assistant_device_id": self.home_assistant_device_id,
            "display_name": self.display_name,
            "manufacturer": self.manufacturer,
            "model": self.model,
            "kind": self.kind.value,
            "integration": self.integration.value,
            "available": self.available,
            "zigbee_ieee_address": self.zigbee_ieee_address,
            "zigbee2mqtt_base_topic": self.zigbee2mqtt_base_topic,
            "zigbee2mqtt_friendly_name": self.zigbee2mqtt_friendly_name,
        }
        if self.battery_percentage is not None:
            data["battery_percentage"] = self.battery_percentage
        if self.battery_status is not None:
            data["battery_status"] = self.battery_status
        if self.battery_entity_id is not None:
            data["battery_entity_id"] = self.battery_entity_id
        return data


class HomeAssistantAccessDeviceDiscovery:
    """Find explicitly supported accessories already paired with Home Assistant."""

    def __init__(self, hass: HomeAssistant) -> None:
        self._hass = hass

    async def discover_supported(self) -> tuple[DiscoveredAccessDevice, ...]:
        device_registry = dr.async_get(self._hass)
        entity_registry = er.async_get(self._hass)
        discovered: list[DiscoveredAccessDevice] = []
        for device in device_registry.devices.values():
            manufacturer = (device.manufacturer or "").strip()
            model = (device.model or "").strip()
            model_id = (getattr(device, "model_id", None) or "").strip()
            all_entities = tuple(
                entry for entry in entity_registry.entities.values() if entry.device_id == device.id
            )
            entities = tuple(entry for entry in all_entities if entry.disabled_by is None)
            available = any(
                (state := self._hass.states.get(entry.entity_id)) is not None
                and state.state not in {"unavailable", "unknown"}
                for entry in entities
            )
            battery = resolve_device_battery(self._hass, device.id)
            if _is_supported_zha_frient_keypad(
                manufacturer,
                model,
                device.identifiers,
            ):
                discovered.append(
                    DiscoveredAccessDevice(
                        home_assistant_device_id=device.id,
                        display_name=(
                            device.name_by_user or device.name or "Frient keypad"
                        ).strip(),
                        manufacturer=manufacturer or "frient",
                        model=model or "KEPZB-110",
                        kind=AccessDeviceKind.KEYPAD,
                        integration=AccessDeviceIntegration.ZHA,
                        available=available,
                        battery_percentage=(battery.percentage if battery is not None else None),
                        battery_status=battery.status.value if battery is not None else None,
                        battery_entity_id=battery.entity_id if battery is not None else None,
                    )
                )
                continue

            ieee_address = _zigbee2mqtt_ieee_address(device.identifiers)
            friendly_name = (device.name or "").strip().strip("/")
            if not _is_supported_zigbee2mqtt_frient_keypad(
                manufacturer,
                model,
                model_id,
                ieee_address,
                friendly_name,
                all_entities,
            ):
                continue
            discovered.append(
                DiscoveredAccessDevice(
                    home_assistant_device_id=device.id,
                    display_name=(device.name_by_user or device.name or friendly_name).strip(),
                    manufacturer=manufacturer or "Develco",
                    model=model or "Keypad",
                    kind=AccessDeviceKind.KEYPAD,
                    integration=AccessDeviceIntegration.ZIGBEE2MQTT,
                    available=available,
                    battery_percentage=battery.percentage if battery is not None else None,
                    battery_status=battery.status.value if battery is not None else None,
                    battery_entity_id=battery.entity_id if battery is not None else None,
                    zigbee_ieee_address=ieee_address,
                    zigbee2mqtt_base_topic="zigbee2mqtt",
                    zigbee2mqtt_friendly_name=friendly_name,
                )
            )
        return tuple(
            sorted(
                discovered,
                key=lambda item: (item.display_name.casefold(), item.home_assistant_device_id),
            )
        )


def _is_supported_zha_frient_keypad(
    manufacturer: str,
    model: str,
    identifiers: Collection[tuple[str, str]],
) -> bool:
    integration_domains = {domain.casefold() for domain, _identifier in identifiers}
    normalized_manufacturer = manufacturer.casefold()
    normalized_model = model.casefold().replace(" ", "")
    return (
        "zha" in integration_domains
        and ("frient" in normalized_manufacturer or "develco" in normalized_manufacturer)
        and "kepzb-110" in normalized_model
    )


def _zigbee2mqtt_ieee_address(
    identifiers: Collection[tuple[str, str]],
) -> str | None:
    """Extract only the MQTT identifier shape observed from Zigbee2MQTT discovery."""
    candidates: set[str] = set()
    for domain, identifier in identifiers:
        if domain.casefold() != "mqtt" or not identifier.casefold().startswith("zigbee2mqtt_"):
            continue
        compact = identifier[len("zigbee2mqtt_") :].strip().lower().removeprefix("0x")
        compact = compact.replace(":", "").replace("-", "")
        if len(compact) == 16 and all(character in "0123456789abcdef" for character in compact):
            candidates.add(f"0x{compact}")
    return next(iter(candidates)) if len(candidates) == 1 else None


def _is_supported_zigbee2mqtt_frient_keypad(
    manufacturer: str,
    model: str,
    model_id: str,
    ieee_address: str | None,
    friendly_name: str,
    entities: Collection[object],
) -> bool:
    """Match the registry shape emitted for a Develco/Frient KEYZB-110."""
    normalized_manufacturer = manufacturer.casefold()
    normalized_model = model.casefold().replace(" ", "")
    normalized_model_id = model_id.casefold().replace(" ", "")
    entity_names = {
        str(getattr(entity, "original_name", "")).casefold()
        for entity in entities
        if str(getattr(entity, "platform", "")).casefold() == "mqtt"
    }
    return (
        ieee_address is not None
        and ("frient" in normalized_manufacturer or "develco" in normalized_manufacturer)
        and (
            normalized_model_id in {"kepzb-110", "keyzb-110"}
            or normalized_model in {"kepzb-110", "keyzb-110"}
        )
        and entity_names.issuperset({"action code", "action transaction", "action zone"})
        and bool(friendly_name)
        and len(friendly_name) <= 255
        and not any(character in friendly_name for character in ("+", "#", "\x00"))
    )


__all__ = ["DiscoveredAccessDevice", "HomeAssistantAccessDeviceDiscovery"]
