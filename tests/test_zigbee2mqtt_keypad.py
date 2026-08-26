"""Secure Zigbee2MQTT keypad transport tests."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID

import pytest

from custom_components.homepass.models import AccessDevice, AccessDeviceIntegration
from custom_components.homepass.services.keypad_processor import (
    KeypadProcessingOutcome,
    KeypadProcessingResult,
)
from custom_components.homepass.services.zigbee2mqtt_keypad import (
    Zigbee2MqttKeypadService,
    parse_zigbee2mqtt_keypad_command,
)

ACCESS_POINT_ID = UUID("00000000-0000-4000-8000-000000000101")
ACCESS_DEVICE_ID = UUID("00000000-0000-4000-8000-000000000201")
NOW = datetime(2026, 8, 16, 12, 0, tzinfo=UTC)
STATE_TOPIC = "zigbee2mqtt/garage_keypad"


def _payload(
    *,
    action: object = "arm_all_zones",
    pin: object = "2468",
    zone: object = 23,
    transaction: object = 99,
) -> str:
    return json.dumps(
        {
            "action": action,
            "action_code": pin,
            "action_zone": zone,
            "action_transaction": transaction,
        }
    )


def _device() -> AccessDevice:
    return AccessDevice(
        id=ACCESS_DEVICE_ID,
        display_name="Garage keypad",
        home_assistant_device_id="mqtt-device-id",
        access_point_id=ACCESS_POINT_ID,
        integration=AccessDeviceIntegration.ZIGBEE2MQTT,
        zigbee_ieee_address="0x0200000000000001",
        zigbee2mqtt_base_topic="zigbee2mqtt",
        zigbee2mqtt_friendly_name="garage_keypad",
        created_at=NOW,
        updated_at=NOW,
    )


class _Store:
    def __init__(self, device: AccessDevice) -> None:
        self.device = device

    async def list_all(self) -> tuple[AccessDevice, ...]:
        return (self.device,)

    async def upsert(self, device: AccessDevice) -> AccessDevice:
        self.device = device
        return device


class _Hass:
    @staticmethod
    def async_create_task(target: object, _name: str) -> asyncio.Task[None]:
        return asyncio.create_task(target)  # type: ignore[arg-type]


def test_valid_payload_parses_and_repr_redacts_pin() -> None:
    command = parse_zigbee2mqtt_keypad_command(_payload())

    assert command is not None
    assert command.action == "arm_all_zones"
    assert command.transaction == 99
    assert "2468" not in repr(command)
    assert "<redacted>" in repr(command)


@pytest.mark.parametrize(
    "payload",
    [
        "not-json",
        json.dumps([]),
        json.dumps({"action": "arm_all_zones"}),
        _payload(action="exit_delay"),
        _payload(pin="12ab"),
        _payload(pin="123"),
        _payload(zone=True),
        _payload(transaction=True),
        _payload(transaction="99"),
        _payload(transaction=256),
    ],
)
def test_malformed_payloads_are_rejected(payload: str) -> None:
    assert parse_zigbee2mqtt_keypad_command(payload) is None


@pytest.mark.asyncio
async def test_success_acknowledges_once_and_rejects_retained_and_duplicate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    subscriptions: dict[str, object] = {}
    subscription_calls: list[str] = []
    unsubscribed: list[str] = []

    async def subscribe(
        _hass: object,
        topic: str,
        callback: object,
        *,
        qos: int,
        encoding: str,
    ) -> object:
        assert qos == 0
        assert encoding == "utf-8"
        subscription_calls.append(topic)
        subscriptions[topic] = callback
        return lambda: unsubscribed.append(topic)

    publish = AsyncMock()
    monkeypatch.setattr(
        "custom_components.homepass.services.zigbee2mqtt_keypad.mqtt.async_subscribe",
        subscribe,
    )
    monkeypatch.setattr(
        "custom_components.homepass.services.zigbee2mqtt_keypad.mqtt.async_publish",
        publish,
    )
    processor = SimpleNamespace(
        process=AsyncMock(return_value=KeypadProcessingResult(KeypadProcessingOutcome.SUCCESS))
    )
    service = Zigbee2MqttKeypadService(
        _Hass(),  # type: ignore[arg-type]
        _Store(_device()),
        processor,  # type: ignore[arg-type]
        clock=lambda: NOW,
    )
    await service.async_start()
    await service.async_reconcile()
    callback = subscriptions[STATE_TOPIC]
    message = SimpleNamespace(topic=STATE_TOPIC, payload=_payload(), retain=False)

    callback(SimpleNamespace(topic=STATE_TOPIC, payload=_payload(), retain=True))  # type: ignore[operator]
    callback(message)  # type: ignore[operator]
    callback(message)  # type: ignore[operator]
    await service.async_stop()

    processor.process.assert_awaited_once()
    publish.assert_awaited_once()
    _hass, topic, payload = publish.await_args.args
    assert topic == f"{STATE_TOPIC}/set"
    assert json.loads(payload) == {"arm_mode": {"transaction": 99, "mode": "arm_all_zones"}}
    assert publish.await_args.kwargs == {"qos": 0, "retain": False}
    assert set(unsubscribed) == {
        STATE_TOPIC,
        "zigbee2mqtt/bridge/devices",
    }
    assert subscription_calls == [STATE_TOPIC, "zigbee2mqtt/bridge/devices"]


@pytest.mark.asyncio
async def test_invalid_pin_outcome_publishes_invalid_code(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    subscriptions: dict[str, object] = {}

    async def subscribe(
        _hass: object,
        topic: str,
        callback: object,
        **_kwargs: object,
    ) -> object:
        subscriptions[topic] = callback
        return lambda: None

    publish = AsyncMock()
    monkeypatch.setattr(
        "custom_components.homepass.services.zigbee2mqtt_keypad.mqtt.async_subscribe",
        subscribe,
    )
    monkeypatch.setattr(
        "custom_components.homepass.services.zigbee2mqtt_keypad.mqtt.async_publish",
        publish,
    )
    processor = SimpleNamespace(
        process=AsyncMock(return_value=KeypadProcessingResult(KeypadProcessingOutcome.INVALID_CODE))
    )
    service = Zigbee2MqttKeypadService(
        _Hass(),  # type: ignore[arg-type]
        _Store(_device()),
        processor,  # type: ignore[arg-type]
        clock=lambda: NOW,
    )
    await service.async_start()

    subscriptions[STATE_TOPIC](  # type: ignore[operator]
        SimpleNamespace(topic=STATE_TOPIC, payload=_payload(), retain=False)
    )
    await service.async_stop()

    payload = json.loads(publish.await_args.args[2])
    assert payload["arm_mode"] == {"transaction": 99, "mode": "invalid_code"}


@pytest.mark.asyncio
async def test_retained_catalog_rename_rebinds_exact_keypad_topic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    subscriptions: dict[str, object] = {}
    unsubscribed: list[str] = []

    async def subscribe(
        _hass: object,
        topic: str,
        callback: object,
        **_kwargs: object,
    ) -> object:
        subscriptions[topic] = callback
        return lambda: unsubscribed.append(topic)

    monkeypatch.setattr(
        "custom_components.homepass.services.zigbee2mqtt_keypad.mqtt.async_subscribe",
        subscribe,
    )
    store = _Store(_device())
    processor = SimpleNamespace(process=AsyncMock())
    service = Zigbee2MqttKeypadService(
        _Hass(),  # type: ignore[arg-type]
        store,
        processor,  # type: ignore[arg-type]
        clock=lambda: NOW,
    )
    await service.async_start()
    catalog_payload = json.dumps(
        [
            {
                "ieee_address": "0x0200000000000001",
                "friendly_name": "renamed/keypad",
                "disabled": False,
                "interview_state": "SUCCESSFUL",
                "definition": {"vendor": "Develco", "model": "KEYZB-110"},
            }
        ]
    )

    subscriptions["zigbee2mqtt/bridge/devices"](  # type: ignore[operator]
        SimpleNamespace(
            topic="zigbee2mqtt/bridge/devices",
            payload=catalog_payload,
            retain=True,
        )
    )
    await asyncio.sleep(0)
    await asyncio.sleep(0)

    assert store.device.zigbee2mqtt_friendly_name == "renamed/keypad"
    assert "zigbee2mqtt/renamed/keypad" in subscriptions
    assert STATE_TOPIC in unsubscribed
    await service.async_stop()


@pytest.mark.asyncio
async def test_processing_exception_never_logs_pin(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    subscriptions: dict[str, object] = {}

    async def subscribe(
        _hass: object,
        topic: str,
        callback: object,
        **_kwargs: object,
    ) -> object:
        subscriptions[topic] = callback
        return lambda: None

    monkeypatch.setattr(
        "custom_components.homepass.services.zigbee2mqtt_keypad.mqtt.async_subscribe",
        subscribe,
    )
    monkeypatch.setattr(
        "custom_components.homepass.services.zigbee2mqtt_keypad.mqtt.async_publish",
        AsyncMock(),
    )
    processor = SimpleNamespace(
        process=AsyncMock(side_effect=RuntimeError("synthetic failure containing 2468"))
    )
    service = Zigbee2MqttKeypadService(
        _Hass(),  # type: ignore[arg-type]
        _Store(_device()),
        processor,  # type: ignore[arg-type]
        clock=lambda: NOW,
    )
    await service.async_start()

    with caplog.at_level(
        logging.WARNING,
        logger="custom_components.homepass.services.zigbee2mqtt_keypad",
    ):
        subscriptions[STATE_TOPIC](  # type: ignore[operator]
            SimpleNamespace(topic=STATE_TOPIC, payload=_payload(), retain=False)
        )
        await service.async_stop()

    assert "2468" not in caplog.text
    assert "action_code" not in caplog.text
