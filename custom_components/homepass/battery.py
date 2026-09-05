"""Home Assistant battery discovery and truthful level normalization."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

from homeassistant.const import (
    ATTR_DEVICE_CLASS,
    STATE_OFF,
    STATE_ON,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.helpers import entity_registry as er

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_BATTERY_DEVICE_CLASS = "battery"
_BATTERY_ATTRIBUTES = ("battery_level", "battery_percentage", "battery")
LOW_BATTERY_PERCENTAGE = 30
CRITICAL_BATTERY_PERCENTAGE = 10


class BatteryStatus(StrEnum):
    """Normalized battery state independent of the source integration."""

    NORMAL = "normal"
    LOW = "low"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class BatteryReading:
    """One sanitized battery reading and the entity that updates it."""

    entity_id: str
    percentage: int | None
    status: BatteryStatus


def status_for_percentage(percentage: int) -> BatteryStatus:
    """Classify a validated whole percentage using HomePASS thresholds."""
    if (
        not isinstance(percentage, int)
        or isinstance(percentage, bool)
        or not 0 <= percentage <= 100
    ):
        raise ValueError("Battery percentage must be between 0 and 100")
    if percentage <= CRITICAL_BATTERY_PERCENTAGE:
        return BatteryStatus.CRITICAL
    if percentage <= LOW_BATTERY_PERCENTAGE:
        return BatteryStatus.LOW
    return BatteryStatus.NORMAL


def resolve_entity_battery(hass: HomeAssistant, entity_id: str) -> BatteryReading | None:
    """Resolve a battery entity or battery attribute associated with one HA entity."""
    registry = er.async_get(hass)
    entry = registry.async_get(entity_id)
    if entry is not None and entry.device_id is not None:
        device_reading = resolve_device_battery(hass, entry.device_id)
        if device_reading is not None:
            return device_reading
    return read_battery_source(hass, entity_id, allow_attributes=True)


def resolve_device_battery(hass: HomeAssistant, device_id: str) -> BatteryReading | None:
    """Choose the best enabled standard battery entity for one HA device."""
    registry = er.async_get(hass)
    candidates: list[tuple[tuple[int, int, str], BatteryReading]] = []
    for entry in er.async_entries_for_device(registry, device_id):
        if entry.disabled_by is not None or entry.domain not in {"sensor", "binary_sensor"}:
            continue
        state = hass.states.get(entry.entity_id)
        device_class = entry.device_class or entry.original_device_class
        if device_class is None and state is not None:
            device_class = state.attributes.get(ATTR_DEVICE_CLASS)
        if device_class != _BATTERY_DEVICE_CLASS:
            continue
        reading = read_battery_source(hass, entry.entity_id)
        if reading is None:
            reading = BatteryReading(entry.entity_id, None, BatteryStatus.UNKNOWN)
        candidates.append(
            (
                (
                    0 if reading.percentage is not None else 1,
                    0 if reading.status is not BatteryStatus.UNKNOWN else 1,
                    entry.entity_id,
                ),
                reading,
            )
        )
    return min(candidates, key=lambda item: item[0])[1] if candidates else None


def read_battery_source(
    hass: HomeAssistant,
    entity_id: str,
    *,
    allow_attributes: bool = False,
) -> BatteryReading | None:
    """Read one previously selected source without inferring a different device."""
    state = hass.states.get(entity_id)
    if state is None:
        return None
    registry = er.async_get(hass)
    entry = registry.async_get(entity_id)
    device_class = (
        (entry.device_class or entry.original_device_class) if entry is not None else None
    ) or state.attributes.get(ATTR_DEVICE_CLASS)
    if device_class == _BATTERY_DEVICE_CLASS:
        if entity_id.startswith("binary_sensor."):
            if state.state == STATE_ON:
                return BatteryReading(entity_id, None, BatteryStatus.LOW)
            if state.state == STATE_OFF:
                return BatteryReading(entity_id, None, BatteryStatus.NORMAL)
            return BatteryReading(entity_id, None, BatteryStatus.UNKNOWN)
        percentage = _percentage(state.state)
        return BatteryReading(
            entity_id,
            percentage,
            status_for_percentage(percentage) if percentage is not None else BatteryStatus.UNKNOWN,
        )
    if not allow_attributes:
        return None
    for attribute in _BATTERY_ATTRIBUTES:
        percentage = _percentage(state.attributes.get(attribute))
        if percentage is not None:
            return BatteryReading(entity_id, percentage, status_for_percentage(percentage))
    return None


def _percentage(value: object) -> int | None:
    if (
        value is None
        or value == ""
        or value in (STATE_UNKNOWN, STATE_UNAVAILABLE)
        or isinstance(value, bool)
    ):
        return None
    try:
        numeric = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    if not 0 <= numeric <= 100:
        return None
    return int(numeric + 0.5)


__all__ = [
    "CRITICAL_BATTERY_PERCENTAGE",
    "LOW_BATTERY_PERCENTAGE",
    "BatteryReading",
    "BatteryStatus",
    "read_battery_source",
    "resolve_device_battery",
    "resolve_entity_battery",
    "status_for_percentage",
]
