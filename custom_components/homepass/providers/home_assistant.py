"""Home Assistant adapter for local lock control, including Matter locks."""

from __future__ import annotations

from homeassistant.components.lock import LockEntityFeature
from homeassistant.components.lock.const import DOMAIN as LOCK_DOMAIN
from homeassistant.const import (
    ATTR_ENTITY_ID,
    SERVICE_LOCK,
    SERVICE_UNLOCK,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import Context, HomeAssistant

from .base import LockState


class HomeAssistantLockProvider:
    """Use Home Assistant entity state and services as the local lock boundary."""

    def __init__(self, hass: HomeAssistant) -> None:
        self._hass = hass

    async def get_state(self, entity_id: str) -> LockState:
        """Return the normalized local entity state."""
        state = self._hass.states.get(entity_id)
        if state is None or state.state == STATE_UNKNOWN:
            return LockState.UNKNOWN
        if state.state == STATE_UNAVAILABLE:
            return LockState.UNAVAILABLE
        try:
            return LockState(state.state)
        except ValueError:
            return LockState.UNKNOWN

    async def lock(self, entity_id: str, *, context: object | None = None) -> None:
        """Dispatch a local Home Assistant lock command."""
        await self._call(SERVICE_LOCK, entity_id, context)

    async def unlock(self, entity_id: str, *, context: object | None = None) -> None:
        """Dispatch a local Home Assistant unlock command."""
        await self._call(SERVICE_UNLOCK, entity_id, context)

    async def open(self, entity_id: str, *, context: object | None = None) -> None:
        """Dispatch latch retraction separately from Unlock."""
        state = self._hass.states.get(entity_id)
        features = state.attributes.get("supported_features", 0) if state is not None else 0
        if (state is None or state.state in {STATE_UNKNOWN, STATE_UNAVAILABLE}
                or not isinstance(features, int) or isinstance(features, bool)
                or not features & LockEntityFeature.OPEN):
            raise ValueError("Open Door is currently unavailable")
        await self._call("open", entity_id, context)

    async def _call(self, service: str, entity_id: str, context: object | None) -> None:
        await self._hass.services.async_call(
            LOCK_DOMAIN,
            service,
            target={ATTR_ENTITY_ID: entity_id},
            blocking=True,
            context=context if isinstance(context, Context) else None,
        )
