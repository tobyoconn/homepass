"""Monitor discovered Home Assistant batteries and record threshold crossings."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import timedelta
from typing import TYPE_CHECKING, Protocol

from homeassistant.const import EVENT_STATE_CHANGED
from homeassistant.core import CALLBACK_TYPE, Event, EventStateChangedData, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.event import async_track_time_interval

from ..battery import BatteryStatus, read_battery_source
from ..models import (
    ActivityActorType,
    ActivityEventType,
    ActivityNavigationKind,
    ActivityNavigationReference,
    ActivitySource,
)
from .activity import ActivityEventProposal

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Coroutine
    from datetime import datetime
    from uuid import UUID

    from homeassistant.core import HomeAssistant

    from .access_device import AccessDeviceView
    from .access_point import AccessPointSummary
    from .activity import ActivityService

_LOGGER = logging.getLogger(__name__)
_REFRESH_INTERVAL = timedelta(minutes=15)


class BatteryAccessPoints(Protocol):
    async def list_access_point_summaries(self) -> tuple[AccessPointSummary, ...]: ...

    def add_change_listener(
        self, listener: Callable[[], Awaitable[None]]
    ) -> Callable[[], None]: ...


class BatteryAccessDevices(Protocol):
    async def list_views(self) -> tuple[AccessDeviceView, ...]: ...


@dataclass(frozen=True, slots=True)
class _BatteryTarget:
    entity_id: str
    access_point_id: UUID
    display_name: str


class BatteryMonitoringService:
    """Turn supported battery changes into canonical Activity and notifications."""

    def __init__(
        self,
        hass: HomeAssistant,
        access_points: BatteryAccessPoints,
        access_devices: BatteryAccessDevices,
        activity: ActivityService,
    ) -> None:
        self._hass = hass
        self._access_points = access_points
        self._access_devices = access_devices
        self._activity = activity
        self._targets: dict[str, _BatteryTarget] = {}
        self._statuses: dict[str, BatteryStatus] = {}
        self._tasks: set[asyncio.Task[None]] = set()
        self._refresh_lock = asyncio.Lock()
        self._state_unsubscribe: CALLBACK_TYPE | None = None
        self._registry_unsubscribe: CALLBACK_TYPE | None = None
        self._timer_unsubscribe: CALLBACK_TYPE | None = None
        self._access_point_unsubscribe: CALLBACK_TYPE | None = None
        self._started = False

    async def async_start(self) -> None:
        """Establish a quiet baseline before listening for threshold crossings."""
        if self._started:
            return
        self._started = True
        self._state_unsubscribe = self._hass.bus.async_listen(
            EVENT_STATE_CHANGED, self._handle_state_change
        )
        self._registry_unsubscribe = self._hass.bus.async_listen(
            er.EVENT_ENTITY_REGISTRY_UPDATED, self._handle_registry_update
        )
        self._timer_unsubscribe = async_track_time_interval(
            self._hass, self._handle_interval, _REFRESH_INTERVAL
        )
        self._access_point_unsubscribe = self._access_points.add_change_listener(
            self._refresh_safely
        )
        await self._refresh_safely()

    async def async_stop(self) -> None:
        """Release listeners and finish accepted monitoring work."""
        self._started = False
        for unsubscribe in (
            self._state_unsubscribe,
            self._registry_unsubscribe,
            self._timer_unsubscribe,
            self._access_point_unsubscribe,
        ):
            if callable(unsubscribe):
                unsubscribe()
        self._state_unsubscribe = None
        self._registry_unsubscribe = None
        self._timer_unsubscribe = None
        self._access_point_unsubscribe = None
        if self._tasks:
            await asyncio.gather(*tuple(self._tasks), return_exceptions=True)
        self._targets.clear()
        self._statuses.clear()

    @callback
    def _handle_state_change(self, event: Event[EventStateChangedData]) -> None:
        entity_id = event.data["entity_id"]
        if entity_id in self._targets:
            self._schedule(
                self._process_state_change(entity_id, event.time_fired),
                "HomePASS battery state change",
            )

    @callback
    def _handle_registry_update(self, _event: Event[er.EventEntityRegistryUpdatedData]) -> None:
        self._schedule(self._refresh_safely(), "HomePASS battery discovery refresh")

    @callback
    def _handle_interval(self, _now: datetime) -> None:
        self._schedule(self._refresh_safely(), "HomePASS battery periodic refresh")

    def _schedule(self, target: Coroutine[object, object, None], name: str) -> None:
        if not self._started:
            target.close()
            return
        task = self._hass.async_create_task(target, name)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def _refresh_safely(self) -> None:
        if not self._started:
            return
        try:
            async with self._refresh_lock:
                summaries = await self._access_points.list_access_point_summaries()
                devices = await self._access_devices.list_views()
                targets: dict[str, _BatteryTarget] = {}
                for summary in summaries:
                    state = summary.state
                    if state.battery_entity_id is not None:
                        targets.setdefault(
                            state.battery_entity_id,
                            _BatteryTarget(
                                state.battery_entity_id,
                                summary.access_point.id,
                                summary.access_point.display_name,
                            ),
                        )
                    if state.door_sensor_battery_entity_id is not None:
                        targets.setdefault(
                            state.door_sensor_battery_entity_id,
                            _BatteryTarget(
                                state.door_sensor_battery_entity_id,
                                summary.access_point.id,
                                f"{summary.access_point.display_name} door sensor",
                            ),
                        )
                for view in devices:
                    if view.battery_entity_id is not None:
                        targets.setdefault(
                            view.battery_entity_id,
                            _BatteryTarget(
                                view.battery_entity_id,
                                view.device.access_point_id,
                                view.device.display_name,
                            ),
                        )
                previous = self._statuses
                self._targets = targets
                self._statuses = {
                    entity_id: previous.get(entity_id, reading.status)
                    for entity_id in targets
                    if (
                        reading := read_battery_source(self._hass, entity_id, allow_attributes=True)
                    )
                    is not None
                }
        except Exception:  # noqa: BLE001 - monitoring cannot disrupt HomePASS
            _LOGGER.warning("HomePASS could not refresh battery monitoring")

    async def _process_state_change(self, entity_id: str, occurred_at: datetime) -> None:
        target = self._targets.get(entity_id)
        reading = read_battery_source(self._hass, entity_id, allow_attributes=True)
        if target is None or reading is None or reading.status is BatteryStatus.UNKNOWN:
            return
        previous = self._statuses.get(entity_id, BatteryStatus.UNKNOWN)
        self._statuses[entity_id] = reading.status
        if not self._is_escalation(previous, reading.status):
            return
        event_type = (
            ActivityEventType.BATTERY_CRITICAL
            if reading.status is BatteryStatus.CRITICAL
            else ActivityEventType.BATTERY_LOW
        )
        attributes = (
            {"battery_percentage": reading.percentage} if reading.percentage is not None else {}
        )
        await self._activity.record(
            ActivityEventProposal(
                event_type=event_type,
                occurred_at=occurred_at,
                source=ActivitySource.HOME_ASSISTANT,
                actor_type=ActivityActorType.SYSTEM,
                door_id=target.access_point_id,
                door_name=target.display_name,
                attributes=attributes,
                navigation=(
                    ActivityNavigationReference(
                        ActivityNavigationKind.DOOR, target.access_point_id
                    ),
                ),
                source_event_key=(
                    f"battery:{entity_id}:{reading.status.value}:{occurred_at.isoformat()}"
                ),
            )
        )

    @staticmethod
    def _is_escalation(previous: BatteryStatus, current: BatteryStatus) -> bool:
        rank = {
            BatteryStatus.UNKNOWN: -1,
            BatteryStatus.NORMAL: 0,
            BatteryStatus.LOW: 1,
            BatteryStatus.CRITICAL: 2,
        }
        return (
            current in {BatteryStatus.LOW, BatteryStatus.CRITICAL}
            and rank[current] > rank[previous]
        )


__all__ = ["BatteryMonitoringService"]
