"""Open capability, persisted consent, and physical-entry command contracts."""

from dataclasses import replace
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from homeassistant.components.lock import LockEntityFeature
from homeassistant.core import Context

from custom_components.homepass.access_point_actions import (
    ENROLL_ACCESS_POINT_SCHEMA,
    UPDATE_ACCESS_POINT_SCHEMA,
)
from custom_components.homepass.access_point_state import HomeAssistantAccessPointStateResolver
from custom_components.homepass.models import AccessPoint, LockEventOrigin
from custom_components.homepass.providers.home_assistant import HomeAssistantLockProvider
from custom_components.homepass.providers.nuki_bluetooth import NukiBluetoothTransport
from custom_components.homepass.services.access_point import (
    AccessPointAvailability,
    AccessPointService,
    AccessPointState,
    AccessPointTarget,
)
from custom_components.homepass.services.access_point_command import AccessPointCommandService
from custom_components.homepass.services.lock_event_correlation import (
    LockCommandCorrelationService,
    LockStableState,
)
from custom_components.homepass.services.physical_activity import (
    normalize_physical_state,
    PhysicalEntityKind,
    NormalizedPhysicalState,
)


def test_legacy_policy_stays_unlock_only_and_new_policy_round_trips():
    door = AccessPoint(display_name="Example Door")
    legacy = door.to_dict()
    legacy.pop("open_enabled")
    legacy.pop("entry_action")
    assert AccessPoint.from_dict(legacy) == door
    updated = replace(door, open_enabled=True, entry_action="open")
    assert AccessPoint.from_dict(updated.to_dict()) == updated
    with pytest.raises(ValueError):
        replace(door, entry_action="open")
    with pytest.raises(TypeError):
        replace(door, open_enabled="true")


@pytest.mark.parametrize(
    "features,expected", [(0, False), (1, True), (2, False), (3, True), ("1", False), (True, False)]
)
async def test_capability_is_ha_feature_not_brand(hass, features, expected):
    hass.states.async_set("lock.example", "locked", {"supported_features": features})
    resolver = HomeAssistantAccessPointStateResolver(hass)
    target = AccessPointTarget(AccessPoint(display_name="Example Door"), "lock.example")
    state = await resolver.resolve_state(target)
    assert state.supports_open is expected
    assert state.recommended_entry_action is None


async def test_nuki_recommendation_never_creates_capability_or_permission(hass):
    reader = AsyncMock(return_value="open")
    resolver = HomeAssistantAccessPointStateResolver(
        hass, nuki_entity_id="lock.example", nuki_entry_recommendation=reader
    )
    target = AccessPointTarget(AccessPoint(display_name="Example Door"), "lock.example")
    hass.states.async_set("lock.example", "locked", {"supported_features": 0})
    assert (await resolver.resolve_state(target)).recommended_entry_action is None
    reader.assert_not_awaited()
    hass.states.async_set(
        "lock.example", "locked", {"supported_features": int(LockEntityFeature.OPEN)}
    )
    assert (await resolver.resolve_state(target)).recommended_entry_action == "open"
    assert target.access_point.open_enabled is False
    assert target.access_point.entry_action == "unlock"


def command_fixture(hass, *, enabled=True, entry="open", supported=True):
    target = AccessPointTarget(
        AccessPoint(display_name="Example Door", open_enabled=enabled, entry_action=entry),
        "lock.example",
    )
    state = AccessPointState(
        AccessPointAvailability.AVAILABLE, lock_state="locked", supports_open=supported
    )
    points = SimpleNamespace(
        get_target=AsyncMock(return_value=target), resolve_state=AsyncMock(return_value=state)
    )
    hass.states.async_set("lock.example", "locked", {"supported_features": int(supported)})
    provider = SimpleNamespace(open=AsyncMock(), unlock=AsyncMock(), lock=AsyncMock())
    correlations = LockCommandCorrelationService()
    return (
        target,
        provider,
        correlations,
        AccessPointCommandService(hass, points, correlations, provider),
    )


@pytest.mark.parametrize("origin", [LockEventOrigin.NFC_PASSKEY, LockEventOrigin.HOMEPASS_KEYPAD])
async def test_credential_entry_uses_open_and_does_not_accept_unlock_confirmation(hass, origin):
    target, provider, correlations, commands = command_fixture(hass)
    person_id = uuid4()
    result = await commands.execute(
        target.access_point.id,
        "unlock",
        origin=origin,
        context=Context(),
        person_id=person_id,
        person_name="Example Resident",
    )
    assert result.confirmation_required
    provider.open.assert_awaited_once()
    provider.unlock.assert_not_awaited()
    assert (
        correlations.consume(
            access_point_id=target.access_point.id,
            confirmed_state=LockStableState.UNLOCKED,
            confirmed_at=datetime.now(UTC),
        )
        is None
    )
    pending = correlations.consume(
        access_point_id=target.access_point.id,
        confirmed_state=LockStableState.OPEN,
        confirmed_at=datetime.now(UTC),
    )
    assert pending.person_id == person_id


async def test_manual_unlock_stays_unlock_even_when_entry_uses_open(hass):
    target, provider, _, commands = command_fixture(hass)
    await commands.execute(
        target.access_point.id, "unlock", origin=LockEventOrigin.HOMEPASS_MANUAL, context=Context()
    )
    provider.unlock.assert_awaited_once()
    provider.open.assert_not_awaited()


@pytest.mark.parametrize("enabled,supported", [(False, True), (True, False), (False, False)])
async def test_open_cannot_bypass_permission_or_current_capability(hass, enabled, supported):
    target, provider, _, commands = command_fixture(
        hass, enabled=enabled, entry="unlock", supported=supported
    )
    with pytest.raises(ValueError):
        await commands.execute(
            target.access_point.id,
            "open",
            origin=LockEventOrigin.HOMEPASS_MANUAL,
            context=Context(),
        )
    provider.open.assert_not_awaited()
    provider.unlock.assert_not_awaited()


async def test_capability_loss_does_not_silently_downgrade_entry(hass):
    target, provider, _, commands = command_fixture(hass, supported=False)
    with pytest.raises(ValueError):
        await commands.execute(
            target.access_point.id,
            "unlock",
            origin=LockEventOrigin.HOMEPASS_KEYPAD,
            context=Context(),
        )
    assert not await commands.supports_nfc_access(target.access_point.id)
    provider.unlock.assert_not_awaited()


async def test_dispatch_uses_distinct_home_assistant_open_service(hass):
    calls = []
    hass.states.async_set("lock.example", "locked", {"supported_features": 1})
    hass.services.async_register("lock", "open", lambda call: calls.append(call))
    context = Context()
    await HomeAssistantLockProvider(hass).open("lock.example", context=context)
    assert calls[0].data["entity_id"] == "lock.example"
    assert calls[0].context is context


async def test_onboarding_requires_explicit_decision_before_persistence():
    target = AccessPointTarget(AccessPoint(display_name="Example Door"), "lock.example")
    store = AsyncMock()
    store.list_all.return_value = ()
    resolver = SimpleNamespace(
        resolve_state=AsyncMock(
            return_value=AccessPointState(AccessPointAvailability.AVAILABLE, supports_open=True)
        )
    )
    service = AccessPointService(targets=(target,), state_resolver=resolver, enrollment_store=store)
    with pytest.raises(ValueError, match="Confirm"):
        await service.enroll_access_point(target.access_point.id)
    store.upsert.assert_not_awaited()
    result = await service.enroll_access_point(
        target.access_point.id, open_enabled=True, entry_action="open"
    )
    assert result.access_point.entry_action == "open"
    assert store.upsert.await_args.args[1].open_enabled is True


async def test_open_policy_update_preserves_identity_and_unrelated_fields():
    door = AccessPoint(display_name="Example Door")
    target = AccessPointTarget(door, "lock.example")
    store = AsyncMock()
    store.get.return_value = door
    resolver = SimpleNamespace(
        resolve_state=AsyncMock(
            return_value=AccessPointState(AccessPointAvailability.AVAILABLE, supports_open=True)
        )
    )
    service = AccessPointService(targets=(target,), state_resolver=resolver, policy_store=store)
    result = await service.update_open_policy(door.id, open_enabled=True, entry_action="open")
    assert result.access_point.id == door.id
    assert result.access_point.display_name == door.display_name
    assert result.access_point.created_at == door.created_at
    assert store.update.await_args.kwargs["expected_updated_at"] == door.updated_at


@pytest.mark.parametrize(
    "value,expected", [(0, "unlock"), (1, "open"), (None, None), (2, None), ("1", None)]
)
async def test_nuki_reads_only_door_fitting_and_caches_recommendation(value, expected):
    import asyncio

    transport = object.__new__(NukiBluetoothTransport)
    transport._entry_recommendation = None
    transport._entry_recommendation_expires = 0
    transport._entry_recommendation_lock = asyncio.Lock()
    transport._challenge = AsyncMock(return_value=SimpleNamespace(nonce=b"x" * 32))
    device = SimpleNamespace(
        _const=SimpleNamespace(NukiCommand=SimpleNamespace(REQUEST_CONFIG=20, CONFIG=21)),
        _send_encrypted_command=AsyncMock(
            return_value={"auto_unlatch": value, "name": "discarded"}
        ),
    )

    async def run(label, operation):
        return await operation(device)

    transport._run = AsyncMock(side_effect=run)
    assert await transport.entry_recommendation() == expected
    assert await transport.entry_recommendation() == expected
    transport._run.assert_awaited_once()
    device._send_encrypted_command.assert_awaited_once_with(
        20, {"nonce": b"x" * 32}, expected_response=21
    )


def test_latch_release_is_not_physical_door_open():
    assert (
        normalize_physical_state(PhysicalEntityKind.LOCK, "open")
        is NormalizedPhysicalState.UNLATCHED
    )
    assert (
        normalize_physical_state(PhysicalEntityKind.CONTACT, "on") is NormalizedPhysicalState.OPEN
    )


def test_policy_fields_are_available_in_admin_schemas():
    payload = {"access_point_id": str(uuid4()), "open_enabled": True, "entry_action": "open"}
    assert ENROLL_ACCESS_POINT_SCHEMA(payload) == payload
    assert UPDATE_ACCESS_POINT_SCHEMA(payload) == payload


async def test_consent_is_rechecked_after_state_discovery(hass):
    target, provider, _, commands = command_fixture(hass)
    revoked = replace(
        target, access_point=replace(target.access_point, open_enabled=False, entry_action="unlock")
    )
    commands._access_points.get_target.side_effect = [target, revoked]
    with pytest.raises(ValueError):
        await commands.execute(
            target.access_point.id,
            "open",
            origin=LockEventOrigin.HOMEPASS_MANUAL,
            context=Context(),
        )
    provider.open.assert_not_awaited()


async def test_non_admin_cannot_change_open_permission(hass):
    from homeassistant.exceptions import ServiceValidationError
    from custom_components.homepass.access_point_actions import async_register_access_point_actions

    points = AsyncMock()
    async_register_access_point_actions(hass, points, AsyncMock(), AsyncMock())
    with pytest.raises(ServiceValidationError, match="administrator"):
        await hass.services.async_call(
            "homepass",
            "update_access_point",
            {"access_point_id": str(uuid4()), "open_enabled": True, "entry_action": "open"},
            blocking=True,
            return_response=True,
            context=Context(),
        )
    points.update_open_policy.assert_not_awaited()
