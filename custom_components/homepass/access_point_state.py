"""Home Assistant adapter for truthful Access Point operational state."""

from datetime import datetime
from collections.abc import Awaitable, Callable
from homeassistant.components.lock import LockEntityFeature
from typing import Final

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.const import (
    ATTR_DEVICE_CLASS,
    STATE_OFF,
    STATE_ON,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .battery import resolve_entity_battery
from .services import (
    AccessPointAvailability,
    AccessPointState,
    AccessPointTarget,
)

_KNOWN_LOCK_STATES = frozenset(
    {"jammed", "locked", "locking", "open", "opening", "unlocked", "unlocking"}
)
_CONTACT_DEVICE_CLASSES = frozenset(
    {BinarySensorDeviceClass.DOOR.value, BinarySensorDeviceClass.OPENING.value}
)
_CURRENT_DOOR_STATUS_MARKERS: Final = (
    "current_door_status",
    "door_status",
    "doorsense",
)


class HomeAssistantAccessPointStateResolver:
    """Project current lock and same-device contact state without leaking identifiers."""

    def __init__(
        self,
        hass: HomeAssistant,
        *,
        nuki_entity_id: str | None = None,
        nuki_entry_recommendation: Callable[[], Awaitable[str | None]] | None = None,
    ) -> None:
        """Initialize the Home Assistant state adapter."""
        self._hass = hass
        self._nuki_entity_id = nuki_entity_id
        self._nuki_entry_recommendation = nuki_entry_recommendation

    async def resolve_state(self, target: AccessPointTarget) -> AccessPointState:
        """Resolve known lock, availability, and associated contact states."""
        lock = self._hass.states.get(target.lock_entity_id)
        features = lock.attributes.get("supported_features", 0) if lock is not None else 0
        supports_open = (
            target.control_profile == "lock"
            and isinstance(features, int)
            and not isinstance(features, bool)
            and bool(features & LockEntityFeature.OPEN)
        )
        recommendation = None
        if (
            supports_open
            and target.lock_entity_id == self._nuki_entity_id
            and self._nuki_entry_recommendation
        ):
            recommendation = await self._nuki_entry_recommendation()
        if target.status_entity_id is not None:
            door_state, door_entity_id, door_last_updated = self._resolve_explicit_status(
                target.status_entity_id, target.status_inverted
            )
        else:
            door_state, door_entity_id, door_last_updated = self._resolve_contact_state(
                target.lock_entity_id
            )
        battery = resolve_entity_battery(self._hass, target.lock_entity_id)
        door_sensor_battery = (
            resolve_entity_battery(self._hass, door_entity_id)
            if door_entity_id is not None
            else None
        )
        if (
            battery is not None
            and door_sensor_battery is not None
            and battery.entity_id == door_sensor_battery.entity_id
        ):
            door_sensor_battery = None
        timestamps = [
            timestamp
            for timestamp in (lock.last_updated if lock is not None else None, door_last_updated)
            if timestamp is not None
        ]
        last_updated = max(timestamps) if timestamps else None

        def resolved_state(
            availability: AccessPointAvailability,
            lock_state: str | None = None,
        ) -> AccessPointState:
            return AccessPointState(
                availability,
                lock_state=lock_state,
                supports_open=supports_open,
                recommended_entry_action=recommendation,
                door_state=door_state,
                last_updated=last_updated,
                lock_entity_id=target.lock_entity_id,
                door_entity_id=door_entity_id,
                battery_percentage=battery.percentage if battery is not None else None,
                battery_status=battery.status.value if battery is not None else None,
                battery_entity_id=battery.entity_id if battery is not None else None,
                door_sensor_battery_percentage=(
                    door_sensor_battery.percentage if door_sensor_battery is not None else None
                ),
                door_sensor_battery_status=(
                    door_sensor_battery.status.value if door_sensor_battery is not None else None
                ),
                door_sensor_battery_entity_id=(
                    door_sensor_battery.entity_id if door_sensor_battery is not None else None
                ),
            )

        if lock is None or lock.state == STATE_UNKNOWN:
            return resolved_state(AccessPointAvailability.UNKNOWN)
        if lock.state == STATE_UNAVAILABLE:
            return resolved_state(AccessPointAvailability.UNAVAILABLE)
        if lock.state == AccessPointAvailability.OFFLINE.value:
            return resolved_state(AccessPointAvailability.OFFLINE)

        lock_state = self._control_state(target, lock.state, door_state)
        return resolved_state(AccessPointAvailability.AVAILABLE, lock_state)

    @staticmethod
    def _control_state(
        target: AccessPointTarget, raw_state: str, door_state: str | None
    ) -> str | None:
        """Normalize capability-based controls into the existing stable-state contract."""
        if target.control_profile == "lock":
            return raw_state if raw_state in _KNOWN_LOCK_STATES else None
        if target.control_profile == "garage_cover":
            return {
                "closed": "locked",
                "closing": "locking",
                "open": "unlocked",
                "opening": "unlocking",
            }.get(raw_state)
        if door_state == "open":
            return "unlocked"
        if door_state == "closed":
            return "locked"
        return "locked" if target.control_profile == "electric_strike" else None

    def _resolve_explicit_status(
        self, entity_id: str, inverted: bool
    ) -> tuple[str | None, str, datetime | None]:
        """Resolve an administrator-selected open/closed status entity."""
        state = self._hass.states.get(entity_id)
        if state is None:
            return None, entity_id, None
        value = state.state.casefold()
        if value in {STATE_ON, "open", "opening", "unlocked"}:
            door_state = "open"
        elif value in {STATE_OFF, "closed", "closing", "locked"}:
            door_state = "closed"
        else:
            door_state = None
        if inverted and door_state is not None:
            door_state = "closed" if door_state == "open" else "open"
        return door_state, entity_id, state.last_updated

    def _resolve_contact_state(
        self, lock_entity_id: str
    ) -> tuple[str | None, str | None, datetime | None]:
        """Return a same-device contact's truthful state, source, and update time."""
        entity_id = self.resolve_contact_entity_id(lock_entity_id)
        if entity_id is None:
            return None, None, None
        state = self._hass.states.get(entity_id)
        if state is None:
            return None, entity_id, None
        if state.state == STATE_ON:
            return "open", entity_id, state.last_updated
        if state.state == STATE_OFF:
            return "closed", entity_id, state.last_updated
        return None, entity_id, state.last_updated

    def resolve_contact_entity_id(self, lock_entity_id: str) -> str | None:
        """Select one deterministic trustworthy same-device door contact."""
        registry = er.async_get(self._hass)
        lock_entry = registry.async_get(lock_entity_id)
        if lock_entry is None or lock_entry.device_id is None:
            return None

        candidates: list[tuple[tuple[int, int, int, int, str], str]] = []
        for entry in er.async_entries_for_device(registry, lock_entry.device_id):
            if entry.domain != "binary_sensor" or entry.disabled_by is not None:
                continue
            state = self._hass.states.get(entry.entity_id)
            device_class = (
                entry.device_class
                or (state.attributes.get(ATTR_DEVICE_CLASS) if state is not None else None)
                or entry.original_device_class
            )
            if device_class not in _CONTACT_DEVICE_CLASSES:
                continue
            identity = " ".join(
                value
                for value in (
                    entry.entity_id,
                    entry.unique_id,
                    entry.name,
                    entry.original_name,
                    entry.translation_key,
                )
                if value
            ).casefold()
            candidates.append(
                (
                    (
                        0 if entry.hidden_by is None else 1,
                        0 if device_class == BinarySensorDeviceClass.DOOR.value else 1,
                        0
                        if any(marker in identity for marker in _CURRENT_DOOR_STATUS_MARKERS)
                        else 1,
                        0 if state is not None and state.state in {STATE_ON, STATE_OFF} else 1,
                        entry.entity_id,
                    ),
                    entry.entity_id,
                )
            )
        return min(candidates)[1] if candidates else None
