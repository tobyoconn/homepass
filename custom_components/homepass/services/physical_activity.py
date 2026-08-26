"""Home Assistant physical door observations recorded as canonical Activity."""

from __future__ import annotations

import asyncio
import hashlib
import logging
from collections.abc import Callable, Coroutine, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any, Protocol
from uuid import UUID

from homeassistant.components.zwave_js.const import ZWAVE_JS_NOTIFICATION_EVENT
from homeassistant.const import STATE_OFF, STATE_ON, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import (
    CALLBACK_TYPE,
    Event,
    EventStateChangedData,
    HomeAssistant,
    State,
    callback,
)
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.event import async_track_state_change_event

from ..models import (
    AccessPoint,
    ActivityAccessMethod,
    ActivityActorType,
    ActivityEventType,
    ActivityNavigationKind,
    ActivityNavigationReference,
    ActivitySource,
    LockEventOrigin,
    Person,
)
from .access_point import AccessPointChangeListener, AccessPointSummary
from .activity import ActivityEventProposal, ActivityService
from .lock_event_correlation import LockCommandCorrelationService, LockStableState

_LOGGER = logging.getLogger(__name__)
_TRANSITIONAL_LOCK_STATES = frozenset({"locking", "unlocking", "opening"})
_UNLOCK_EVIDENCE_WAIT_SECONDS = 5.0
_PROVIDER_UNLOCK_EVIDENCE_WAIT_SECONDS = 12.0
_UNLOCK_EVIDENCE_WINDOW = timedelta(seconds=12)
_ACCESS_CONTROL_COMMAND_CLASS = 113
_ACCESS_CONTROL_NOTIFICATION_TYPE = 6
_MANUAL_UNLOCK_EVENT = 2
_REMOTE_UNLOCK_EVENT = 4
_KEYPAD_UNLOCK_EVENT = 6


class PhysicalEntityKind(StrEnum):
    """Supported integration-neutral Home Assistant entity roles."""

    LOCK = "lock"
    CONTACT = "contact"


class NormalizedPhysicalState(StrEnum):
    """Canonical state interpretation without retaining raw Home Assistant values."""

    LOCKED = "locked"
    UNLOCKED = "unlocked"
    OPEN = "open"
    CLOSED = "closed"
    TRANSITIONAL = "transitional"
    UNAVAILABLE = "unavailable"
    UNSUPPORTED = "unsupported"


_EVENT_TYPES = {
    NormalizedPhysicalState.LOCKED: ActivityEventType.DOOR_LOCKED,
    NormalizedPhysicalState.UNLOCKED: ActivityEventType.DOOR_UNLOCKED,
    NormalizedPhysicalState.OPEN: ActivityEventType.DOOR_OPENED,
    NormalizedPhysicalState.CLOSED: ActivityEventType.DOOR_CLOSED,
}
_STABLE_STATES = frozenset(_EVENT_TYPES)


def _lock_origin_actor(
    origin: LockEventOrigin,
) -> tuple[ActivityActorType, ActivityAccessMethod | None]:
    if origin is LockEventOrigin.HOMEPASS_MANUAL:
        return ActivityActorType.REMOTE, ActivityAccessMethod.REMOTE
    if origin is LockEventOrigin.HOMEPASS_AUTOMATIC:
        return ActivityActorType.SYSTEM, ActivityAccessMethod.REMOTE
    if origin is LockEventOrigin.HOMEPASS_KEYPAD:
        return ActivityActorType.CREDENTIAL, ActivityAccessMethod.KEYPAD
    if origin is LockEventOrigin.NFC_PASSKEY:
        return ActivityActorType.REMOTE, ActivityAccessMethod.REMOTE
    if origin is LockEventOrigin.PHYSICAL_AT_DOOR:
        return ActivityActorType.MANUAL, ActivityAccessMethod.MANUAL
    return ActivityActorType.UNKNOWN, None


@dataclass(frozen=True, slots=True)
class UnlockMethodEvidence:
    """Sanitized authoritative unlock evidence without credential material."""

    access_method: ActivityAccessMethod
    slot: int | None = None


def classify_zwave_unlock_notification(data: Mapping[str, Any]) -> UnlockMethodEvidence:
    """Classify the Access Control values confirmed on supported Z-Wave locks."""
    if not isinstance(data, Mapping):
        raise TypeError("Z-Wave notification data must be a mapping")
    command_class = data.get("command_class")
    notification_type = data.get("type")
    event = data.get("event")
    if (
        isinstance(command_class, bool)
        or not isinstance(command_class, int)
        or command_class != _ACCESS_CONTROL_COMMAND_CLASS
        or isinstance(notification_type, bool)
        or not isinstance(notification_type, int)
        or notification_type != _ACCESS_CONTROL_NOTIFICATION_TYPE
        or isinstance(event, bool)
        or not isinstance(event, int)
    ):
        return UnlockMethodEvidence(ActivityAccessMethod.UNKNOWN)
    if event == _MANUAL_UNLOCK_EVENT:
        return UnlockMethodEvidence(ActivityAccessMethod.MANUAL)
    if event == _REMOTE_UNLOCK_EVENT:
        return UnlockMethodEvidence(ActivityAccessMethod.REMOTE)
    if event != _KEYPAD_UNLOCK_EVENT:
        return UnlockMethodEvidence(ActivityAccessMethod.UNKNOWN)

    parameters = data.get("parameters")
    if parameters is None:
        return UnlockMethodEvidence(ActivityAccessMethod.KEYPAD)
    if not isinstance(parameters, Mapping):
        return UnlockMethodEvidence(ActivityAccessMethod.UNKNOWN)
    slot = parameters.get("userId")
    if slot is None:
        return UnlockMethodEvidence(ActivityAccessMethod.KEYPAD)
    if isinstance(slot, bool) or not isinstance(slot, int) or slot < 1:
        return UnlockMethodEvidence(ActivityAccessMethod.KEYPAD)
    return UnlockMethodEvidence(ActivityAccessMethod.KEYPAD, slot)


def normalize_physical_state(
    kind: PhysicalEntityKind, state: str | None
) -> NormalizedPhysicalState:
    """Normalize standard Home Assistant lock/contact states into physical facts."""
    if not isinstance(kind, PhysicalEntityKind):
        raise TypeError("Physical entity kind is invalid")
    if state is None or state in {STATE_UNKNOWN, STATE_UNAVAILABLE}:
        return NormalizedPhysicalState.UNAVAILABLE
    if kind is PhysicalEntityKind.LOCK:
        if state == "locked":
            return NormalizedPhysicalState.LOCKED
        if state == "unlocked":
            return NormalizedPhysicalState.UNLOCKED
        if state in _TRANSITIONAL_LOCK_STATES:
            return NormalizedPhysicalState.TRANSITIONAL
        return NormalizedPhysicalState.UNSUPPORTED
    if state == STATE_ON:
        return NormalizedPhysicalState.OPEN
    if state == STATE_OFF:
        return NormalizedPhysicalState.CLOSED
    return NormalizedPhysicalState.UNSUPPORTED


class PhysicalActivityAccessPointSource(Protocol):
    """Provide durable managed policy scope with current HA associations."""

    async def list_access_point_summaries(self) -> tuple[AccessPointSummary, ...]: ...

    def add_change_listener(self, listener: AccessPointChangeListener) -> Callable[[], None]: ...


class PhysicalActivityKeypadAttribution(Protocol):
    """Resolve exact non-secret keypad evidence without inferring an identity."""

    async def resolve_person(self, access_point_id: UUID, slot: int) -> Person | None: ...


@dataclass(frozen=True, slots=True)
class _MonitoredEntity:
    access_point: AccessPoint
    kind: PhysicalEntityKind


@dataclass(slots=True)
class _PendingUnlock:
    binding: _MonitoredEntity
    entity_id: str
    event: Event[EventStateChangedData]
    new_state: State | None
    occurred_at: datetime
    timer: asyncio.TimerHandle | None = None


@dataclass(slots=True)
class _CachedUnlockEvidence:
    evidence: UnlockMethodEvidence
    observed_at: datetime
    timer: asyncio.TimerHandle | None = None


class PhysicalActivityIngestionService:
    """Observe enrolled Door state changes and record only stable physical facts."""

    def __init__(
        self,
        hass: HomeAssistant,
        access_points: PhysicalActivityAccessPointSource,
        activity_service: ActivityService,
        lock_correlations: LockCommandCorrelationService,
        keypad_attribution: PhysicalActivityKeypadAttribution | None = None,
    ) -> None:
        self._hass = hass
        self._access_points = access_points
        self._activity_service = activity_service
        self._lock_correlations = lock_correlations
        self._keypad_attribution = keypad_attribution
        self._monitored: dict[str, _MonitoredEntity] = {}
        self._notification_devices: dict[str, tuple[str, _MonitoredEntity]] = {}
        self._provider_evidence_entities: set[str] = set()
        self._last_stable: dict[str, NormalizedPhysicalState] = {}
        self._established: set[str] = set()
        self._pending_unlocks: dict[str, _PendingUnlock] = {}
        self._unlock_evidence: dict[str, _CachedUnlockEvidence] = {}
        self._recent_unlocks: dict[str, datetime] = {}
        self._state_unsubscribe: CALLBACK_TYPE | None = None
        self._zwave_unsubscribe: CALLBACK_TYPE | None = None
        self._registry_unsubscribe: CALLBACK_TYPE | None = None
        self._access_point_unsubscribe: Callable[[], None] | None = None
        self._refresh_lock = asyncio.Lock()
        self._tasks: set[asyncio.Task[None]] = set()
        self._started = False

    @property
    def started(self) -> bool:
        """Return whether subscription lifecycle ownership is active."""
        return self._started

    async def async_start(self) -> None:
        """Register lifecycle listeners and establish a noise-free state baseline."""
        if self._started:
            return
        self._started = True
        self._registry_unsubscribe = self._hass.bus.async_listen(
            er.EVENT_ENTITY_REGISTRY_UPDATED,
            self._handle_registry_update,
        )
        self._zwave_unsubscribe = self._hass.bus.async_listen(
            ZWAVE_JS_NOTIFICATION_EVENT,
            self._handle_zwave_notification,
        )
        self._access_point_unsubscribe = self._access_points.add_change_listener(
            self._handle_access_point_change
        )
        await self._async_refresh_safely()

    async def async_stop(self) -> None:
        """Release every listener and finish already accepted secondary work."""
        if not self._started:
            self._lock_correlations.clear()
            return
        self._started = False
        for unsubscribe in (
            self._state_unsubscribe,
            self._zwave_unsubscribe,
            self._registry_unsubscribe,
            self._access_point_unsubscribe,
        ):
            if unsubscribe is not None:
                unsubscribe()
        self._state_unsubscribe = None
        self._zwave_unsubscribe = None
        self._registry_unsubscribe = None
        self._access_point_unsubscribe = None
        for pending in self._pending_unlocks.values():
            if pending.timer is not None:
                pending.timer.cancel()
        for cached in self._unlock_evidence.values():
            if cached.timer is not None:
                cached.timer.cancel()
        self._pending_unlocks.clear()
        self._unlock_evidence.clear()
        self._recent_unlocks.clear()
        self._monitored.clear()
        self._notification_devices.clear()
        self._provider_evidence_entities.clear()
        self._last_stable.clear()
        self._established.clear()
        if self._tasks:
            await asyncio.gather(*tuple(self._tasks), return_exceptions=True)
        self._lock_correlations.clear()

    async def async_refresh(self) -> None:
        """Refresh monitored associations without emitting physical Activity."""
        await self._async_refresh_safely()

    def register_unlock_evidence_entity(self, entity_id: str) -> Callable[[], None]:
        """Declare that a local provider can classify unlocks for one lock entity."""
        if not isinstance(entity_id, str) or not entity_id.startswith("lock."):
            raise ValueError("Unlock evidence entity must be a lock entity")
        self._provider_evidence_entities.add(entity_id)

        def unsubscribe() -> None:
            self._provider_evidence_entities.discard(entity_id)
            self._discard_unlock_evidence(entity_id)

        return unsubscribe

    def accept_provider_unlock_evidence(
        self,
        entity_id: str,
        evidence: UnlockMethodEvidence,
        observed_at: datetime,
    ) -> bool:
        """Correlate sanitized local-provider evidence with a physical unlock."""
        binding = self._monitored.get(entity_id)
        if (
            not self._started
            or binding is None
            or binding.kind is not PhysicalEntityKind.LOCK
            or entity_id not in self._provider_evidence_entities
            or evidence.access_method
            not in {ActivityAccessMethod.KEYPAD, ActivityAccessMethod.FINGERPRINT}
        ):
            return False
        self._accept_unlock_evidence(entity_id, binding, evidence, observed_at)
        return True

    async def _async_refresh_safely(self) -> None:
        if not self._started:
            return
        try:
            async with self._refresh_lock:
                summaries = await self._access_points.list_access_point_summaries()
                self._replace_monitored_entities(self._monitored_entities(summaries))
        except Exception:  # noqa: BLE001 - ingestion cannot disrupt HomePASS
            _LOGGER.warning("HomePASS could not refresh physical Activity subscriptions")

    @staticmethod
    def _monitored_entities(
        summaries: tuple[AccessPointSummary, ...],
    ) -> dict[str, _MonitoredEntity]:
        monitored: dict[str, _MonitoredEntity] = {}
        for summary in sorted(summaries, key=lambda item: str(item.access_point.id)):
            if not summary.access_point.enabled:
                continue
            sources = (
                (
                    summary.state.lock_entity_id
                    if summary.control_profile == "lock"
                    else None,
                    PhysicalEntityKind.LOCK,
                ),
                (summary.state.door_entity_id, PhysicalEntityKind.CONTACT),
            )
            for entity_id, kind in sources:
                if entity_id is not None:
                    monitored.setdefault(
                        entity_id,
                        _MonitoredEntity(summary.access_point, kind),
                    )
        return monitored

    def _replace_monitored_entities(self, monitored: dict[str, _MonitoredEntity]) -> None:
        previous = self._monitored
        previous_ids = frozenset(previous)
        next_ids = frozenset(monitored)
        if previous_ids != next_ids and self._state_unsubscribe is not None:
            self._state_unsubscribe()
            self._state_unsubscribe = None

        for entity_id in previous_ids - next_ids:
            self._last_stable.pop(entity_id, None)
            self._established.discard(entity_id)
            self._cancel_pending_unlock(entity_id)
            self._discard_unlock_evidence(entity_id)
            self._recent_unlocks.pop(entity_id, None)
        for entity_id, binding in monitored.items():
            previous_binding = previous.get(entity_id)
            if (
                previous_binding is None
                or previous_binding.kind is not binding.kind
                or previous_binding.access_point.id != binding.access_point.id
            ):
                self._establish_baseline(entity_id, binding.kind)

        self._monitored = monitored
        registry = er.async_get(self._hass)
        self._notification_devices = {}
        for entity_id, binding in monitored.items():
            if binding.kind is not PhysicalEntityKind.LOCK:
                continue
            registry_entry = registry.async_get(entity_id)
            if registry_entry is not None and registry_entry.device_id is not None:
                self._notification_devices.setdefault(
                    registry_entry.device_id,
                    (entity_id, binding),
                )
        if previous_ids != next_ids and next_ids:
            self._state_unsubscribe = async_track_state_change_event(
                self._hass,
                sorted(next_ids),
                self._handle_state_change,
            )

    def _establish_baseline(self, entity_id: str, kind: PhysicalEntityKind) -> None:
        state = self._hass.states.get(entity_id)
        normalized = normalize_physical_state(kind, state.state if state is not None else None)
        if normalized in _STABLE_STATES:
            self._last_stable[entity_id] = normalized
            self._established.add(entity_id)
            return
        self._last_stable.pop(entity_id, None)
        self._established.discard(entity_id)

    @callback
    def _handle_registry_update(self, _event: Event[er.EventEntityRegistryUpdatedData]) -> None:
        self._schedule(self._async_refresh_safely(), "HomePASS physical Activity refresh")

    async def _handle_access_point_change(self) -> None:
        await self._async_refresh_safely()

    @callback
    def _handle_state_change(self, event: Event[EventStateChangedData]) -> None:
        self._schedule(
            self._async_process_state_change_safely(event),
            "HomePASS physical Activity event",
        )

    @callback
    def _handle_zwave_notification(self, event: Event[dict[str, Any]]) -> None:
        """Accept only sanitized Access Control evidence for a monitored lock."""
        device_id = event.data.get("device_id")
        if not isinstance(device_id, str):
            return
        monitored = self._notification_devices.get(device_id)
        if monitored is None:
            return
        evidence = classify_zwave_unlock_notification(event.data)
        if evidence.access_method is ActivityAccessMethod.UNKNOWN:
            return
        entity_id, binding = monitored
        self._accept_unlock_evidence(entity_id, binding, evidence, event.time_fired.astimezone(UTC))

    def _schedule(self, target: Coroutine[Any, Any, None], name: str) -> None:
        if not self._started:
            target.close()
            return
        task: asyncio.Task[None] = self._hass.async_create_task(target, name)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def _async_process_state_change_safely(self, event: Event[EventStateChangedData]) -> None:
        try:
            await self._async_process_state_change(event)
        except Exception:  # noqa: BLE001 - state handling must remain isolated
            _LOGGER.warning("HomePASS could not record a physical Activity event")

    async def _async_process_state_change(self, event: Event[EventStateChangedData]) -> None:
        entity_id = event.data["entity_id"]
        binding = self._monitored.get(entity_id)
        if binding is None:
            return
        new_state: State | None = event.data["new_state"]
        normalized = normalize_physical_state(
            binding.kind,
            new_state.state if new_state is not None else None,
        )
        if normalized not in _STABLE_STATES:
            return
        if entity_id not in self._established:
            self._last_stable[entity_id] = normalized
            self._established.add(entity_id)
            return
        previous = self._last_stable.get(entity_id)
        if previous is normalized:
            return
        self._last_stable[entity_id] = normalized
        occurred_at = event.time_fired.astimezone(UTC)
        actor_type = ActivityActorType.UNKNOWN
        actor_id: UUID | None = None
        actor_name: str | None = None
        person_id: UUID | None = None
        person_name: str | None = None
        access_method: ActivityAccessMethod | None = None
        correlation_id = None
        attributes: dict[str, str] = {}
        if binding.kind is PhysicalEntityKind.LOCK:
            pending = self._lock_correlations.consume(
                access_point_id=binding.access_point.id,
                confirmed_state=LockStableState(normalized.value),
                confirmed_at=occurred_at,
            )
            origin = pending.origin if pending is not None else LockEventOrigin.UNKNOWN
            actor_type, access_method = _lock_origin_actor(origin)
            if (
                origin in {LockEventOrigin.NFC_PASSKEY, LockEventOrigin.HOMEPASS_KEYPAD}
                and pending is not None
                and pending.person_id is not None
                and pending.person_name is not None
            ):
                actor_type = ActivityActorType.PERSON
                actor_id = pending.person_id
                actor_name = pending.person_name
                person_id = pending.person_id
                person_name = pending.person_name
            if (
                normalized is not NormalizedPhysicalState.UNLOCKED
                and origin is not LockEventOrigin.HOMEPASS_KEYPAD
            ):
                access_method = None
            correlation_id = pending.command_id if pending is not None else None
            attributes["lock_origin"] = origin.value
            if (
                normalized is NormalizedPhysicalState.UNLOCKED
                and pending is None
                and self._supports_unlock_evidence(entity_id)
            ):
                cached = self._consume_unlock_evidence(entity_id, occurred_at)
                if cached is not None:
                    await self._async_record_unlock_with_evidence(
                        binding,
                        entity_id,
                        event,
                        new_state,
                        occurred_at,
                        cached,
                    )
                else:
                    self._queue_pending_unlock(
                        binding,
                        entity_id,
                        event,
                        new_state,
                        occurred_at,
                    )
                return
        elif binding.kind is PhysicalEntityKind.CONTACT:
            confirmed_state = (
                LockStableState.UNLOCKED
                if normalized is NormalizedPhysicalState.OPEN
                else LockStableState.LOCKED
            )
            pending = self._lock_correlations.consume(
                access_point_id=binding.access_point.id,
                confirmed_state=confirmed_state,
                confirmed_at=occurred_at,
            )
            if pending is not None:
                actor_type, access_method = _lock_origin_actor(pending.origin)
                correlation_id = pending.command_id
                if pending.person_id is not None and pending.person_name is not None:
                    actor_type = ActivityActorType.PERSON
                    actor_id = pending.person_id
                    actor_name = pending.person_name
                    person_id = pending.person_id
                    person_name = pending.person_name
        await self._record_transition(
            binding=binding,
            entity_id=entity_id,
            normalized=normalized,
            event=event,
            new_state=new_state,
            occurred_at=occurred_at,
            actor_type=actor_type,
            access_method=access_method,
            attributes=attributes,
            correlation_id=correlation_id,
            actor_id=actor_id,
            actor_name=actor_name,
            person_id=person_id,
            person_name=person_name,
        )
        if normalized is NormalizedPhysicalState.UNLOCKED:
            self._recent_unlocks[entity_id] = occurred_at

    def _supports_unlock_evidence(self, entity_id: str) -> bool:
        return entity_id in self._provider_evidence_entities or any(
            monitored_id == entity_id
            for monitored_id, _binding in self._notification_devices.values()
        )

    def _queue_pending_unlock(
        self,
        binding: _MonitoredEntity,
        entity_id: str,
        event: Event[EventStateChangedData],
        new_state: State | None,
        occurred_at: datetime,
    ) -> None:
        self._cancel_pending_unlock(entity_id)
        pending = _PendingUnlock(binding, entity_id, event, new_state, occurred_at)
        wait_seconds = (
            _PROVIDER_UNLOCK_EVIDENCE_WAIT_SECONDS
            if entity_id in self._provider_evidence_entities
            else _UNLOCK_EVIDENCE_WAIT_SECONDS
        )
        pending.timer = asyncio.get_running_loop().call_later(
            wait_seconds,
            self._expire_pending_unlock,
            entity_id,
            pending,
        )
        self._pending_unlocks[entity_id] = pending

    @callback
    def _expire_pending_unlock(self, entity_id: str, pending: _PendingUnlock) -> None:
        if self._pending_unlocks.get(entity_id) is not pending:
            return
        self._pending_unlocks.pop(entity_id, None)
        self._schedule(
            self._async_record_unlock_with_evidence(
                pending.binding,
                entity_id,
                pending.event,
                pending.new_state,
                pending.occurred_at,
                UnlockMethodEvidence(ActivityAccessMethod.UNKNOWN),
            ),
            "HomePASS physical unlock Activity",
        )

    def _cancel_pending_unlock(self, entity_id: str) -> _PendingUnlock | None:
        pending = self._pending_unlocks.pop(entity_id, None)
        if pending is not None and pending.timer is not None:
            pending.timer.cancel()
        return pending

    def _accept_unlock_evidence(
        self,
        entity_id: str,
        binding: _MonitoredEntity,
        evidence: UnlockMethodEvidence,
        observed_at: datetime,
    ) -> None:
        pending = self._pending_unlocks.get(entity_id)
        if pending is not None and self._within_unlock_window(pending.occurred_at, observed_at):
            self._cancel_pending_unlock(entity_id)
            self._schedule(
                self._async_record_unlock_with_evidence(
                    binding,
                    entity_id,
                    pending.event,
                    pending.new_state,
                    pending.occurred_at,
                    evidence,
                ),
                "HomePASS classified unlock Activity",
            )
            return
        recent = self._recent_unlocks.get(entity_id)
        if recent is not None and self._within_unlock_window(recent, observed_at):
            return
        self._discard_unlock_evidence(entity_id)
        cached = _CachedUnlockEvidence(evidence, observed_at)
        cached.timer = asyncio.get_running_loop().call_later(
            _UNLOCK_EVIDENCE_WAIT_SECONDS,
            self._discard_unlock_evidence,
            entity_id,
        )
        self._unlock_evidence[entity_id] = cached

    def _consume_unlock_evidence(
        self, entity_id: str, occurred_at: datetime
    ) -> UnlockMethodEvidence | None:
        cached = self._unlock_evidence.get(entity_id)
        if cached is None:
            return None
        self._discard_unlock_evidence(entity_id)
        if not self._within_unlock_window(cached.observed_at, occurred_at):
            return None
        return cached.evidence

    def _discard_unlock_evidence(self, entity_id: str) -> None:
        cached = self._unlock_evidence.pop(entity_id, None)
        if cached is not None and cached.timer is not None:
            cached.timer.cancel()

    @staticmethod
    def _within_unlock_window(left: datetime, right: datetime) -> bool:
        return abs(right - left) <= _UNLOCK_EVIDENCE_WINDOW

    async def _async_record_unlock_with_evidence(
        self,
        binding: _MonitoredEntity,
        entity_id: str,
        event: Event[EventStateChangedData],
        new_state: State | None,
        occurred_at: datetime,
        evidence: UnlockMethodEvidence,
    ) -> None:
        actor_type = {
            ActivityAccessMethod.KEYPAD: ActivityActorType.CREDENTIAL,
            ActivityAccessMethod.FINGERPRINT: ActivityActorType.CREDENTIAL,
            ActivityAccessMethod.MANUAL: ActivityActorType.MANUAL,
            ActivityAccessMethod.REMOTE: ActivityActorType.REMOTE,
            ActivityAccessMethod.UNKNOWN: ActivityActorType.UNKNOWN,
        }[evidence.access_method]
        person: Person | None = None
        if (
            evidence.access_method
            in {ActivityAccessMethod.KEYPAD, ActivityAccessMethod.FINGERPRINT}
            and evidence.slot is not None
            and self._keypad_attribution is not None
        ):
            try:
                person = await self._keypad_attribution.resolve_person(
                    binding.access_point.id,
                    evidence.slot,
                )
            except Exception:  # noqa: BLE001 - attribution failure must remain unidentified
                person = None
        if person is not None:
            actor_type = ActivityActorType.PERSON
        origin = (
            LockEventOrigin.PHYSICAL_AT_DOOR
            if evidence.access_method is ActivityAccessMethod.MANUAL
            else LockEventOrigin.UNKNOWN
        )
        await self._record_transition(
            binding=binding,
            entity_id=entity_id,
            normalized=NormalizedPhysicalState.UNLOCKED,
            event=event,
            new_state=new_state,
            occurred_at=occurred_at,
            actor_type=actor_type,
            access_method=evidence.access_method,
            attributes={"lock_origin": origin.value},
            person=person,
        )
        self._recent_unlocks[entity_id] = occurred_at

    async def _record_transition(
        self,
        *,
        binding: _MonitoredEntity,
        entity_id: str,
        normalized: NormalizedPhysicalState,
        event: Event[EventStateChangedData],
        new_state: State | None,
        occurred_at: datetime,
        actor_type: ActivityActorType,
        access_method: ActivityAccessMethod | None,
        attributes: dict[str, str],
        correlation_id: UUID | None = None,
        person: Person | None = None,
        actor_id: UUID | None = None,
        actor_name: str | None = None,
        person_id: UUID | None = None,
        person_name: str | None = None,
    ) -> None:
        resolved_person_id = person.person_id if person is not None else person_id
        resolved_person_name = person.display_name if person is not None else person_name
        await self._activity_service.record(
            ActivityEventProposal(
                event_type=_EVENT_TYPES[normalized],
                occurred_at=occurred_at,
                source=ActivitySource.HOME_ASSISTANT,
                actor_type=actor_type,
                actor_id=person.person_id if person is not None else actor_id,
                actor_name=person.display_name if person is not None else actor_name,
                access_method=access_method,
                door_id=binding.access_point.id,
                door_name=binding.access_point.display_name,
                person_id=resolved_person_id,
                person_name=resolved_person_name,
                attributes=attributes,
                navigation=(
                    ActivityNavigationReference(
                        ActivityNavigationKind.DOOR,
                        binding.access_point.id,
                    ),
                ),
                correlation_id=correlation_id,
                source_event_key=self._source_event_key(
                    binding,
                    entity_id,
                    normalized,
                    event,
                    new_state,
                ),
            )
        )

    @staticmethod
    def _source_event_key(
        binding: _MonitoredEntity,
        entity_id: str,
        current: NormalizedPhysicalState,
        event: Event[EventStateChangedData],
        new_state: State | None,
    ) -> str:
        context_id = new_state.context.id if new_state is not None else event.context.id
        state_changed = new_state.last_changed.isoformat() if new_state is not None else "missing"
        material = "\x1f".join(
            (
                str(binding.access_point.id),
                binding.kind.value,
                entity_id,
                current.value,
                event.time_fired.isoformat(),
                state_changed,
                context_id,
            )
        )
        return f"ha-physical:{hashlib.sha256(material.encode()).hexdigest()}"


__all__ = [
    "NormalizedPhysicalState",
    "PhysicalActivityIngestionService",
    "PhysicalEntityKind",
    "UnlockMethodEvidence",
    "classify_zwave_unlock_notification",
    "normalize_physical_state",
]
