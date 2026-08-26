"""Persistence for HomePASS-managed Door accessories."""

from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import UTC, datetime
from typing import TYPE_CHECKING, cast

from ..exceptions import StorageError
from ..models import AccessDevice

if TYPE_CHECKING:
    from collections.abc import Callable
    from uuid import UUID

    from ..storage import HomePassStorageData, HomePassStorageManager, StorageRecord


class AccessDeviceRepository:
    """Store accessories independently from Home Assistant's device registry."""

    def __init__(self, storage: HomePassStorageManager) -> None:
        self._storage = storage
        self._lock = asyncio.Lock()

    async def list_all(self) -> tuple[AccessDevice, ...]:
        try:
            snapshot = await self._storage.async_load()
            return self.list_from_snapshot(snapshot)
        except StorageError:
            raise
        except Exception as err:
            raise StorageError("Unable to load managed HomePASS devices") from err

    async def get(self, device_id: UUID) -> AccessDevice:
        snapshot = await self._storage.async_load()
        try:
            return AccessDevice.from_dict(snapshot["data"]["access_devices"][str(device_id)])
        except (KeyError, TypeError, ValueError) as err:
            raise StorageError("Managed HomePASS device is unavailable") from err

    async def upsert(self, device: AccessDevice) -> AccessDevice:
        def mutate(snapshot: HomePassStorageData) -> AccessDevice:
            records = snapshot["data"]["access_devices"]
            for identifier, raw in records.items():
                existing = AccessDevice.from_dict(raw)
                if (
                    identifier != str(device.id)
                    and existing.home_assistant_device_id == device.home_assistant_device_id
                ):
                    raise ValueError("This Home Assistant device is already managed by HomePASS")
                if (
                    identifier != str(device.id)
                    and device.zigbee_ieee_address is not None
                    and existing.zigbee_ieee_address == device.zigbee_ieee_address
                ):
                    raise ValueError("This Zigbee device is already managed by HomePASS")
                if (
                    identifier != str(device.id)
                    and device.zigbee2mqtt_state_topic is not None
                    and existing.zigbee2mqtt_state_topic == device.zigbee2mqtt_state_topic
                ):
                    raise ValueError("This Zigbee2MQTT topic is already managed by HomePASS")
            current_raw = records.get(str(device.id))
            saved = device
            if current_raw is not None:
                current = AccessDevice.from_dict(current_raw)
                if device.created_at != current.created_at:
                    raise ValueError("Managed device creation time cannot be changed")
                saved = replace(
                    device,
                    updated_at=max(device.updated_at, current.updated_at, datetime.now(UTC)),
                )
            records[str(saved.id)] = cast("StorageRecord", saved.to_dict())
            return saved

        return await self._mutate(mutate)

    async def remove(self, device_id: UUID) -> bool:
        def mutate(snapshot: HomePassStorageData) -> bool:
            return snapshot["data"]["access_devices"].pop(str(device_id), None) is not None

        return await self._mutate(mutate)

    async def remove_for_access_point(self, access_point_id: UUID) -> int:
        """Remove accessories when their logical Door leaves HomePASS."""

        def mutate(snapshot: HomePassStorageData) -> int:
            records = snapshot["data"]["access_devices"]
            identifiers = [
                identifier
                for identifier, raw in records.items()
                if AccessDevice.from_dict(raw).access_point_id == access_point_id
            ]
            for identifier in identifiers:
                del records[identifier]
            return len(identifiers)

        return await self._mutate(mutate)

    @staticmethod
    def list_from_snapshot(snapshot: HomePassStorageData) -> tuple[AccessDevice, ...]:
        devices = tuple(
            AccessDevice.from_dict(raw) for raw in snapshot["data"]["access_devices"].values()
        )
        return tuple(sorted(devices, key=lambda item: (item.display_name.casefold(), str(item.id))))

    async def _mutate[ResultT](self, mutator: Callable[[HomePassStorageData], ResultT]) -> ResultT:
        try:
            async with self._lock:
                return await self._storage.async_transaction(mutator)
        except StorageError:
            raise
        except Exception as err:
            raise StorageError("Unable to save managed HomePASS device") from err


__all__ = ["AccessDeviceRepository"]
