"""Managed Frient ZHA keypad parsing and Activity attribution."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from homeassistant.core import Context

from custom_components.homepass.models import (
    AccessDevice,
    AccessDeviceIntegration,
    ActivityAccessMethod,
    ActivityActorType,
    ActivityCategory,
    ActivityEvent,
    ActivityEventType,
    ActivitySeverity,
    ActivitySource,
    KeypadOperation,
    LockEventOrigin,
    default_keypad_button_actions,
)
from custom_components.homepass.services.activity_presentation import present_activity
from custom_components.homepass.services.lock_event_correlation import (
    LockCommandCorrelationService,
    LockStableState,
)
from custom_components.homepass.services.zha_keypad import (
    ZhaKeypadService,
    parse_zha_keypad_command,
)

_DEVICE_ID = "00000000000000000000000000000001"


def _event(arm_mode: int, code: str = "2468") -> dict[str, object]:
    return {
        "device_id": _DEVICE_ID,
        "cluster_id": 1281,
        "command": "arm",
        "params": {"arm_mode": arm_mode, "code": code, "zone_id": 0},
    }


def test_observed_padlock_events_map_to_two_supported_buttons() -> None:
    unlock = parse_zha_keypad_command(_event(0))
    lock = parse_zha_keypad_command(_event(3))

    assert unlock is not None and unlock.button == "disarm"
    assert lock is not None and lock.button == "arm_all_zones"


def test_other_observed_arm_modes_remain_parseable_but_policy_disabled() -> None:
    house = parse_zha_keypad_command(_event(1))
    night = parse_zha_keypad_command(_event(2))

    assert house is not None and house.button == "arm_day_zones"
    assert night is not None and night.button == "arm_night_zones"
    actions = default_keypad_button_actions()
    assert actions[house.button] is KeypadOperation.NONE
    assert actions[night.button] is KeypadOperation.NONE
    assert actions["emergency"] is KeypadOperation.NONE


def test_internal_state_event_and_malformed_pins_are_ignored() -> None:
    internal = dict(_event(0))
    internal["command"] = (
        "00:11:22:33:44:55:66:77:44:0x0501_CLIENT_zha_armed_state_changed"
    )

    assert parse_zha_keypad_command(internal) is None
    assert parse_zha_keypad_command(_event(0, "12ab")) is None
    assert parse_zha_keypad_command(_event(0, "123")) is None


def test_parsed_command_repr_never_contains_pin() -> None:
    command = parse_zha_keypad_command(_event(0))

    assert command is not None
    assert "2468" not in repr(command)
    assert "<redacted>" in repr(command)


def test_keypad_identity_survives_physical_confirmation() -> None:
    now = datetime.now(UTC)
    access_point_id = uuid4()
    person_id = uuid4()
    correlations = LockCommandCorrelationService(clock=lambda: now)
    correlations.register(
        access_point_id=access_point_id,
        requested_state=LockStableState.UNLOCKED,
        origin=LockEventOrigin.HOMEPASS_KEYPAD,
        command_id=uuid4(),
        person_id=person_id,
        person_name="Example Resident",
    )

    confirmed = correlations.consume(
        access_point_id=access_point_id,
        confirmed_state=LockStableState.UNLOCKED,
        confirmed_at=now,
    )

    assert confirmed is not None
    assert confirmed.person_id == person_id
    assert confirmed.person_name == "Example Resident"


def test_confirmed_roller_door_activity_names_user_and_pin_method() -> None:
    now = datetime.now(UTC)
    person_id = uuid4()
    event = ActivityEvent(
        event_id=uuid4(),
        occurred_at=now,
        recorded_at=now,
        event_type=ActivityEventType.DOOR_OPENED,
        category=ActivityCategory.DOOR,
        severity=ActivitySeverity.INFO,
        source=ActivitySource.HOME_ASSISTANT,
        actor_type=ActivityActorType.PERSON,
        actor_id=person_id,
        actor_name="Example Resident",
        access_method=ActivityAccessMethod.KEYPAD,
        door_id=uuid4(),
        door_name="Workshop Door",
        person_id=person_id,
        person_name="Example Resident",
    )

    presented = present_activity(event)

    assert presented.title == "Example Resident opened Workshop Door with a PIN."


@pytest.mark.asyncio
async def test_zha_adapter_delegates_only_to_matching_zha_device() -> None:
    access_point_id = UUID("00000000-0000-4000-8000-000000000101")
    zha_device = AccessDevice(
        display_name="ZHA keypad",
        home_assistant_device_id=_DEVICE_ID,
        access_point_id=access_point_id,
    )
    mqtt_device = AccessDevice(
        display_name="MQTT keypad",
        home_assistant_device_id=_DEVICE_ID,
        access_point_id=access_point_id,
        integration=AccessDeviceIntegration.ZIGBEE2MQTT,
        zigbee_ieee_address="0x0200000000000001",
        zigbee2mqtt_base_topic="zigbee2mqtt",
        zigbee2mqtt_friendly_name="garage_keypad",
    )
    store = SimpleNamespace(list_all=AsyncMock(return_value=(zha_device, mqtt_device)))
    processor = SimpleNamespace(process=AsyncMock())
    service = ZhaKeypadService(
        SimpleNamespace(),  # type: ignore[arg-type]
        store,  # type: ignore[arg-type]
        processor,  # type: ignore[arg-type]
    )
    parsed = parse_zha_keypad_command(_event(0))
    assert parsed is not None
    event = SimpleNamespace(time_fired=datetime.now(UTC), context=Context())

    await service._process(event, parsed)  # noqa: SLF001

    processor.process.assert_awaited_once()
    delegated = processor.process.await_args.args[0]
    assert delegated.device == zha_device
