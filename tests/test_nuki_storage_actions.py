"""Tests for the read-only Nuki storage status action."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from custom_components.homepass.models import AccessDriver
from custom_components.homepass.nuki_storage_actions import _load_status
from custom_components.homepass.providers import (
    AuthorizationRecord,
    ProviderCommunicationError,
)


async def test_storage_status_distinguishes_homepass_and_existing_pins() -> None:
    """The status snapshot labels ownership without exposing PIN digits."""
    provider = AsyncMock()
    provider.list_authorizations.return_value = (
        AuthorizationRecord("17", "HomePASS user", True),
        AuthorizationRecord("18", "Existing guest", False),
    )
    metadata = AsyncMock()
    metadata.list_all.return_value = (
        SimpleNamespace(
            driver=AccessDriver.NUKI,
            lock_entity_id="lock.front_door",
            slot=17,
        ),
    )
    fingerprints = AsyncMock()
    fingerprints.storage_summary.return_value = {
        "linked_count": 1,
        "entries": [{"person_name": "Alex", "status": "confirmed"}],
        "complete_lock_inventory_available": False,
    }

    result = await _load_status(
        provider,
        "lock.front_door",
        metadata,
        fingerprints,
    )

    assert result["pins"] == {
        "total": 2,
        "managed": 1,
        "existing": 1,
        "entries": [
            {
                "nuki_id": "17",
                "name": "HomePASS user",
                "enabled": True,
                "management": "homepass",
            },
            {
                "nuki_id": "18",
                "name": "Existing guest",
                "enabled": False,
                "management": "existing",
            },
        ],
    }
    assert "123456" not in repr(result)
    assert result["fingerprints"]["complete_lock_inventory_available"] is False


async def test_storage_status_reports_unconfigured_without_bluetooth_calls() -> None:
    """The settings action remains useful before local Nuki pairing exists."""
    metadata = AsyncMock()
    fingerprints = AsyncMock()

    result = await _load_status(None, "", metadata, fingerprints)

    assert result["configured"] is False
    assert result["pins"]["total"] == 0
    metadata.list_all.assert_not_awaited()
    fingerprints.storage_summary.assert_not_awaited()


async def test_storage_status_bounds_a_stalled_bluetooth_scan(monkeypatch) -> None:
    """A transport that never answers must not leave Settings loading forever."""
    blocker = asyncio.Event()
    provider = AsyncMock()
    provider.list_authorizations.side_effect = blocker.wait
    monkeypatch.setattr(
        "custom_components.homepass.nuki_storage_actions._SCAN_ATTEMPT_TIMEOUT",
        0.001,
    )
    monkeypatch.setattr(
        "custom_components.homepass.nuki_storage_actions._SCAN_RETRY_DELAY",
        0,
    )

    with pytest.raises(ProviderCommunicationError, match="timed out"):
        await _load_status(
            provider,
            "lock.front_door",
            AsyncMock(),
            AsyncMock(),
        )

    assert provider.list_authorizations.await_count == 3
