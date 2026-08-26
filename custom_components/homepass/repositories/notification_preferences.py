"""Persistence boundary for independently versioned notification preferences."""

from __future__ import annotations

import asyncio
from typing import cast

from ..exceptions import StorageError
from ..models.notification_preferences import NotificationPreferences
from ..storage import HomePassStorageData, HomePassStorageManager, JsonValue

NOTIFICATION_PREFERENCES_SETTING = "notification_preferences"


class NotificationPreferencesRepository:
    """Load and atomically persist installation-wide notification preferences."""

    def __init__(self, storage: HomePassStorageManager) -> None:
        self._storage = storage
        self._lock = asyncio.Lock()

    async def get(self) -> NotificationPreferences | None:
        """Return saved preferences, or None before their first initialization."""
        try:
            async with self._lock:
                snapshot = await self._storage.async_load()
            raw = snapshot["data"]["settings"].get(NOTIFICATION_PREFERENCES_SETTING)
            return None if raw is None else NotificationPreferences.from_dict(raw)
        except StorageError:
            raise
        except Exception as err:
            raise StorageError("Unable to load notification preferences") from err

    async def save(
        self,
        preferences: NotificationPreferences,
    ) -> NotificationPreferences:
        """Persist the complete preference document in one storage transaction."""
        if not isinstance(preferences, NotificationPreferences):
            raise TypeError("Notification preferences are required")

        def mutate(snapshot: HomePassStorageData) -> NotificationPreferences:
            snapshot["data"]["settings"][NOTIFICATION_PREFERENCES_SETTING] = cast(
                JsonValue,
                preferences.to_dict(),
            )
            return preferences

        try:
            async with self._lock:
                return await self._storage.async_transaction(mutate)
        except StorageError:
            raise
        except Exception as err:
            raise StorageError("Unable to save notification preferences") from err


__all__ = ["NOTIFICATION_PREFERENCES_SETTING", "NotificationPreferencesRepository"]
