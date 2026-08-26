"""Home Assistant registry adapter for Access Point display names."""

from homeassistant.const import ATTR_FRIENDLY_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er


def _name(value: object) -> str | None:
    """Return a non-empty normalized name."""
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None


class HomeAssistantAccessPointNameResolver:
    """Resolve device-neutral names from Home Assistant registries and state."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the registry adapter."""
        self._hass = hass

    async def resolve_name(self, lock_entity_id: str) -> str:
        """Resolve device name, entity friendly name, then a safe fallback."""
        entity_entry = er.async_get(self._hass).async_get(lock_entity_id)
        if entity_entry is not None and entity_entry.device_id is not None:
            device_entry = dr.async_get(self._hass).async_get(entity_entry.device_id)
            if device_entry is not None:
                device_name = _name(device_entry.name_by_user) or _name(device_entry.name)
                if device_name is not None:
                    return device_name

        state = self._hass.states.get(lock_entity_id)
        if state is not None:
            friendly_name = _name(state.attributes.get(ATTR_FRIENDLY_NAME))
            if friendly_name is not None:
                return friendly_name

        if entity_entry is not None:
            entity_name = _name(entity_entry.name)
            if entity_name is not None:
                return entity_name
        return "Lock"
