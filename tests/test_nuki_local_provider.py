"""Tests for direct, account-free Nuki authorization management."""

import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from pyNukiBT import NukiConst
from pyNukiBT.const import NukiUltraConst

from custom_components.homepass.providers.base import (
    AuthorizationMutationState,
    AuthorizationRequest,
    AuthorizationSchedule,
    ProviderCommunicationError,
)
from custom_components.homepass.providers.nuki_bluetooth import (
    NukiBluetoothCredential,
    NukiBluetoothTransport,
    _install_keypad_message_types,
)
from custom_components.homepass.providers.nuki_local import (
    NukiLocalAuthorizationProvider,
    NukiLocalKeypadCode,
)


def _request() -> AuthorizationRequest:
    return AuthorizationRequest(
        "Toby",
        "345678",
        AuthorizationSchedule(
            valid_from=datetime(2026, 8, 21, 8, tzinfo=UTC),
            valid_until=datetime(2026, 8, 22, 20, tzinfo=UTC),
            weekdays=frozenset({1, 2, 3, 4, 5}),
            from_minute=8 * 60,
            until_minute=18 * 60,
        ),
    )


def _credential() -> NukiBluetoothCredential:
    return NukiBluetoothCredential(
        auth_id="01" * 4,
        nuki_public_key="02" * 32,
        client_public_key="03" * 32,
        client_private_key="04" * 32,
        app_id=42,
        security_pin="123456",
    )


async def test_local_provider_reports_pending_until_readback_confirms() -> None:
    """A mutation is pending until the lock returns the exact requested record."""
    request = _request()
    transport = AsyncMock()
    transport.add_keypad_code.return_value = "7"
    transport.list_keypad_codes.return_value = (
        NukiLocalKeypadCode("7", "Toby", "345678", True, request.schedule),
    )
    provider = NukiLocalAuthorizationProvider(transport)

    created = await provider.create_authorization(request)
    verified = await provider.verify_authorization(request, external_id="7")

    assert created.state is AuthorizationMutationState.PENDING
    assert created.external_id == "7"
    assert verified.state is AuthorizationMutationState.CONFIRMED


async def test_local_provider_sanitizes_transport_failure() -> None:
    """Bluetooth failures become explicit failed synchronization state."""
    transport = AsyncMock()
    transport.add_keypad_code.side_effect = ProviderCommunicationError(
        "Nuki Bluetooth could not create keypad code"
    )
    result = await NukiLocalAuthorizationProvider(transport).create_authorization(_request())

    assert result.state is AuthorizationMutationState.FAILED
    assert result.error_summary == "Nuki Bluetooth could not create keypad code"
    assert "345678" not in repr(result)


@pytest.mark.parametrize("pin", ["123456", "012345", "34567", "345670"])
async def test_local_provider_rejects_invalid_nuki_pin(pin: str) -> None:
    """Nuki's keypad restrictions are enforced before any Bluetooth call."""
    provider = NukiLocalAuthorizationProvider(AsyncMock())

    with pytest.raises(ValueError, match="Nuki keypad PINs"):
        await provider.create_authorization(AuthorizationRequest("Toby", pin))


def test_bluetooth_credential_round_trip_and_repr_are_secret_safe() -> None:
    """Pairing material round-trips only through strict encrypted-vault payloads."""
    credential = _credential()

    assert NukiBluetoothCredential.deserialize(credential.serialize()) == credential
    assert "123456" not in repr(credential)

    with pytest.raises(ValueError, match="credential is invalid"):
        NukiBluetoothCredential.deserialize('{"security_pin":"123456"}')


def test_bluetooth_payload_maps_schedule_in_home_timezone() -> None:
    """Provider schedules are encoded using the lock's local wall clock."""
    hass = SimpleNamespace(config=SimpleNamespace(time_zone="Asia/Dubai"))
    transport = NukiBluetoothTransport(hass, "AA:BB:CC:DD:EE:FF", _credential())

    payload = transport._keypad_payload(_request(), b"n" * 32)

    assert payload["code"] == 345678
    assert payload["allowed_from_date"] == datetime(2026, 8, 21, 12)
    assert payload["allowed_until_date"] == datetime(2026, 8, 23, 0)
    assert payload["allowed_weekdays"]["monday"] is True
    assert payload["allowed_weekdays"]["sunday"] is False
    assert payload["security_pin"] == 123456


def test_ultra_keypad_command_table_uses_six_digit_security_pin_width() -> None:
    """The completed command table follows Ultra's uint32 Security PIN layout."""
    _install_keypad_message_types(SimpleNamespace(_const=NukiUltraConst))
    command = NukiUltraConst.NukiCommand.REQUEST_KEYPAD_CODES
    encoded = NukiUltraConst.message_types[command].build(
        {
            "offset": 0,
            "count": 50,
            "nonce": b"n" * 32,
            "security_pin": 123456,
        }
    )

    assert len(encoded) == 40
    assert encoded[-4:] == (123456).to_bytes(4, "little")


async def test_bluetooth_transport_serializes_operations() -> None:
    """Audit polling cannot overlap keypad work on the same Bluetooth lock."""
    hass = SimpleNamespace(config=SimpleNamespace(time_zone="Asia/Dubai"))
    transport = NukiBluetoothTransport(hass, "AA:BB:CC:DD:EE:FF", _credential())
    device = AsyncMock()
    device.device_type = NukiConst.NukiDeviceType.SMARTLOCK_ULTRA
    device._const = NukiUltraConst
    transport._device = lambda: device
    first_started = asyncio.Event()
    allow_first_to_finish = asyncio.Event()
    second_started = asyncio.Event()

    async def first_operation(_device: object) -> str:
        first_started.set()
        await allow_first_to_finish.wait()
        return "first"

    async def second_operation(_device: object) -> str:
        second_started.set()
        return "second"

    first = asyncio.create_task(transport._run("run first operation", first_operation))
    await first_started.wait()
    second = asyncio.create_task(transport._run("run second operation", second_operation))
    await asyncio.sleep(0)

    assert not second_started.is_set()

    allow_first_to_finish.set()

    assert await first == "first"
    assert await second == "second"
    assert device.connect.await_count == 2
    assert device.disconnect.await_count == 2
