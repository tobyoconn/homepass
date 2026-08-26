"""Repository for durable Access Point policy definitions."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Mapping
from datetime import datetime
from typing import cast
from uuid import UUID

from ..exceptions import (
    AccessPointNotFoundError,
    AccessPointPolicyInUseError,
    StorageError,
)
from ..models import AccessGrant, AccessMetadata, AccessPoint, LifecycleOperation
from ..storage import HomePassStorageData, HomePassStorageManager, StorageRecord

_ACCESS_POINT_FIELDS = {
    "id",
    "display_name",
    "enabled",
    "created_at",
    "updated_at",
}
_ENROLLMENT_SETTING = "managed_access_points"
_NAME_FALLBACKS_SETTING = "access_point_name_fallbacks"


class AccessPointRepository:
    """Persist and resolve stable Access Point authorization policy."""

    def __init__(self, storage_manager: HomePassStorageManager) -> None:
        """Initialize the repository."""
        self._storage_manager = storage_manager
        self._lock = asyncio.Lock()

    async def get(self, access_point_id: UUID) -> AccessPoint:
        """Return one durable policy definition without consulting discovery."""
        try:
            async with self._lock:
                snapshot = await self._storage_manager.async_load()
                return self.get_from_snapshot(snapshot, access_point_id)
        except (AccessPointNotFoundError, StorageError):
            raise
        except Exception as err:
            raise StorageError("Unable to load HomePASS Access Point") from err

    async def list_all(self) -> tuple[AccessPoint, ...]:
        """Return every durable policy definition in deterministic display order."""
        try:
            async with self._lock:
                snapshot = await self._storage_manager.async_load()
                return self.list_from_snapshot(snapshot)
        except StorageError:
            raise
        except Exception as err:
            raise StorageError("Unable to load HomePASS Access Points") from err

    async def update(
        self,
        access_point: AccessPoint,
        *,
        expected_updated_at: datetime,
    ) -> AccessPoint:
        """Replace an existing policy record while retaining its creation timestamp."""

        def mutate(snapshot: HomePassStorageData) -> AccessPoint:
            current = self.get_from_snapshot(snapshot, access_point.id)
            if current.updated_at != expected_updated_at:
                raise ValueError("Access Point policy changed concurrently")
            if access_point.created_at != current.created_at:
                raise ValueError("Access Point created_at cannot be changed")
            if access_point.updated_at < current.updated_at:
                raise ValueError("Access Point updated_at cannot move backwards")
            snapshot["data"]["access_points"][str(access_point.id)] = self._serialize(access_point)
            self._name_fallbacks(snapshot).pop(str(access_point.id), None)
            return access_point

        return await self._mutate(mutate)

    async def remove_if_unreferenced(self, access_point_id: UUID) -> bool:
        """Delete retained policy and enrolment only after proving no references remain."""

        def mutate(snapshot: HomePassStorageData) -> bool:
            key = str(access_point_id)
            if key not in snapshot["data"]["access_points"]:
                return False
            enrollments = cast(
                dict[str, object],
                snapshot["data"]["settings"][_ENROLLMENT_SETTING],
            )
            enrollment = enrollments.get(key)
            if isinstance(enrollment, dict) and enrollment.get("managed") is True:
                raise AccessPointPolicyInUseError("Managed Access Point policy cannot be deleted")
            if self._has_durable_reference(snapshot, access_point_id):
                raise AccessPointPolicyInUseError(
                    "Access Point policy is retained by HomePASS data"
                )
            del snapshot["data"]["access_points"][key]
            enrollments.pop(key, None)
            self._name_fallbacks(snapshot).pop(key, None)
            return True

        return await self._mutate(mutate)

    async def get_access_point(
        self,
        snapshot: HomePassStorageData,
        access_point_id: UUID,
    ) -> AccessPoint:
        """Implement the snapshot-backed authorization lookup boundary."""
        return self.get_from_snapshot(snapshot, access_point_id)

    async def list_access_points(
        self,
        snapshot: HomePassStorageData,
    ) -> tuple[AccessPoint, ...]:
        """Implement the snapshot-backed authorization enumeration boundary."""
        return self.list_from_snapshot(snapshot)

    @classmethod
    def get_from_snapshot(
        cls,
        snapshot: HomePassStorageData,
        access_point_id: UUID,
    ) -> AccessPoint:
        """Decode one stable policy object from a caller-supplied snapshot."""
        try:
            records = snapshot["data"]["access_points"]
        except (KeyError, TypeError) as err:
            raise StorageError("Stored Access Point collection is unavailable") from err
        if not isinstance(records, dict):
            raise StorageError("Stored Access Point collection is invalid")
        try:
            record = records[str(access_point_id)]
        except KeyError as err:
            raise AccessPointNotFoundError from err
        return cls._deserialize(str(access_point_id), record)

    @classmethod
    def list_from_snapshot(
        cls,
        snapshot: HomePassStorageData,
    ) -> tuple[AccessPoint, ...]:
        """Decode all stable policy objects from one caller-supplied snapshot."""
        try:
            records = snapshot["data"]["access_points"]
        except (KeyError, TypeError) as err:
            raise StorageError("Stored Access Point collection is unavailable") from err
        if not isinstance(records, dict):
            raise StorageError("Stored Access Point collection is invalid")
        access_points = [
            cls._deserialize(stored_id, record) for stored_id, record in records.items()
        ]
        return tuple(
            sorted(
                access_points,
                key=lambda item: (item.display_name.casefold(), str(item.id)),
            )
        )

    async def list_name_fallback_ids(self) -> frozenset[UUID]:
        """Return policies still eligible for their one-time migrated-name upgrade."""
        try:
            async with self._lock:
                snapshot = await self._storage_manager.async_load()
                return self.name_fallback_ids_from_snapshot(snapshot)
        except StorageError:
            raise
        except Exception as err:
            raise StorageError("Unable to load HomePASS Access Point name fallbacks") from err

    @classmethod
    def name_fallback_ids_from_snapshot(
        cls,
        snapshot: HomePassStorageData,
    ) -> frozenset[UUID]:
        """Decode pending migrated-name markers from a caller-supplied snapshot."""
        return frozenset(UUID(access_point_id) for access_point_id in cls._name_fallbacks(snapshot))

    async def _mutate[ResultT](
        self,
        mutator: Callable[[HomePassStorageData], ResultT],
    ) -> ResultT:
        """Run one Access Point mutation in the shared storage transaction."""
        try:
            async with self._lock:
                return await self._storage_manager.async_transaction(mutator)
        except (AccessPointNotFoundError, AccessPointPolicyInUseError, StorageError):
            raise
        except Exception as err:
            raise StorageError("Unable to save HomePASS Access Point") from err

    @staticmethod
    def _deserialize(stored_id: object, record: object) -> AccessPoint:
        """Validate one exact serialized Access Point record."""
        if (
            not isinstance(stored_id, str)
            or not isinstance(record, Mapping)
            or set(record) != _ACCESS_POINT_FIELDS
        ):
            raise StorageError("Stored Access Point record is invalid")
        try:
            access_point = AccessPoint.from_dict(record)
        except (KeyError, TypeError, ValueError) as err:
            raise StorageError("Stored Access Point record is invalid") from err
        if str(access_point.id) != stored_id:
            raise StorageError("Stored Access Point identifier does not match its record")
        return access_point

    @staticmethod
    def _serialize(access_point: AccessPoint) -> StorageRecord:
        return cast(StorageRecord, access_point.to_dict())

    @staticmethod
    def _name_fallbacks(snapshot: HomePassStorageData) -> dict[str, object]:
        """Return the optional schema-10 migrated-name marker collection."""
        settings = snapshot["data"]["settings"]
        raw = settings.get(_NAME_FALLBACKS_SETTING, {})
        if not isinstance(raw, dict):
            raise StorageError("Stored Access Point name fallbacks are invalid")
        if any(
            not isinstance(access_point_id, str) or pending is not True
            for access_point_id, pending in raw.items()
        ):
            raise StorageError("Stored Access Point name fallbacks are invalid")
        return cast(dict[str, object], raw)

    @staticmethod
    def _has_durable_reference(
        snapshot: HomePassStorageData,
        access_point_id: UUID,
    ) -> bool:
        """Return whether policy, grants, metadata, or cleanup state retains this UUID."""
        if any(
            AccessGrant.from_dict(record).access_point_id == access_point_id
            for record in snapshot["data"]["access_grants"].values()
        ):
            return True
        if any(
            AccessMetadata.from_dict(record).access_point_id == access_point_id
            for record in snapshot["data"]["access_metadata"].values()
        ):
            return True
        reference = str(access_point_id)
        if any(
            _contains_value(LifecycleOperation.from_dict(record).payload, reference)
            for record in snapshot["data"]["lifecycle_operations"].values()
        ):
            return True
        return _contains_value(snapshot["data"]["properties"], reference)


def _contains_value(value: object, expected: str) -> bool:
    """Return whether nested JSON-compatible data contains an exact string value."""
    if value == expected:
        return True
    if isinstance(value, Mapping):
        return any(_contains_value(item, expected) for item in value.values())
    if isinstance(value, list):
        return any(_contains_value(item, expected) for item in value)
    return False


__all__ = ["AccessPointRepository"]
