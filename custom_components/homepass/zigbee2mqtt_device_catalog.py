"""Sanitized parsing for the retained Zigbee2MQTT device catalog."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Zigbee2MqttCatalogDevice:
    """Non-secret identity needed to bind one supported keypad."""

    ieee_address: str
    friendly_name: str
    manufacturer: str
    model: str
    available: bool


def _normalize_ieee(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    compact = value.strip().lower().removeprefix("0x")
    compact = compact.replace(":", "").replace("-", "")
    if len(compact) != 16 or any(character not in "0123456789abcdef" for character in compact):
        return None
    return f"0x{compact}"


def parse_zigbee2mqtt_device_catalog(payload: str) -> tuple[Zigbee2MqttCatalogDevice, ...]:
    """Return only complete supported-keypad records from a bridge/devices payload."""
    if not isinstance(payload, str) or len(payload) > 2_000_000:
        return ()
    try:
        raw = json.loads(payload)
    except TypeError, ValueError:
        return ()
    if not isinstance(raw, list):
        return ()

    devices: list[Zigbee2MqttCatalogDevice] = []
    for item in raw:
        if not isinstance(item, Mapping):
            continue
        definition = item.get("definition")
        if not isinstance(definition, Mapping):
            continue
        manufacturer = definition.get("vendor")
        model = definition.get("model")
        friendly_name = item.get("friendly_name")
        ieee_address = _normalize_ieee(item.get("ieee_address"))
        if (
            not isinstance(manufacturer, str)
            or not isinstance(model, str)
            or not isinstance(friendly_name, str)
            or ieee_address is None
        ):
            continue
        normalized_manufacturer = manufacturer.casefold()
        normalized_model = model.casefold().replace(" ", "")
        normalized_friendly_name = friendly_name.strip().strip("/")
        if (
            not ("frient" in normalized_manufacturer or "develco" in normalized_manufacturer)
            or normalized_model not in {"kepzb-110", "keyzb-110"}
            or not normalized_friendly_name
            or len(normalized_friendly_name) > 255
            or "+" in normalized_friendly_name
            or "#" in normalized_friendly_name
            or "\x00" in normalized_friendly_name
        ):
            continue
        devices.append(
            Zigbee2MqttCatalogDevice(
                ieee_address=ieee_address,
                friendly_name=normalized_friendly_name,
                manufacturer=manufacturer.strip() or "Develco",
                model=model.strip() or "KEYZB-110",
                available=(
                    item.get("disabled") is False and item.get("interview_state") == "SUCCESSFUL"
                ),
            )
        )
    return tuple(sorted(devices, key=lambda item: item.ieee_address))


__all__ = ["Zigbee2MqttCatalogDevice", "parse_zigbee2mqtt_device_catalog"]
