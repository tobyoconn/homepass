"""Home Assistant entity-registry discovery for supported Access Points."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from uuid import NAMESPACE_URL, UUID, uuid5

from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .models import AccessDriver, AccessPoint
from .services import (
    FRONT_DOOR_ACCESS_POINT,
    AccessPointTarget,
    AccessPointTargetDiscovery,
)
from .services.access_point import FRONT_DOOR_TARGET

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_registry import RegistryEntry

_LOGGER = logging.getLogger(__name__)

_ZWAVE_LOCK_PLATFORM = "zwave_js"
_MATTER_LOCK_PLATFORM = "matter"


def _stable_access_point_id(entry: RegistryEntry) -> UUID:
    """Return a stable UUID without changing the legacy built-in identity."""
    if entry.entity_id == FRONT_DOOR_TARGET.lock_entity_id:
        return FRONT_DOOR_ACCESS_POINT.id
    return uuid5(
        NAMESPACE_URL,
        f"homepass:access-point:entity-registry:{entry.id}",
    )


class HomeAssistantAccessPointDiscovery(AccessPointTargetDiscovery):
    """Reconcile supported enabled lock entities from Home Assistant's registry."""

    def __init__(
        self,
        hass: HomeAssistant,
        *,
        nuki_authorization_entity_id: str | None = None,
    ) -> None:
        """Initialize the registry adapter."""
        self._hass = hass
        self._nuki_authorization_entity_id = nuki_authorization_entity_id

    async def discover_targets(self) -> tuple[AccessPointTarget, ...]:
        """Return each supported enabled registry lock exactly once."""
        registry = er.async_get(self._hass)
        device_registry = dr.async_get(self._hass)
        registry_candidates = {
            entry.entity_id for entry in registry.entities.values() if entry.domain == "lock"
        }
        state_candidates = {state.entity_id for state in self._hass.states.async_all("lock")}

        targets: list[AccessPointTarget] = []
        for entity_id in sorted(registry_candidates | state_candidates):
            entry = registry.async_get(entity_id)
            rejection = self._rejection_reason(entry, device_registry)
            if rejection is not None:
                _LOGGER.debug(
                    "Access Point discovery candidate entity_id=%s decision=rejected reason=%s",
                    entity_id,
                    rejection,
                )
                continue

            assert entry is not None
            driver = self._driver(entry, device_registry)
            assert driver is not None
            access_point_id = _stable_access_point_id(entry)
            _LOGGER.debug(
                "Access Point discovery candidate entity_id=%s decision=accepted "
                "access_point_id=%s platform=%s hidden=%s state_present=%s",
                entity_id,
                access_point_id,
                entry.platform,
                entry.hidden_by is not None,
                entity_id in state_candidates,
            )
            targets.append(
                AccessPointTarget(
                    access_point=AccessPoint(
                        id=access_point_id,
                        display_name="Lock",
                        created_at=entry.created_at,
                        updated_at=entry.modified_at,
                    ),
                    lock_entity_id=entity_id,
                    driver=driver,
                    pin_capable=(
                        driver is AccessDriver.ZWAVE_JS
                        or (
                            driver is AccessDriver.NUKI
                            and entity_id == self._nuki_authorization_entity_id
                        )
                    ),
                    migrate_generated_display_name=True,
                    discovery_key=entry.id,
                )
            )
        return tuple(targets)

    @classmethod
    def _rejection_reason(
        cls,
        entry: RegistryEntry | None,
        device_registry: dr.DeviceRegistry,
    ) -> str | None:
        """Return the explicit compatibility rejection reason, if any."""
        if entry is None:
            return "missing_entity_registry_entry"
        if entry.disabled_by is not None:
            return f"disabled_by_{entry.disabled_by.value}"
        if entry.entity_category is not None:
            return f"entity_category_{entry.entity_category.value}"
        if entry.platform not in {_ZWAVE_LOCK_PLATFORM, _MATTER_LOCK_PLATFORM}:
            return f"unsupported_platform_{entry.platform}"
        if cls._driver(entry, device_registry) is None:
            return "unsupported_matter_lock_manufacturer"
        return None

    @staticmethod
    def _driver(
        entry: RegistryEntry,
        device_registry: dr.DeviceRegistry,
    ) -> AccessDriver | None:
        if entry.platform == _ZWAVE_LOCK_PLATFORM:
            return AccessDriver.ZWAVE_JS
        if entry.platform != _MATTER_LOCK_PLATFORM or entry.device_id is None:
            return None
        device = device_registry.async_get(entry.device_id)
        if device is None:
            return None
        manufacturer = (device.manufacturer or "").strip().casefold()
        model = (device.model or "").strip().casefold()
        if manufacturer == "nuki" and "smart lock" in model:
            return AccessDriver.NUKI
        return None
