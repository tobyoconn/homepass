"""Tests for local Nuki audit-event ingestion."""

import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from custom_components.homepass.models import ActivityAccessMethod
from custom_components.homepass.providers.base import ProviderAuditEvent
from custom_components.homepass.services.nuki_audit_ingestion import (
    NukiAuditIngestionService,
)


def _service(*, correlated: bool = True):
    access_point_id = uuid4()
    summary = SimpleNamespace(
        state=SimpleNamespace(lock_entity_id="lock.front_door"),
        access_point=SimpleNamespace(id=access_point_id),
    )
    access_points = AsyncMock()
    access_points.list_access_point_summaries.return_value = (summary,)
    physical = Mock()
    physical.accept_provider_unlock_evidence.return_value = correlated
    fingerprint = AsyncMock()
    service = NukiAuditIngestionService(
        SimpleNamespace(),
        AsyncMock(),
        "lock.front_door",
        access_points,
        physical,
        fingerprint,
    )
    return service, physical, fingerprint, access_point_id


async def test_keypad_audit_event_supplies_exact_physical_unlock_evidence() -> None:
    """A successful keypad record is correlated by its lock-assigned code ID."""
    service, physical, fingerprint, _access_point_id = _service()
    occurred_at = datetime.now(UTC)
    event = ProviderAuditEvent(
        "51", occurred_at, "unlock", "success", "17", "Ignored", "keypad"
    )

    await service._process(event)

    evidence = physical.accept_provider_unlock_evidence.call_args.args[1]
    assert evidence.access_method is ActivityAccessMethod.KEYPAD
    assert evidence.slot == 17
    assert physical.accept_provider_unlock_evidence.call_args.args[2] == occurred_at
    fingerprint.observe_provider_event.assert_not_awaited()


async def test_fingerprint_event_confirms_mapping_without_duplicate_activity() -> None:
    """Correlated fingerprint evidence confirms enrollment while physical Activity owns output."""
    service, physical, fingerprint, access_point_id = _service(correlated=True)
    event = ProviderAuditEvent(
        "52", datetime.now(UTC), "unlock", "success", "17", None, "fingerprint"
    )

    await service._process(event)

    evidence = physical.accept_provider_unlock_evidence.call_args.args[1]
    assert evidence.access_method is ActivityAccessMethod.FINGERPRINT
    fingerprint.observe_provider_event.assert_awaited_once_with(
        access_point_id, event, record_activity=False
    )


async def test_uncorrelated_fingerprint_event_records_safe_fallback_activity() -> None:
    """If Matter is not monitored, fingerprint attribution still records its own event."""
    service, _physical, fingerprint, access_point_id = _service(correlated=False)
    event = ProviderAuditEvent(
        "53", datetime.now(UTC), "unlatch", "success", "17", None, "fingerprint"
    )

    await service._process(event)

    fingerprint.observe_provider_event.assert_awaited_once_with(
        access_point_id, event, record_activity=True
    )


async def test_failed_or_unidentified_audit_event_is_ignored() -> None:
    """Names never substitute for exact successful authorization evidence."""
    service, physical, fingerprint, _access_point_id = _service()
    event = ProviderAuditEvent(
        "54", datetime.now(UTC), "unlock", "failed", None, "Toby", "fingerprint"
    )

    await service._process(event)

    physical.accept_provider_unlock_evidence.assert_not_called()
    fingerprint.observe_provider_event.assert_not_awaited()


async def test_poll_scheduler_keeps_only_one_bluetooth_read_in_flight() -> None:
    """Interval and unlock signals must not build a queue behind a slow BLE read."""
    started = asyncio.Event()
    release = asyncio.Event()

    async def list_audit_events(*, limit: int):
        assert limit == 50
        started.set()
        await release.wait()
        return ()

    hass = SimpleNamespace(
        async_create_task=lambda target, name: asyncio.create_task(target, name=name)
    )
    service, _physical, _fingerprint, _access_point_id = _service()
    service._hass = hass
    service._provider.list_audit_events.side_effect = list_audit_events
    service._started = True

    service._schedule(service._poll_safely(process=False), "baseline")
    await started.wait()
    service._schedule(service._poll_safely(process=True), "interval")
    service._schedule(service._poll_safely(process=True), "unlock")

    assert service._provider.list_audit_events.await_count == 1
    release.set()
    assert service._poll_task is not None
    await service._poll_task
    await asyncio.sleep(0)
    assert service._poll_task is None


async def test_stop_cancels_the_active_bluetooth_read() -> None:
    """Unload must not leave a local Nuki audit operation running."""
    started = asyncio.Event()

    async def list_audit_events(*, limit: int):
        assert limit == 50
        started.set()
        await asyncio.Event().wait()

    hass = SimpleNamespace(
        async_create_task=lambda target, name: asyncio.create_task(target, name=name)
    )
    service, _physical, _fingerprint, _access_point_id = _service()
    service._hass = hass
    service._provider.list_audit_events.side_effect = list_audit_events
    service._started = True

    service._schedule(service._poll_safely(process=False), "baseline")
    await started.wait()
    await service.async_stop()

    assert service._poll_task is None
