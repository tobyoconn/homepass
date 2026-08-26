"""Atomic persistence boundary for installation identity settings."""

from __future__ import annotations

import asyncio
from typing import cast

from ..exceptions import StorageError
from ..models.property_settings import PropertySettings
from ..storage import HomePassStorageData, HomePassStorageManager, JsonValue

PROPERTY_SETTINGS_KEY = "property_settings"


class PropertySettingsRepository:
    """Persist Property Settings within the existing settings collection."""

    def __init__(self, storage: HomePassStorageManager) -> None:
        self._storage = storage
        self._lock = asyncio.Lock()

    async def get(self) -> PropertySettings | None:
        """Return saved settings or None before first initialization."""
        try:
            async with self._lock:
                snapshot = await self._storage.async_load()
            raw = snapshot["data"]["settings"].get(PROPERTY_SETTINGS_KEY)
            return None if raw is None else PropertySettings.from_dict(raw)
        except StorageError:
            raise
        except Exception as err:
            raise StorageError("Unable to load Property Settings") from err

    async def save(self, settings: PropertySettings) -> PropertySettings:
        """Atomically persist one complete settings document."""
        if not isinstance(settings, PropertySettings):
            raise TypeError("Property Settings are required")

        def mutate(snapshot: HomePassStorageData) -> PropertySettings:
            snapshot["data"]["settings"][PROPERTY_SETTINGS_KEY] = cast(
                JsonValue,
                settings.to_dict(),
            )
            return settings

        try:
            async with self._lock:
                return await self._storage.async_transaction(mutate)
        except StorageError:
            raise
        except Exception as err:
            raise StorageError("Unable to save Property Settings") from err

    async def initialize(self, defaults: PropertySettings) -> PropertySettings:
        """Atomically create defaults only when no saved document exists."""
        if not isinstance(defaults, PropertySettings):
            raise TypeError("Default Property Settings are required")

        def mutate(snapshot: HomePassStorageData) -> PropertySettings:
            raw = snapshot["data"]["settings"].get(PROPERTY_SETTINGS_KEY)
            if raw is not None:
                return PropertySettings.from_dict(raw)
            snapshot["data"]["settings"][PROPERTY_SETTINGS_KEY] = cast(
                JsonValue,
                defaults.to_dict(),
            )
            return defaults

        try:
            async with self._lock:
                return await self._storage.async_transaction(mutate)
        except StorageError:
            raise
        except Exception as err:
            raise StorageError("Unable to initialize Property Settings") from err


__all__ = ["PROPERTY_SETTINGS_KEY", "PropertySettingsRepository"]
