"""Transport-neutral keypad security processing tests."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from homeassistant.core import Context

from custom_components.homepass.models import AccessDevice, KeypadOperation
from custom_components.homepass.services.access_point_command import AccessPointCommandResult
from custom_components.homepass.services.keypad_processor import (
    KeypadCommand,
    KeypadCommandProcessor,
    KeypadProcessingOutcome,
)
from custom_components.homepass.vault import AccessMethod

ACCESS_POINT_ID = UUID("00000000-0000-4000-8000-000000000101")
ACCESS_DEVICE_ID = UUID("00000000-0000-4000-8000-000000000201")
PERSON_ID = UUID("00000000-0000-4000-8000-000000000301")
NOW = datetime(2026, 8, 16, 12, 0, tzinfo=UTC)


def _device() -> AccessDevice:
    return AccessDevice(
        id=ACCESS_DEVICE_ID,
        display_name="Garage keypad",
        home_assistant_device_id="zha-device-id",
        access_point_id=ACCESS_POINT_ID,
        created_at=NOW,
        updated_at=NOW,
    )


def _command(device: AccessDevice, *, button: str = "disarm", pin: str = "2468") -> KeypadCommand:
    return KeypadCommand(
        device=device,
        button=button,
        pin=pin,
        occurred_at=NOW,
        context=Context(),
        source_event_key="test-keypad:99",
    )


def _processor(*, saved_pin: str = "2468", allowed: bool = True) -> tuple[object, ...]:
    metadata = SimpleNamespace(
        access_method=AccessMethod.PIN,
        credential_id=SimpleNamespace(value=UUID(int=401)),
        person_id=PERSON_ID,
    )
    credential_metadata = SimpleNamespace(list_enabled=AsyncMock(return_value=(metadata,)))
    vault = SimpleNamespace(retrieve=AsyncMock(return_value=saved_pin))
    relationship = SimpleNamespace(
        decision=SimpleNamespace(allowed=allowed),
        person=SimpleNamespace(person_id=PERSON_ID, display_name="Alex"),
    )
    authorization = SimpleNamespace(
        resolve_person_for_access_point=AsyncMock(return_value=relationship)
    )
    access_point = SimpleNamespace(id=ACCESS_POINT_ID, display_name="Garage Door")
    access_points = SimpleNamespace(get_access_point=AsyncMock(return_value=access_point))
    commands = SimpleNamespace(execute=AsyncMock(return_value=AccessPointCommandResult(True, True)))
    access_devices = SimpleNamespace(mark_ready_after_hardware_test=AsyncMock())
    activity = SimpleNamespace(record=AsyncMock())
    processor = KeypadCommandProcessor(
        access_devices,  # type: ignore[arg-type]
        credential_metadata,  # type: ignore[arg-type]
        vault,  # type: ignore[arg-type]
        authorization,  # type: ignore[arg-type]
        access_points,  # type: ignore[arg-type]
        commands,  # type: ignore[arg-type]
        activity,  # type: ignore[arg-type]
    )
    return processor, commands, access_devices, activity, authorization, vault


@pytest.mark.asyncio
async def test_authorized_request_executes_configured_action() -> None:
    processor, commands, access_devices, activity, _authorization, _vault = _processor()

    result = await processor.process(_command(_device()))  # type: ignore[union-attr]

    assert result.outcome is KeypadProcessingOutcome.SUCCESS
    assert result.operation is KeypadOperation.UNLOCK
    commands.execute.assert_awaited_once()  # type: ignore[union-attr]
    access_devices.mark_ready_after_hardware_test.assert_awaited_once_with(  # type: ignore[union-attr]
        ACCESS_DEVICE_ID
    )
    activity.record.assert_not_awaited()  # type: ignore[union-attr]


@pytest.mark.asyncio
async def test_invalid_pin_records_sanitized_failure_without_operating() -> None:
    processor, commands, _access_devices, activity, authorization, _vault = _processor(
        saved_pin="1357"
    )
    command = _command(_device())

    result = await processor.process(command)  # type: ignore[union-attr]

    assert result.outcome is KeypadProcessingOutcome.INVALID_CODE
    commands.execute.assert_not_awaited()  # type: ignore[union-attr]
    authorization.resolve_person_for_access_point.assert_not_awaited()  # type: ignore[union-attr]
    activity.record.assert_awaited_once()  # type: ignore[union-attr]
    proposal = activity.record.await_args.args[0]  # type: ignore[union-attr]
    assert proposal.source_event_key == "test-keypad:99"
    assert "2468" not in repr(proposal)
    assert "2468" not in repr(command)


@pytest.mark.asyncio
async def test_valid_but_unauthorized_pin_returns_not_ready_without_operating() -> None:
    processor, commands, _access_devices, activity, _authorization, _vault = _processor(
        allowed=False
    )

    result = await processor.process(_command(_device()))  # type: ignore[union-attr]

    assert result.outcome is KeypadProcessingOutcome.NOT_READY
    commands.execute.assert_not_awaited()  # type: ignore[union-attr]
    activity.record.assert_awaited_once()  # type: ignore[union-attr]


@pytest.mark.asyncio
async def test_unconfigured_button_does_not_validate_pin_or_operate() -> None:
    processor, commands, _access_devices, _activity, authorization, vault = _processor()

    result = await processor.process(  # type: ignore[union-attr]
        _command(_device(), button="arm_day_zones")
    )

    assert result.outcome is KeypadProcessingOutcome.NOT_READY
    vault.retrieve.assert_not_awaited()  # type: ignore[union-attr]
    authorization.resolve_person_for_access_point.assert_not_awaited()  # type: ignore[union-attr]
    commands.execute.assert_not_awaited()  # type: ignore[union-attr]


@pytest.mark.asyncio
async def test_processing_is_serialized_per_keypad() -> None:
    processor, commands, *_rest = _processor()
    entered = asyncio.Event()
    release = asyncio.Event()
    active = 0
    maximum_active = 0

    async def execute(*_args: object, **_kwargs: object) -> AccessPointCommandResult:
        nonlocal active, maximum_active
        active += 1
        maximum_active = max(maximum_active, active)
        entered.set()
        await release.wait()
        active -= 1
        return AccessPointCommandResult(True, True)

    commands.execute.side_effect = execute  # type: ignore[union-attr]
    first = asyncio.create_task(processor.process(_command(_device())))  # type: ignore[union-attr]
    await entered.wait()
    second = asyncio.create_task(processor.process(_command(_device())))  # type: ignore[union-attr]
    await asyncio.sleep(0)
    release.set()
    await asyncio.gather(first, second)

    assert maximum_active == 1
    assert commands.execute.await_count == 2  # type: ignore[union-attr]
