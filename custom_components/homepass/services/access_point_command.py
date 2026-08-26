"""Shared Home Assistant command boundary for every HomePASS access method."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from homeassistant.const import (
    ATTR_ENTITY_ID,
    SERVICE_LOCK,
    SERVICE_UNLOCK,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)

from ..models import LockEventOrigin
from ..providers.home_assistant import HomeAssistantLockProvider
from .access_point import (
    AccessPointAvailability,
    AccessPointService,
    AccessPointTarget,
)
from .lock_event_correlation import (
    LockCommandCorrelationError,
    LockCommandCorrelationService,
    LockStableState,
)

if TYPE_CHECKING:
    from homeassistant.core import Context, HomeAssistant

    from ..providers import LockControlProvider

_PROFILE_DOMAINS = {
    "lock": frozenset({"lock"}),
    "garage_cover": frozenset({"cover"}),
    "garage_toggle": frozenset({"button", "switch"}),
    "electric_strike": frozenset({"button", "switch", "lock"}),
}


@dataclass(frozen=True, slots=True)
class AccessPointCommandResult:
    """Truthful result of dispatching or safely skipping one door command."""

    command_sent: bool
    confirmation_required: bool


class AccessPointCommandService:
    """Use one control-profile implementation for app and NFC commands."""

    def __init__(
        self,
        hass: HomeAssistant,
        access_points: AccessPointService,
        lock_correlations: LockCommandCorrelationService,
        lock_provider: LockControlProvider | None = None,
    ) -> None:
        self._hass = hass
        self._access_points = access_points
        self._lock_correlations = lock_correlations
        self._lock_provider = lock_provider or HomeAssistantLockProvider(hass)

    async def supports_nfc_access(self, access_point_id: UUID) -> bool:
        """Return whether NFC may safely invoke this door's unlock path now."""
        try:
            target = await self._access_points.get_target(access_point_id)
            state = await self._access_points.resolve_state(access_point_id)
        except (TypeError, ValueError):
            return False
        if not target.access_point.enabled or not target.nfc_capable:
            return False
        domain = target.control_entity_id.split(".", 1)[0]
        if domain not in _PROFILE_DOMAINS.get(target.control_profile, frozenset()):
            return False
        entity = self._hass.states.get(target.control_entity_id)
        if entity is None or entity.state in {STATE_UNKNOWN, STATE_UNAVAILABLE}:
            return False
        if state.availability is not AccessPointAvailability.AVAILABLE:
            return False
        if target.control_profile == "lock":
            return state.lock_state in {
                "locked",
                "locking",
                "unlocked",
                "unlocking",
                "open",
                "opening",
            }
        if target.control_profile == "garage_cover":
            return state.lock_state in {"locked", "locking", "unlocked", "unlocking"}
        if target.control_profile == "garage_toggle":
            return target.status_entity_id is not None and state.door_state in {
                "open",
                "closed",
            }
        return target.control_profile == "electric_strike"

    async def execute(
        self,
        access_point_id: UUID,
        operation: str,
        *,
        origin: LockEventOrigin,
        context: Context,
        person_id: UUID | None = None,
        person_name: str | None = None,
    ) -> AccessPointCommandResult:
        """Dispatch one generic lock/cover/relay command."""
        if operation not in {SERVICE_LOCK, SERVICE_UNLOCK}:
            raise ValueError("Unsupported access point operation")
        if origin is LockEventOrigin.NFC_PASSKEY and not await self.supports_nfc_access(
            access_point_id
        ):
            raise ValueError("This Door does not currently support NFC access")

        target = await self._access_points.get_target(access_point_id)
        state = await self._access_points.resolve_state(access_point_id)
        no_op = self._already_in_requested_state(target, state.door_state, operation)
        if no_op:
            return AccessPointCommandResult(False, False)
        if target.control_profile == "electric_strike" and operation == SERVICE_LOCK:
            raise ValueError("An electric strike can only be released")

        command_id = uuid4()
        correlation_registered = False
        confirmation_required = target.control_profile != "electric_strike" and not (
            target.control_profile == "garage_toggle" and target.status_entity_id is None
        )
        if confirmation_required:
            try:
                self._lock_correlations.register(
                    access_point_id=target.access_point.id,
                    requested_state=(
                        LockStableState.LOCKED
                        if operation == SERVICE_LOCK
                        else LockStableState.UNLOCKED
                    ),
                    origin=origin,
                    command_id=command_id,
                    person_id=person_id,
                    person_name=person_name,
                )
                correlation_registered = True
            except LockCommandCorrelationError as err:
                raise ValueError(str(err)) from err
        try:
            await self._dispatch(target, operation, context)
        except BaseException:
            if correlation_registered:
                self._lock_correlations.cancel(command_id)
            raise
        return AccessPointCommandResult(
            True,
            confirmation_required,
        )

    async def unlock_access_point(
        self,
        access_point_id: UUID,
        *,
        origin: LockEventOrigin,
        context: Context,
        person_id: UUID,
        person_name: str,
    ) -> None:
        """Protocol-compatible NFC unlock dispatcher."""
        await self.execute(
            access_point_id,
            SERVICE_UNLOCK,
            origin=origin,
            context=context,
            person_id=person_id,
            person_name=person_name,
        )

    @staticmethod
    def _already_in_requested_state(
        target: AccessPointTarget,
        door_state: str | None,
        operation: str,
    ) -> bool:
        if target.control_profile != "garage_toggle" or door_state is None:
            return False
        return (operation == SERVICE_UNLOCK and door_state == "open") or (
            operation == SERVICE_LOCK and door_state == "closed"
        )

    async def _dispatch(
        self,
        target: AccessPointTarget,
        operation: str,
        context: Context,
    ) -> None:
        if target.control_profile == "garage_cover":
            service = "close_cover" if operation == SERVICE_LOCK else "open_cover"
            await self._hass.services.async_call(
                "cover",
                service,
                target={ATTR_ENTITY_ID: target.control_entity_id},
                blocking=True,
                context=context,
            )
            return
        if target.control_profile in {"garage_toggle", "electric_strike"}:
            domain = target.control_entity_id.split(".", 1)[0]
            if domain == "button":
                await self._hass.services.async_call(
                    "button",
                    "press",
                    target={ATTR_ENTITY_ID: target.control_entity_id},
                    blocking=True,
                    context=context,
                )
                return
            if domain == "switch":
                await self._hass.services.async_call(
                    "switch",
                    "turn_on",
                    target={ATTR_ENTITY_ID: target.control_entity_id},
                    blocking=True,
                    context=context,
                )
                try:
                    await asyncio.sleep(target.pulse_seconds)
                finally:
                    await self._hass.services.async_call(
                        "switch",
                        "turn_off",
                        target={ATTR_ENTITY_ID: target.control_entity_id},
                        blocking=True,
                        context=context,
                    )
                return
            await self._lock_provider.unlock(target.control_entity_id, context=context)
            return
        if operation == SERVICE_LOCK:
            await self._lock_provider.lock(target.control_entity_id, context=context)
        else:
            await self._lock_provider.unlock(target.control_entity_id, context=context)


__all__ = ["AccessPointCommandResult", "AccessPointCommandService"]
