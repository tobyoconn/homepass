"""Secure ZHA keypad input for HomePASS-managed Door accessories."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Coroutine, Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol

from homeassistant.core import callback

from ..models import AccessDevice, AccessDeviceIntegration
from .keypad_processor import KeypadCommand, KeypadCommandProcessor

if TYPE_CHECKING:
    from uuid import UUID

    from homeassistant.core import CALLBACK_TYPE, Event, HomeAssistant

_LOGGER = logging.getLogger(__name__)
_ZHA_EVENT = "zha_event"
_IAS_ACE_CLUSTER = 0x0501
_ARM_MODE_BUTTONS = {
    0: "disarm",
    1: "arm_day_zones",
    2: "arm_night_zones",
    3: "arm_all_zones",
}


class AccessDeviceStore(Protocol):
    """Load managed access devices without exposing persistence details."""

    async def list_all(self) -> tuple[AccessDevice, ...]: ...


@dataclass(frozen=True, slots=True, repr=False)
class ZhaKeypadCommand:
    """Strictly parsed keypad request; the PIN is deliberately excluded from repr."""

    home_assistant_device_id: str
    button: str
    pin: str

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}(home_assistant_device_id="
            f"{self.home_assistant_device_id!r}, button={self.button!r}, pin=<redacted>)"
        )


def parse_zha_keypad_command(data: object) -> ZhaKeypadCommand | None:
    """Accept only the observed Frient IAS ACE arm command shape."""
    if not isinstance(data, Mapping):
        return None
    device_id = data.get("device_id")
    cluster_id = data.get("cluster_id")
    if (
        not isinstance(device_id, str)
        or not device_id.strip()
        or isinstance(cluster_id, bool)
        or cluster_id != _IAS_ACE_CLUSTER
        or data.get("command") != "arm"
    ):
        return None
    params = data.get("params")
    if not isinstance(params, Mapping):
        return None
    arm_mode = params.get("arm_mode")
    pin = params.get("code")
    if isinstance(arm_mode, bool) or not isinstance(arm_mode, int):
        return None
    button = _ARM_MODE_BUTTONS.get(arm_mode)
    if button is None or not isinstance(pin, str):
        return None
    if not 4 <= len(pin) <= 10 or any(character not in "0123456789" for character in pin):
        return None
    return ZhaKeypadCommand(device_id.strip(), button, pin)


class ZhaKeypadService:
    """Validate managed keypad PINs and issue authorized Door operations."""

    def __init__(
        self,
        hass: HomeAssistant,
        access_devices: AccessDeviceStore,
        processor: KeypadCommandProcessor,
    ) -> None:
        self._hass = hass
        self._access_devices = access_devices
        self._processor = processor
        self._unsubscribe: CALLBACK_TYPE | None = None
        self._tasks: set[asyncio.Task[None]] = set()
        self._in_flight: set[UUID] = set()

    @property
    def started(self) -> bool:
        return self._unsubscribe is not None

    async def async_start(self) -> None:
        """Listen only after all HomePASS dependencies are ready."""
        if self._unsubscribe is None:
            self._unsubscribe = self._hass.bus.async_listen(_ZHA_EVENT, self._handle_event)

    async def async_stop(self) -> None:
        """Stop accepting requests and finish already accepted work."""
        if self._unsubscribe is not None:
            self._unsubscribe()
            self._unsubscribe = None
        if self._tasks:
            await asyncio.gather(*tuple(self._tasks), return_exceptions=True)
        self._in_flight.clear()

    @callback
    def _handle_event(self, event: Event[dict[str, Any]]) -> None:
        command = parse_zha_keypad_command(event.data)
        if command is None:
            return
        self._schedule(self._process_safely(event, command), "HomePASS ZHA keypad command")

    def _schedule(self, target: Coroutine[Any, Any, None], name: str) -> None:
        if self._unsubscribe is None:
            target.close()
            return
        task = self._hass.async_create_task(target, name)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def _process_safely(
        self,
        event: Event[dict[str, Any]],
        command: ZhaKeypadCommand,
    ) -> None:
        try:
            await self._process(event, command)
        except Exception:  # noqa: BLE001 - a keypad event must never disrupt Home Assistant
            _LOGGER.warning("HomePASS could not process a managed keypad request")

    async def _process(
        self,
        event: Event[dict[str, Any]],
        command: ZhaKeypadCommand,
    ) -> None:
        device = await self._managed_device(command.home_assistant_device_id)
        if device is None or device.id in self._in_flight:
            return
        self._in_flight.add(device.id)
        try:
            await self._processor.process(
                KeypadCommand(
                    device=device,
                    button=command.button,
                    pin=command.pin,
                    occurred_at=event.time_fired,
                    context=event.context,
                    source_event_key=f"zha-keypad:{event.context.id}",
                )
            )
        finally:
            self._in_flight.discard(device.id)

    async def _managed_device(self, home_assistant_device_id: str) -> AccessDevice | None:
        matches = tuple(
            device
            for device in await self._access_devices.list_all()
            if device.integration is AccessDeviceIntegration.ZHA
            and device.home_assistant_device_id == home_assistant_device_id
        )
        return matches[0] if len(matches) == 1 else None


__all__ = ["ZhaKeypadCommand", "ZhaKeypadService", "parse_zha_keypad_command"]
