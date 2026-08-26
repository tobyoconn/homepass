"""Provider contract tests for Yale/Z-Wave and Nuki adapters."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, time
from typing import TYPE_CHECKING

import pytest

from custom_components.homepass.models import DayOfWeek, Schedule, WeeklyRule
from custom_components.homepass.providers import (
    AuthorizationMutationState,
    AuthorizationProviderRegistry,
    AuthorizationRequest,
    AuthorizationSchedule,
    ProviderCommunicationError,
)
from custom_components.homepass.providers.nuki import NukiAuthorizationProvider
from custom_components.homepass.providers.nuki_credential import NukiNumberedCredentialDriver
from custom_components.homepass.providers.schedule import authorization_schedule_from_homepass
from custom_components.homepass.providers.zwave import ZWaveAuthorizationProvider
from custom_components.homepass.services.zwave_sync import (
    DriverCommandResult,
    DriverCommandStatus,
    VerificationStatus,
    ZWaveDriverError,
    ZWaveUser,
)

if TYPE_CHECKING:
    from custom_components.homepass.drivers.base import CredentialReplacementRequest

SMARTLOCK_ID = "21913877581"


class FakeNukiTransport:
    """Deterministic secret-free Nuki transport fixture."""

    def __init__(self, *responses: object) -> None:
        self.responses = list(responses)
        self.calls: list[tuple[str, str, object | None]] = []

    async def request(
        self,
        method: str,
        path: str,
        *,
        payload: object | None = None,
    ) -> object:
        self.calls.append((method, path, payload))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def _request() -> AuthorizationRequest:
    return AuthorizationRequest(
        display_name="Housekeeper",
        pin="292929",
        schedule=AuthorizationSchedule(
            valid_from=datetime(2026, 8, 22, 6, 0, tzinfo=UTC),
            weekdays=frozenset({1, 2, 3, 4, 5, 6}),
            from_minute=600,
            until_minute=840,
        ),
    )


def test_authorization_request_repr_redacts_pin() -> None:
    request = _request()

    assert "292929" not in repr(request)
    assert "<redacted>" in repr(request)


def test_provider_registry_requires_explicit_provider() -> None:
    registry = AuthorizationProviderRegistry()
    transport = FakeNukiTransport()
    provider = NukiAuthorizationProvider(transport, SMARTLOCK_ID)

    registry.register("nuki", provider)

    assert registry.require("nuki") is provider
    with pytest.raises(ValueError, match="not configured"):
        registry.require("zwave_js")


@pytest.mark.asyncio
async def test_nuki_create_is_pending_and_maps_schedule_without_exposing_pin() -> None:
    transport = FakeNukiTransport(
        {
            "requestId": "request-1",
            "detail": [
                {
                    "smartlockId": int(SMARTLOCK_ID),
                    "success": True,
                    "id": "authorization-1",
                    "authId": 17,
                }
            ],
        }
    )
    provider = NukiAuthorizationProvider(transport, SMARTLOCK_ID)

    result = await provider.create_authorization(_request())

    assert result.state is AuthorizationMutationState.PENDING
    assert result.external_id == "17"
    assert result.request_id == "request-1"
    assert transport.calls == [
        (
            "PUT",
            "/smartlock/auth",
            {
                "name": "Housekeeper",
                "type": 13,
                "code": 292929,
                "remoteAllowed": False,
                "smartlockIds": [int(SMARTLOCK_ID)],
                "allowedFromDate": "2026-08-22T06:00:00.000Z",
                "allowedWeekDays": 126,
                "allowedFromTime": 600,
                "allowedUntilTime": 840,
            },
        )
    ]
    assert "292929" not in repr(result)


@pytest.mark.asyncio
async def test_nuki_readback_confirms_matching_authorization_and_redacts_listing() -> None:
    raw = {
        "id": "authorization-1",
        "authId": 17,
        "smartlockId": int(SMARTLOCK_ID),
        "type": 13,
        "name": "Housekeeper",
        "code": 292929,
        "enabled": True,
        "allowedFromDate": "2026-08-22T06:00:00.000Z",
        "allowedWeekDays": 126,
        "allowedFromTime": 600,
        "allowedUntilTime": 840,
    }
    transport = FakeNukiTransport([raw], [raw])
    provider = NukiAuthorizationProvider(transport, SMARTLOCK_ID)

    verification = await provider.verify_authorization(_request(), external_id="17")
    listed = await provider.list_authorizations()

    assert verification.state is AuthorizationMutationState.CONFIRMED
    assert listed[0].external_id == "17"
    assert listed[0].display_name == "Housekeeper"
    assert "292929" not in repr(listed)


@pytest.mark.asyncio
async def test_nuki_readback_normalizes_server_all_day_defaults() -> None:
    raw = {
        "id": "authorization-1",
        "authId": 17,
        "type": 13,
        "name": "Housekeeper",
        "code": 292929,
        "enabled": True,
        "allowedWeekDays": 127,
        "allowedFromTime": 0,
        "allowedUntilTime": 0,
    }
    provider = NukiAuthorizationProvider(FakeNukiTransport([raw]), SMARTLOCK_ID)
    request = AuthorizationRequest(display_name="Housekeeper", pin="292929")

    result = await provider.verify_authorization(request, external_id="17")

    assert result.state is AuthorizationMutationState.CONFIRMED


@pytest.mark.asyncio
async def test_nuki_missing_readback_remains_pending_then_deletion_confirms() -> None:
    transport = FakeNukiTransport([], [])
    provider = NukiAuthorizationProvider(transport, SMARTLOCK_ID)

    creation = await provider.verify_authorization(_request())
    deletion = await provider.verify_authorization_deleted("17")

    assert creation.state is AuthorizationMutationState.PENDING
    assert deletion.state is AuthorizationMutationState.CONFIRMED


@pytest.mark.asyncio
async def test_nuki_deletion_maps_auth_id_to_batch_record_id() -> None:
    transport = FakeNukiTransport(
        [{"id": "authorization-1", "authId": 17}],
        {"requestId": "delete-1"},
    )
    provider = NukiAuthorizationProvider(transport, SMARTLOCK_ID)

    result = await provider.delete_authorization("17")

    assert result.state is AuthorizationMutationState.PENDING
    assert result.external_id == "17"
    assert result.request_id == "delete-1"
    assert transport.calls[-1] == (
        "DELETE",
        "/smartlock/auth",
        ["authorization-1"],
    )


@pytest.mark.asyncio
async def test_nuki_update_maps_auth_id_to_opaque_record_id() -> None:
    transport = FakeNukiTransport(
        [{"id": "authorization-1", "authId": 17}],
        None,
    )
    provider = NukiAuthorizationProvider(transport, SMARTLOCK_ID)

    result = await provider.update_authorization("17", _request())

    assert result.state is AuthorizationMutationState.PENDING
    assert result.external_id == "17"
    assert transport.calls[-1] == (
        "POST",
        f"/smartlock/{SMARTLOCK_ID}/auth/authorization-1",
        {
            "name": "Housekeeper",
            "code": 292929,
            "remoteAllowed": False,
            "enabled": True,
            "allowedFromDate": "2026-08-22T06:00:00.000Z",
            "allowedWeekDays": 126,
            "allowedFromTime": 600,
            "allowedUntilTime": 840,
        },
    )


@pytest.mark.asyncio
async def test_nuki_numbered_driver_confirms_and_persists_numeric_auth_id() -> None:
    raw = {
        "id": "authorization-1",
        "authId": 17,
        "smartlockId": int(SMARTLOCK_ID),
        "type": 13,
        "name": "Housekeeper",
        "code": 292929,
        "enabled": True,
    }
    transport = FakeNukiTransport(
        {
            "requestId": "request-1",
            "detail": [{"smartlockId": int(SMARTLOCK_ID), "authId": 17}],
        },
        [raw],
    )
    provider = NukiAuthorizationProvider(transport, SMARTLOCK_ID)
    driver = NukiNumberedCredentialDriver(
        provider,
        "lock.computer_room_smart_lock",
        verification_attempts=1,
        verification_delay=0,
    )

    created = await driver.provision_pin(
        "lock.computer_room_smart_lock",
        "292929",
        display_name="Housekeeper",
    )

    assert created.credential_slot == 17
    assert created.verification_status == "verified"


@pytest.mark.asyncio
async def test_nuki_numbered_driver_discovers_auth_id_after_empty_create_response() -> None:
    raw = {
        "id": "authorization-1",
        "authId": 17,
        "smartlockId": int(SMARTLOCK_ID),
        "type": 13,
        "name": "Housekeeper",
        "code": 292929,
        "enabled": True,
    }
    driver = NukiNumberedCredentialDriver(
        NukiAuthorizationProvider(FakeNukiTransport(None, [raw]), SMARTLOCK_ID),
        "lock.computer_room_smart_lock",
        verification_attempts=1,
        verification_delay=0,
    )

    created = await driver.provision_pin(
        "lock.computer_room_smart_lock",
        "292929",
        display_name="Housekeeper",
    )

    assert created.credential_slot == 17
    assert created.verification_status == "verified"


@pytest.mark.asyncio
async def test_nuki_numbered_driver_preserves_pending_state_after_readback_failure() -> None:
    transport = FakeNukiTransport(
        {
            "requestId": "request-1",
            "detail": [{"smartlockId": int(SMARTLOCK_ID), "authId": 17}],
        },
        ProviderCommunicationError("Nuki API request timed out"),
    )
    driver = NukiNumberedCredentialDriver(
        NukiAuthorizationProvider(transport, SMARTLOCK_ID),
        "lock.computer_room_smart_lock",
        verification_attempts=1,
        verification_delay=0,
    )

    created = await driver.provision_pin(
        "lock.computer_room_smart_lock",
        "292929",
        display_name="Housekeeper",
    )

    assert created.credential_slot == 17
    assert created.verification_status == "inconclusive"


@pytest.mark.asyncio
async def test_nuki_numbered_driver_treats_visible_deleted_auth_as_unconfirmed() -> None:
    transport = FakeNukiTransport([{"id": "authorization-1", "authId": 17}])
    driver = NukiNumberedCredentialDriver(
        NukiAuthorizationProvider(transport, SMARTLOCK_ID),
        "lock.computer_room_smart_lock",
        verification_attempts=1,
        verification_delay=0,
    )

    removed = await driver.verify_pin_removed("lock.computer_room_smart_lock", 17)

    assert removed is None


@pytest.mark.asyncio
async def test_nuki_numbered_driver_returns_sanitized_validation_failure() -> None:
    driver = NukiNumberedCredentialDriver(
        NukiAuthorizationProvider(FakeNukiTransport(), SMARTLOCK_ID),
        "lock.computer_room_smart_lock",
        verification_attempts=1,
        verification_delay=0,
    )

    with pytest.raises(ZWaveDriverError, match="six digits") as captured:
        await driver.provision_pin(
            "lock.computer_room_smart_lock",
            "120000",
            display_name="Housekeeper",
        )

    assert "120000" not in repr(captured.value)


def test_nuki_numbered_driver_preflights_pin_before_provider_io() -> None:
    """Access workflows can reject incompatible saved PINs before mutating Nuki."""
    driver = NukiNumberedCredentialDriver(
        NukiAuthorizationProvider(FakeNukiTransport(), SMARTLOCK_ID),
        "lock.computer_room_smart_lock",
    )

    driver.validate_pin("lock.computer_room_smart_lock", "292929")
    with pytest.raises(ValueError, match="six digits") as captured:
        driver.validate_pin("lock.computer_room_smart_lock", "120000")

    assert "120000" not in repr(captured.value)


def test_homepass_schedule_maps_shared_weekday_window_for_nuki() -> None:
    schedule = Schedule(
        name="Weekdays",
        time_zone="Asia/Dubai",
        valid_from=datetime(2026, 8, 22, tzinfo=UTC),
        weekly_rules=(
            WeeklyRule(DayOfWeek.MONDAY, time(10), time(14)),
            WeeklyRule(DayOfWeek.TUESDAY, time(10), time(14)),
        ),
    )

    mapped = authorization_schedule_from_homepass(schedule)

    assert mapped.valid_from == datetime(2026, 8, 22, tzinfo=UTC)
    assert mapped.weekdays == frozenset({1, 2})
    assert mapped.from_minute == 600
    assert mapped.until_minute == 840


def test_homepass_schedule_rejects_multiple_provider_windows() -> None:
    schedule = Schedule(
        name="Split shifts",
        time_zone="Asia/Dubai",
        weekly_rules=(
            WeeklyRule(DayOfWeek.MONDAY, time(10), time(14)),
            WeeklyRule(DayOfWeek.TUESDAY, time(15), time(18)),
        ),
    )

    with pytest.raises(ValueError, match="one recurring time window"):
        authorization_schedule_from_homepass(schedule)


@pytest.mark.asyncio
async def test_nuki_transport_failure_returns_sanitized_failed_state() -> None:
    transport = FakeNukiTransport(ProviderCommunicationError("Nuki API request timed out"))
    provider = NukiAuthorizationProvider(transport, SMARTLOCK_ID)

    result = await provider.create_authorization(_request())

    assert result.state is AuthorizationMutationState.FAILED
    assert result.error_summary == "Nuki API request timed out"
    assert "292929" not in repr(result)


@pytest.mark.asyncio
async def test_nuki_audit_events_are_normalized() -> None:
    transport = FakeNukiTransport(
        [
            {
                "id": "log-1",
                "date": "2026-08-21T10:00:00.000Z",
                "action": 1,
                "state": 0,
                "source": 1,
                "authId": 17,
                "name": "Housekeeper",
            }
        ]
    )
    provider = NukiAuthorizationProvider(transport, SMARTLOCK_ID)

    events = await provider.list_audit_events()

    assert events[0].action == "unlock"
    assert events[0].outcome == "success"
    assert events[0].source == "keypad"
    assert events[0].authorization_external_id == "17"


@dataclass
class FakeCreatedCredential:
    credential_slot: int
    verification_status: str


class FakeZWaveDriver:
    """Small Yale/Z-Wave fake proving the legacy adapter boundary."""

    async def provision_pin(self, lock_entity_id: str, pin: str) -> object:
        assert lock_entity_id == "lock.front_door"
        assert pin == "2468"
        return FakeCreatedCredential(7, "verified")

    async def request_remove_pin(self, lock_entity_id: str, slot: int) -> DriverCommandResult:
        return DriverCommandResult(DriverCommandStatus.ACCEPTED)

    async def verify_pin_removed(self, lock_entity_id: str, slot: int) -> bool | None:
        return True

    async def verify_pin(self, lock_entity_id: str, slot: int, pin: str) -> VerificationStatus:
        return "verified"

    async def list_users(self, lock_entity_id: str) -> tuple[ZWaveUser, ...]:
        return (ZWaveUser(7, "Front door PIN"),)

    def supports_pin_replacement(self, target_device: str) -> bool:
        return False

    async def async_request_credential_replacement(
        self, request: CredentialReplacementRequest
    ) -> object:
        raise AssertionError("Replacement is unsupported")

    async def async_verify_credential_replacement(
        self, request: CredentialReplacementRequest
    ) -> object:
        raise AssertionError("Replacement is unsupported")


@pytest.mark.asyncio
async def test_zwave_adapter_preserves_verified_numbered_slot_behavior() -> None:
    provider = ZWaveAuthorizationProvider(FakeZWaveDriver(), "lock.front_door")

    created = await provider.create_authorization(
        AuthorizationRequest(display_name="Ignored by Yale", pin="2468")
    )
    listed = await provider.list_authorizations()

    assert created.state is AuthorizationMutationState.CONFIRMED
    assert created.external_id == "7"
    assert listed[0].external_id == "7"
