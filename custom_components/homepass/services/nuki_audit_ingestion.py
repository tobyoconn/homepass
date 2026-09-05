"""Consume direct Nuki audit evidence for local user attribution."""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import TYPE_CHECKING, Any

from homeassistant.core import CALLBACK_TYPE, Event, EventStateChangedData, callback
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_interval,
)

from ..models import ActivityAccessMethod
from .physical_activity import PhysicalActivityIngestionService, UnlockMethodEvidence

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine
    from uuid import UUID

    from homeassistant.core import HomeAssistant

    from ..providers.base import AuthorizationProvider, ProviderAuditEvent
    from .access_point import AccessPointService
    from .nuki_fingerprint import NukiFingerprintService

_LOGGER = logging.getLogger(__name__)
_POLL_INTERVAL = timedelta(minutes=5)
_POLL_TIMEOUT = 15.0
_SUCCESS_ACTIONS = frozenset({"unlock", "unlatch", "lock_n_go_unlatch"})


class NukiAuditIngestionService:
    """Bridge Nuki audit records into the existing physical Activity pipeline."""

    def __init__(
        self,
        hass: HomeAssistant,
        provider: AuthorizationProvider,
        lock_entity_id: str,
        access_points: AccessPointService,
        physical_activity: PhysicalActivityIngestionService,
        fingerprint: NukiFingerprintService,
    ) -> None:
        self._hass = hass
        self._provider = provider
        self._lock_entity_id = lock_entity_id
        self._access_points = access_points
        self._physical_activity = physical_activity
        self._fingerprint = fingerprint
        self._seen: dict[str, ProviderAuditEvent] = {}
        self._poll_lock = asyncio.Lock()
        self._state_unsubscribe: CALLBACK_TYPE | None = None
        self._timer_unsubscribe: CALLBACK_TYPE | None = None
        self._evidence_unsubscribe: Callable[[], None] | None = None
        self._poll_task: asyncio.Task[None] | None = None
        self._started = False

    async def async_start(self) -> None:
        """Establish a history baseline, then watch for unlocks and new log records."""
        if self._started:
            return
        self._started = True
        self._evidence_unsubscribe = self._physical_activity.register_unlock_evidence_entity(
            self._lock_entity_id
        )
        self._state_unsubscribe = async_track_state_change_event(
            self._hass, [self._lock_entity_id], self._handle_lock_state
        )
        self._timer_unsubscribe = async_track_time_interval(
            self._hass, self._handle_interval, _POLL_INTERVAL
        )
        self._schedule(self._poll_safely(process=False), "HomePASS Nuki audit baseline")

    async def async_stop(self) -> None:
        """Release listeners and finish already accepted polling work."""
        self._started = False
        for unsubscribe in (
            self._state_unsubscribe,
            self._timer_unsubscribe,
            self._evidence_unsubscribe,
        ):
            if unsubscribe is not None:
                unsubscribe()
        self._state_unsubscribe = None
        self._timer_unsubscribe = None
        self._evidence_unsubscribe = None
        task = self._poll_task
        if task is not None:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
            if self._poll_task is task:
                self._poll_task = None
        self._seen.clear()

    @callback
    def _handle_lock_state(self, event: Event[EventStateChangedData]) -> None:
        old_state = event.data["old_state"]
        new_state = event.data["new_state"]
        if (
            new_state is None
            or new_state.state != "unlocked"
            or old_state is not None
            and old_state.state == "unlocked"
        ):
            return
        self._schedule(self._poll_safely(process=True), "HomePASS Nuki audit unlock")

    @callback
    def _handle_interval(self, _now: Any) -> None:
        self._schedule(self._poll_safely(process=True), "HomePASS Nuki audit refresh")

    def _schedule(self, target: Coroutine[Any, Any, None], name: str) -> None:
        if not self._started:
            target.close()
            return
        if self._poll_task is not None and not self._poll_task.done():
            target.close()
            return
        task: asyncio.Task[None] = self._hass.async_create_task(target, name)
        self._poll_task = task
        task.add_done_callback(self._handle_poll_done)

    @callback
    def _handle_poll_done(self, task: asyncio.Task[None]) -> None:
        if self._poll_task is task:
            self._poll_task = None

    async def _poll_safely(self, *, process: bool) -> None:
        try:
            async with self._poll_lock:
                async with asyncio.timeout(_POLL_TIMEOUT):
                    events = await self._provider.list_audit_events(limit=50)
                unseen = tuple(event for event in events if event.external_id not in self._seen)
                for event in events:
                    self._seen[event.external_id] = event
                if len(self._seen) > 200:
                    newest = sorted(
                        self._seen.values(),
                        key=lambda event: event.occurred_at,
                        reverse=True,
                    )[:200]
                    self._seen = {event.external_id: event for event in newest}
                if process:
                    for event in sorted(unseen, key=lambda item: item.occurred_at):
                        await self._process(event)
        except Exception:  # noqa: BLE001 - audit polling must not disrupt HomePASS
            _LOGGER.warning("HomePASS could not refresh the local Nuki audit log")

    async def _process(self, event: ProviderAuditEvent) -> None:
        if (
            event.outcome != "success"
            or event.action not in _SUCCESS_ACTIONS
            or event.source not in {"keypad", "fingerprint"}
            or event.authorization_external_id is None
            or not event.authorization_external_id.isdecimal()
        ):
            return
        access_point_id = await self._access_point_id()
        if access_point_id is None:
            return
        evidence = UnlockMethodEvidence(
            ActivityAccessMethod.FINGERPRINT
            if event.source == "fingerprint"
            else ActivityAccessMethod.KEYPAD,
            int(event.authorization_external_id),
        )
        correlated = self._physical_activity.accept_provider_unlock_evidence(
            self._lock_entity_id, evidence, event.occurred_at
        )
        if event.source == "fingerprint":
            await self._fingerprint.observe_provider_event(
                access_point_id,
                event,
                record_activity=not correlated,
            )

    async def _access_point_id(self) -> UUID | None:
        for summary in await self._access_points.list_access_point_summaries():
            if summary.state.lock_entity_id == self._lock_entity_id:
                return summary.access_point.id
        return None


__all__ = ["NukiAuditIngestionService"]
