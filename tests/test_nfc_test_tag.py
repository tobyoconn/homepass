"""NTAG216 test-tag access behavior."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import ANY, AsyncMock, Mock
from uuid import uuid4

import pytest
from homeassistant.const import SERVICE_LOCK, SERVICE_UNLOCK

from custom_components.homepass.models import LockEventOrigin
from custom_components.homepass.nfc.access import (
    TAP_SESSION_TTL_SECONDS,
    NfcAccessService,
)
from custom_components.homepass.nfc.models import NfcTestTag


def test_tap_session_expires_after_thirty_seconds() -> None:
    """The public unlock page and backend use the same short tap lifetime."""
    assert TAP_SESSION_TTL_SECONDS == 30


@pytest.mark.asyncio
async def test_test_tag_requires_passkey_then_dispatches_real_unlock() -> None:
    """An active static test tag uses policy and the normal NFC unlock boundary."""
    access_point_id = uuid4()
    now = datetime.now(UTC)
    tag = NfcTestTag("A" * 64, access_point_id, True, now + timedelta(days=7), now)
    repository = SimpleNamespace(
        get_active_test_tag=AsyncMock(return_value=tag),
        test_tag_hash_is_active=AsyncMock(return_value=True),
        append_audit=AsyncMock(),
    )
    relationship = SimpleNamespace(
        decision=SimpleNamespace(allowed=True, value="allowed"),
        access_point=SimpleNamespace(display_name="Test Door", entry_action="unlock"),
        person=SimpleNamespace(person_id=uuid4(), display_name="Example Resident"),
    )
    authorization = SimpleNamespace(
        resolve_person_for_access_point=AsyncMock(return_value=relationship)
    )
    target = SimpleNamespace(
        access_point=SimpleNamespace(display_name="Test Door", entry_action="unlock"),
        control_profile="lock",
    )
    access_points = SimpleNamespace(get_target=AsyncMock(return_value=target))
    capabilities = SimpleNamespace(supports_nfc_access=AsyncMock(return_value=True))
    dispatcher = SimpleNamespace(execute=AsyncMock())
    hass = SimpleNamespace(bus=SimpleNamespace(async_fire=Mock()))
    service = NfcAccessService(
        hass,
        repository,
        Mock(),
        authorization,
        access_points,
        capabilities,
        dispatcher,
    )

    ready = await service.begin_test_tap(raw_token="temporary-static-token")
    service.validate_tap_session(ready.tap_session)
    person_id = uuid4()
    result = await service.operate(tap_session=ready.tap_session, person_id=person_id)

    assert result.allowed is True
    assert result.test_mode is True
    assert ready.action == "unlock"
    assert result.action == "unlock"
    dispatcher.execute.assert_awaited_once_with(
        access_point_id,
        SERVICE_UNLOCK,
        origin=LockEventOrigin.NFC_PASSKEY,
        context=ANY,
        person_id=relationship.person.person_id,
        person_name="Example Resident",
    )
    repository.append_audit.assert_awaited_once()


@pytest.mark.asyncio
async def test_revoked_test_tag_cannot_unlock_existing_tap_session() -> None:
    """Revocation is rechecked after passkey verification and before the Door command."""
    access_point_id = uuid4()
    now = datetime.now(UTC)
    tag = NfcTestTag("B" * 64, access_point_id, True, now + timedelta(days=7), now)
    repository = SimpleNamespace(
        get_active_test_tag=AsyncMock(return_value=tag),
        test_tag_hash_is_active=AsyncMock(return_value=False),
        append_audit=AsyncMock(),
    )
    target = SimpleNamespace(
        access_point=SimpleNamespace(display_name="Test Door", entry_action="unlock"),
        control_profile="lock",
    )
    access_points = SimpleNamespace(get_target=AsyncMock(return_value=target))
    capabilities = SimpleNamespace(supports_nfc_access=AsyncMock(return_value=True))
    dispatcher = SimpleNamespace(execute=AsyncMock())
    hass = SimpleNamespace(bus=SimpleNamespace(async_fire=Mock()))
    service = NfcAccessService(
        hass,
        repository,
        Mock(),
        SimpleNamespace(),
        access_points,
        capabilities,
        dispatcher,
    )

    ready = await service.begin_test_tap(raw_token="temporary-static-token")
    result = await service.operate(tap_session=ready.tap_session, person_id=uuid4())

    assert result.allowed is False
    assert result.test_mode is True
    dispatcher.execute.assert_not_awaited()


@pytest.mark.parametrize(
    ("control_profile", "lock_state", "door_state", "operation", "action"),
    (
        ("garage_cover", "locked", "closed", SERVICE_UNLOCK, "open"),
        ("garage_cover", "unlocked", "open", SERVICE_LOCK, "close"),
        ("garage_toggle", "locked", "closed", SERVICE_UNLOCK, "open"),
        ("garage_toggle", "unlocked", "open", SERVICE_LOCK, "close"),
    ),
)
@pytest.mark.asyncio
async def test_roller_door_tap_is_bound_to_current_open_or_close_action(
    control_profile: str,
    lock_state: str,
    door_state: str,
    operation: str,
    action: str,
) -> None:
    """Only roller-door profiles turn an NFC page into an open/close control."""
    access_point_id = uuid4()
    now = datetime.now(UTC)
    tag = NfcTestTag("C" * 64, access_point_id, True, now + timedelta(days=7), now)
    repository = SimpleNamespace(
        get_active_test_tag=AsyncMock(return_value=tag),
        test_tag_hash_is_active=AsyncMock(return_value=True),
        append_audit=AsyncMock(),
    )
    relationship = SimpleNamespace(
        decision=SimpleNamespace(allowed=True, value="allowed"),
        access_point=SimpleNamespace(display_name="Roller Door"),
        person=SimpleNamespace(person_id=uuid4(), display_name="Example Resident"),
    )
    authorization = SimpleNamespace(
        resolve_person_for_access_point=AsyncMock(return_value=relationship)
    )
    target = SimpleNamespace(
        access_point=SimpleNamespace(display_name="Roller Door"),
        control_profile=control_profile,
    )
    access_points = SimpleNamespace(
        get_target=AsyncMock(return_value=target),
        resolve_state=AsyncMock(
            return_value=SimpleNamespace(lock_state=lock_state, door_state=door_state)
        ),
    )
    capabilities = SimpleNamespace(supports_nfc_access=AsyncMock(return_value=True))
    dispatcher = SimpleNamespace(execute=AsyncMock())
    service = NfcAccessService(
        SimpleNamespace(bus=SimpleNamespace(async_fire=Mock())),
        repository,
        Mock(),
        authorization,
        access_points,
        capabilities,
        dispatcher,
    )

    ready = await service.begin_test_tap(raw_token="temporary-static-token")
    result = await service.operate(tap_session=ready.tap_session, person_id=uuid4())

    assert ready.action == action
    assert result.action == action
    expected_progress = "closing" if action == "close" else "opening"
    assert expected_progress in result.message
    dispatcher.execute.assert_awaited_once_with(
        access_point_id,
        operation,
        origin=LockEventOrigin.NFC_PASSKEY,
        context=ANY,
        person_id=relationship.person.person_id,
        person_name="Example Resident",
    )
