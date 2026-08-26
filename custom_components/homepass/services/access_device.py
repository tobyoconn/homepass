"""Application service for Door-associated access devices."""

from __future__ import annotations

import logging
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Protocol

from ..models import (
    AccessDevice,
    AccessDeviceSetupState,
    KeypadOperation,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    from uuid import UUID

    from ..access_device_discovery import DiscoveredAccessDevice
    from ..repositories import AccessDeviceRepository
    from .access_point import AccessPointService

_LOGGER = logging.getLogger(__name__)


class AccessDeviceDiscovery(Protocol):
    async def discover_supported(self) -> tuple[DiscoveredAccessDevice, ...]: ...


@dataclass(frozen=True, slots=True)
class AccessDeviceView:
    """One managed device with its current Door and Home Assistant state."""

    device: AccessDevice
    access_point_name: str
    available: bool
    battery_percentage: int | None = None
    battery_status: str | None = None
    battery_entity_id: str | None = None

    def to_dict(self) -> dict[str, object]:
        data: dict[str, object] = dict(self.device.to_dict())
        data.pop("home_assistant_device_id", None)
        data["access_point_name"] = self.access_point_name
        data["available"] = self.available
        if self.battery_percentage is not None:
            data["battery_percentage"] = self.battery_percentage
        if self.battery_status is not None:
            data["battery_status"] = self.battery_status
        if self.battery_entity_id is not None:
            data["battery_entity_id"] = self.battery_entity_id
        return data


class AccessDeviceService:
    """Manage accessories while leaving physical ownership with Home Assistant."""

    def __init__(
        self,
        repository: AccessDeviceRepository,
        discovery: AccessDeviceDiscovery,
        access_point_service: AccessPointService,
    ) -> None:
        self._repository = repository
        self._discovery = discovery
        self._access_point_service = access_point_service
        self._change_listener: Callable[[], Awaitable[None]] | None = None

    def set_change_listener(self, listener: Callable[[], Awaitable[None]]) -> None:
        """Refresh transport bindings after durable device associations change."""
        self._change_listener = listener

    async def _notify_changed(self) -> None:
        if self._change_listener is None:
            return
        try:
            await self._change_listener()
        except Exception:  # noqa: BLE001 - the durable device change has already succeeded
            _LOGGER.warning("HomePASS could not refresh access-device transports")

    async def list_overview(
        self,
    ) -> tuple[tuple[AccessDeviceView, ...], tuple[dict[str, object], ...]]:
        """Return managed devices and unassigned candidates from one discovery pass."""
        managed_devices = await self._repository.list_all()
        access_points = {
            item.id: item for item in await self._access_point_service.list_access_points()
        }
        discovered_devices = await self._discovery.discover_supported()
        discovered = {item.home_assistant_device_id: item for item in discovered_devices}
        views: list[AccessDeviceView] = []
        for device in managed_devices:
            access_point = access_points.get(device.access_point_id)
            if access_point is None:
                continue
            physical = discovered.get(device.home_assistant_device_id)
            views.append(
                AccessDeviceView(
                    device=device,
                    access_point_name=access_point.display_name,
                    available=physical.available if physical is not None else False,
                    battery_percentage=(
                        physical.battery_percentage if physical is not None else None
                    ),
                    battery_status=physical.battery_status if physical is not None else None,
                    battery_entity_id=(
                        physical.battery_entity_id if physical is not None else None
                    ),
                )
            )
        managed_ids = {item.home_assistant_device_id for item in managed_devices}
        candidates = tuple(
            item.to_dict()
            for item in discovered_devices
            if item.home_assistant_device_id not in managed_ids
        )
        return tuple(views), candidates

    async def reconcile_pin_capabilities(self) -> None:
        """Restore keypad-backed PIN capability from durable device associations."""
        access_point_ids = {
            device.access_point_id
            for device in await self._repository.list_all()
            if device.enabled
        }
        for access_point_id in access_point_ids:
            await self._access_point_service.set_keypad_pin_capable(
                access_point_id,
                enabled=True,
            )

    async def list_views(self) -> tuple[AccessDeviceView, ...]:
        views, _candidates = await self.list_overview()
        return views

    async def list_candidates(self) -> tuple[dict[str, object], ...]:
        _views, candidates = await self.list_overview()
        return candidates

    async def add_keypad(
        self,
        *,
        home_assistant_device_id: str,
        access_point_id: UUID,
        display_name: str | None = None,
    ) -> AccessDeviceView:
        candidates = {
            item.home_assistant_device_id: item
            for item in await self._discovery.discover_supported()
        }
        candidate = candidates.get(home_assistant_device_id)
        if candidate is None:
            raise ValueError("Pair a supported Frient KEPZB-110 keypad with Home Assistant first")
        access_point = await self._access_point_service.get_access_point(access_point_id)
        await self._access_point_service.set_keypad_pin_capable(
            access_point_id,
            enabled=True,
        )
        device = await self._repository.upsert(
            AccessDevice(
                display_name=display_name or candidate.display_name,
                home_assistant_device_id=home_assistant_device_id,
                access_point_id=access_point_id,
                integration=candidate.integration,
                zigbee_ieee_address=candidate.zigbee_ieee_address,
                zigbee2mqtt_base_topic=candidate.zigbee2mqtt_base_topic,
                zigbee2mqtt_friendly_name=candidate.zigbee2mqtt_friendly_name,
            )
        )
        await self._notify_changed()
        return AccessDeviceView(
            device,
            access_point.display_name,
            candidate.available,
            candidate.battery_percentage,
            candidate.battery_status,
            candidate.battery_entity_id,
        )

    async def update(
        self,
        device_id: UUID,
        *,
        access_point_id: UUID | None = None,
        display_name: str | None = None,
        enabled: bool | None = None,
        button_actions: dict[str, str] | None = None,
    ) -> AccessDeviceView:
        current = await self._repository.get(device_id)
        target_access_point_id = access_point_id or current.access_point_id
        target = await self._access_point_service.get_access_point(target_access_point_id)
        actions = current.button_actions
        if button_actions is not None:
            actions = {key: KeypadOperation(value) for key, value in button_actions.items()}
        updated = await self._repository.upsert(
            replace(
                current,
                display_name=display_name if display_name is not None else current.display_name,
                access_point_id=target_access_point_id,
                enabled=enabled if enabled is not None else current.enabled,
                button_actions=actions,
                updated_at=datetime.now(UTC),
            )
        )
        discovered = {
            item.home_assistant_device_id: item
            for item in await self._discovery.discover_supported()
        }
        physical = discovered.get(updated.home_assistant_device_id)
        await self._notify_changed()
        return AccessDeviceView(
            updated,
            target.display_name,
            physical.available if physical is not None else False,
            physical.battery_percentage if physical is not None else None,
            physical.battery_status if physical is not None else None,
            physical.battery_entity_id if physical is not None else None,
        )

    async def remove(self, device_id: UUID) -> bool:
        current = await self._repository.get(device_id)
        others = tuple(
            device
            for device in await self._repository.list_all()
            if device.id != device_id
            and device.access_point_id == current.access_point_id
            and device.enabled
        )
        changed_capability = not others
        if changed_capability:
            await self._access_point_service.set_keypad_pin_capable(
                current.access_point_id,
                enabled=False,
            )
        try:
            removed = await self._repository.remove(device_id)
            if removed:
                await self._notify_changed()
            return removed
        except Exception:
            if changed_capability:
                await self._access_point_service.set_keypad_pin_capable(
                    current.access_point_id,
                    enabled=True,
                )
            raise

    async def mark_ready_after_hardware_test(self, device_id: UUID) -> AccessDevice:
        """Mark setup ready after an authorized command reaches the shared command boundary."""
        current = await self._repository.get(device_id)
        return await self._repository.upsert(
            replace(
                current,
                setup_state=AccessDeviceSetupState.READY,
                updated_at=datetime.now(UTC),
            )
        )


__all__ = ["AccessDeviceDiscovery", "AccessDeviceService", "AccessDeviceView"]
