"""Secure Zigbee2MQTT transport for HomePASS-managed keypads."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Callable, Coroutine, Mapping
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any, Protocol

from homeassistant.components import mqtt
from homeassistant.core import Context, callback
from homeassistant.exceptions import HomeAssistantError

from ..models import AccessDevice, AccessDeviceIntegration
from ..zigbee2mqtt_device_catalog import parse_zigbee2mqtt_device_catalog
from .keypad_processor import (
    KeypadCommand,
    KeypadCommandProcessor,
    KeypadProcessingOutcome,
)

if TYPE_CHECKING:
    from uuid import UUID

    from homeassistant.components.mqtt import ReceiveMessage
    from homeassistant.core import CALLBACK_TYPE, HomeAssistant

_LOGGER = logging.getLogger(__name__)
_TRANSACTION_TTL = timedelta(minutes=2)
_REQUEST_ACTIONS = frozenset(
    {
        "disarm",
        "arm_day_zones",
        "arm_night_zones",
        "arm_all_zones",
        "emergency",
    }
)


class AccessDeviceStore(Protocol):
    """Load managed access devices without exposing persistence details."""

    async def list_all(self) -> tuple[AccessDevice, ...]: ...

    async def upsert(self, device: AccessDevice) -> AccessDevice: ...


@dataclass(frozen=True, slots=True, repr=False)
class Zigbee2MqttKeypadCommand:
    """Strict Zigbee2MQTT keypad request with an always-redacted PIN."""

    action: str
    pin: str
    zone: int
    transaction: int

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}(action={self.action!r}, pin=<redacted>, "
            f"zone={self.zone!r}, transaction={self.transaction!r})"
        )


def parse_zigbee2mqtt_keypad_command(payload: str) -> Zigbee2MqttKeypadCommand | None:
    """Accept only a complete KEYZB-110 request without retaining its raw payload."""
    if not isinstance(payload, str) or len(payload) > 4096:
        return None
    try:
        data = json.loads(payload)
    except (TypeError, ValueError):
        return None
    if not isinstance(data, Mapping):
        return None
    action = data.get("action")
    pin = data.get("action_code")
    zone = data.get("action_zone")
    transaction = data.get("action_transaction")
    if not isinstance(action, str) or action not in _REQUEST_ACTIONS:
        return None
    if (
        not isinstance(pin, str)
        or not 4 <= len(pin) <= 10
        or any(character not in "0123456789" for character in pin)
    ):
        return None
    if isinstance(zone, bool) or not isinstance(zone, int) or not 0 <= zone <= 255:
        return None
    if (
        isinstance(transaction, bool)
        or not isinstance(transaction, int)
        or not 0 <= transaction <= 255
    ):
        return None
    return Zigbee2MqttKeypadCommand(action, pin, zone, transaction)


class Zigbee2MqttKeypadService:
    """Subscribe to exact adopted-keypad topics through Home Assistant MQTT."""

    def __init__(
        self,
        hass: HomeAssistant,
        access_devices: AccessDeviceStore,
        processor: KeypadCommandProcessor,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._hass = hass
        self._access_devices = access_devices
        self._processor = processor
        self._clock = clock or (lambda: datetime.now(UTC))
        self._subscriptions: dict[UUID, tuple[str, CALLBACK_TYPE]] = {}
        self._catalog_subscriptions: dict[str, CALLBACK_TYPE] = {}
        self._tasks: set[asyncio.Task[None]] = set()
        self._seen_transactions: dict[tuple[UUID, int], datetime] = {}
        self._started = False

    @property
    def started(self) -> bool:
        return self._started

    async def async_start(self) -> None:
        """Start exact subscriptions after HomePASS dependencies are ready."""
        if self._started:
            return
        self._started = True
        await self.async_reconcile()

    async def async_reconcile(self) -> None:
        """Match subscriptions to the current enabled Zigbee2MQTT devices."""
        if not self._started:
            return
        devices = {
            device.id: device
            for device in await self._access_devices.list_all()
            if device.enabled
            and device.integration is AccessDeviceIntegration.ZIGBEE2MQTT
            and device.zigbee2mqtt_state_topic is not None
        }
        base_topics = {
            device.zigbee2mqtt_base_topic
            for device in devices.values()
            if device.zigbee2mqtt_base_topic is not None
        }
        for device_id, (topic, unsubscribe) in tuple(self._subscriptions.items()):
            device = devices.get(device_id)
            if device is None or device.zigbee2mqtt_state_topic != topic:
                unsubscribe()
                del self._subscriptions[device_id]

        for device_id, device in devices.items():
            if device_id in self._subscriptions:
                continue
            topic = device.zigbee2mqtt_state_topic
            if topic is None:
                continue
            try:
                unsubscribe = await mqtt.async_subscribe(
                    self._hass,
                    topic,
                    self._message_callback(device_id),
                    qos=0,
                    encoding="utf-8",
                )
            except HomeAssistantError:
                _LOGGER.error(
                    "HomePASS cannot start an adopted Zigbee2MQTT keypad because MQTT "
                    "is unavailable"
                )
                continue
            self._subscriptions[device_id] = (topic, unsubscribe)

        for base_topic, unsubscribe in tuple(self._catalog_subscriptions.items()):
            if base_topic not in base_topics:
                unsubscribe()
                del self._catalog_subscriptions[base_topic]
        for base_topic in base_topics:
            if base_topic in self._catalog_subscriptions:
                continue
            try:
                unsubscribe = await mqtt.async_subscribe(
                    self._hass,
                    f"{base_topic}/bridge/devices",
                    self._catalog_callback(base_topic),
                    qos=0,
                    encoding="utf-8",
                )
            except HomeAssistantError:
                _LOGGER.error(
                    "HomePASS cannot monitor adopted Zigbee2MQTT keypads because MQTT "
                    "is unavailable"
                )
                continue
            self._catalog_subscriptions[base_topic] = unsubscribe

    async def async_stop(self) -> None:
        """Stop accepting MQTT input, unsubscribe, and drain accepted requests."""
        self._started = False
        for _topic, unsubscribe in self._subscriptions.values():
            unsubscribe()
        self._subscriptions.clear()
        for unsubscribe in self._catalog_subscriptions.values():
            unsubscribe()
        self._catalog_subscriptions.clear()
        if self._tasks:
            await asyncio.gather(*tuple(self._tasks), return_exceptions=True)
        self._seen_transactions.clear()

    def _message_callback(self, device_id: UUID) -> Callable[[ReceiveMessage], None]:
        @callback
        def receive(message: ReceiveMessage) -> None:
            try:
                if not self._started or message.retain:
                    return
                if not isinstance(message.payload, str):
                    return
                command = parse_zigbee2mqtt_keypad_command(message.payload)
                if command is None or self._is_duplicate(device_id, command.transaction):
                    return
                self._schedule(
                    self._process_safely(device_id, message.topic, command),
                    "HomePASS Zigbee2MQTT keypad command",
                )
            except Exception:  # noqa: BLE001 - never let HA log a secret-bearing payload
                _LOGGER.warning("HomePASS rejected an unreadable Zigbee2MQTT keypad request")

        return receive

    def _catalog_callback(self, base_topic: str) -> Callable[[ReceiveMessage], None]:
        @callback
        def receive(message: ReceiveMessage) -> None:
            try:
                if not self._started or message.topic != f"{base_topic}/bridge/devices":
                    return
                if not isinstance(message.payload, str):
                    return
                self._schedule(
                    self._process_catalog_safely(base_topic, message.payload),
                    "HomePASS Zigbee2MQTT device catalog",
                )
            except Exception:  # noqa: BLE001 - never allow MQTT callback exceptions
                _LOGGER.warning("HomePASS rejected an unreadable Zigbee2MQTT device catalog")

        return receive

    async def _process_catalog_safely(self, base_topic: str, payload: str) -> None:
        try:
            await self._process_catalog(base_topic, payload)
        except Exception:  # noqa: BLE001 - catalog failures must not escape MQTT work
            _LOGGER.warning("HomePASS could not refresh Zigbee2MQTT keypad identities")

    async def _process_catalog(self, base_topic: str, payload: str) -> None:
        catalog = {item.ieee_address: item for item in parse_zigbee2mqtt_device_catalog(payload)}
        if not catalog:
            return
        changed = False
        for device in await self._access_devices.list_all():
            if (
                device.integration is not AccessDeviceIntegration.ZIGBEE2MQTT
                or device.zigbee2mqtt_base_topic != base_topic
                or device.zigbee_ieee_address is None
            ):
                continue
            physical = catalog.get(device.zigbee_ieee_address)
            if physical is not None and physical.friendly_name != device.zigbee2mqtt_friendly_name:
                await self._access_devices.upsert(
                    replace(
                        device,
                        zigbee2mqtt_friendly_name=physical.friendly_name,
                        updated_at=self._clock(),
                    )
                )
                changed = True
        if changed:
            await self.async_reconcile()

    def _is_duplicate(self, device_id: UUID, transaction: int) -> bool:
        now = self._clock().astimezone(UTC)
        cutoff = now - _TRANSACTION_TTL
        self._seen_transactions = {
            key: seen_at for key, seen_at in self._seen_transactions.items() if seen_at >= cutoff
        }
        key = (device_id, transaction)
        if key in self._seen_transactions:
            return True
        self._seen_transactions[key] = now
        return False

    def _schedule(self, target: Coroutine[Any, Any, None], name: str) -> None:
        if not self._started:
            target.close()
            return
        task = self._hass.async_create_task(target, name)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def _process_safely(
        self,
        device_id: UUID,
        received_topic: str,
        command: Zigbee2MqttKeypadCommand,
    ) -> None:
        try:
            device = await self._managed_device(device_id, received_topic)
        except Exception:  # noqa: BLE001 - never leak a command through a task exception
            _LOGGER.warning("HomePASS could not resolve a Zigbee2MQTT keypad request")
            return
        if device is None:
            return
        try:
            occurred_at = self._clock()
            result = await self._processor.process(
                KeypadCommand(
                    device=device,
                    button=command.action,
                    pin=command.pin,
                    occurred_at=occurred_at,
                    context=Context(),
                    source_event_key=(
                        f"zigbee2mqtt-keypad:{device.id}:{command.transaction}:"
                        f"{int(occurred_at.timestamp() * 1000)}"
                    ),
                )
            )
            mode = (
                command.action
                if result.outcome is KeypadProcessingOutcome.SUCCESS
                else result.outcome.value
            )
        except Exception:  # noqa: BLE001 - transport must return a safe denial
            _LOGGER.warning("HomePASS could not process a Zigbee2MQTT keypad request")
            mode = KeypadProcessingOutcome.NOT_READY.value
        await self._publish_acknowledgement(device, command.transaction, mode)

    async def _managed_device(
        self,
        device_id: UUID,
        received_topic: str,
    ) -> AccessDevice | None:
        matches = tuple(
            device
            for device in await self._access_devices.list_all()
            if device.id == device_id
            and device.enabled
            and device.integration is AccessDeviceIntegration.ZIGBEE2MQTT
            and device.zigbee2mqtt_state_topic == received_topic
        )
        return matches[0] if len(matches) == 1 else None

    async def _publish_acknowledgement(
        self,
        device: AccessDevice,
        transaction: int,
        mode: str,
    ) -> None:
        state_topic = device.zigbee2mqtt_state_topic
        if state_topic is None:
            return
        payload = json.dumps(
            {"arm_mode": {"transaction": transaction, "mode": mode}},
            separators=(",", ":"),
            sort_keys=True,
        )
        try:
            await mqtt.async_publish(
                self._hass,
                f"{state_topic}/set",
                payload,
                qos=0,
                retain=False,
            )
        except Exception:  # noqa: BLE001 - never expose the source message on publish failure
            _LOGGER.warning("HomePASS could not acknowledge a Zigbee2MQTT keypad request")


__all__ = [
    "Zigbee2MqttKeypadCommand",
    "Zigbee2MqttKeypadService",
    "parse_zigbee2mqtt_keypad_command",
]
