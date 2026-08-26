"""Repository for durable lifecycle operations."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import datetime
from typing import cast
from uuid import UUID

from ..exceptions import (
    LifecycleOperationConflictError,
    LifecycleOperationNotFoundError,
    StorageError,
)
from ..models import LifecycleOperation
from ..storage import HomePassStorageData, HomePassStorageManager, StorageRecord


class LifecycleOperationRepository:
    """Persist lifecycle journal records in the shared transaction boundary."""

    def __init__(self, storage_manager: HomePassStorageManager) -> None:
        self._storage_manager = storage_manager
        self._lock = asyncio.Lock()

    async def add(self, operation: LifecycleOperation) -> None:
        def mutate(storage: HomePassStorageData) -> None:
            key = str(operation.operation_id)
            if key in storage["data"]["lifecycle_operations"]:
                raise LifecycleOperationConflictError("Lifecycle operation already exists")
            storage["data"]["lifecycle_operations"][key] = self._serialize(operation)

        await self._mutate(mutate)

    async def get(self, operation_id: UUID) -> LifecycleOperation:
        operations = await self.list_all()
        for operation in operations:
            if operation.operation_id == operation_id:
                return operation
        raise LifecycleOperationNotFoundError("Lifecycle operation was not found")

    async def list_all(self) -> tuple[LifecycleOperation, ...]:
        try:
            async with self._lock:
                storage = await self._storage_manager.async_load()
                return tuple(
                    sorted(
                        self._deserialize(storage).values(),
                        key=lambda operation: (operation.created_at, str(operation.operation_id)),
                    )
                )
        except StorageError:
            raise
        except Exception as err:
            raise StorageError("Unable to load HomePASS lifecycle operations") from err

    async def replace(
        self,
        operation: LifecycleOperation,
        *,
        expected_updated_at: datetime,
    ) -> None:
        def mutate(storage: HomePassStorageData) -> None:
            key = str(operation.operation_id)
            record = storage["data"]["lifecycle_operations"].get(key)
            if record is None:
                raise LifecycleOperationNotFoundError("Lifecycle operation was not found")
            current = LifecycleOperation.from_dict(record)
            if current.updated_at != expected_updated_at:
                raise LifecycleOperationConflictError("Lifecycle operation changed concurrently")
            storage["data"]["lifecycle_operations"][key] = self._serialize(operation)

        await self._mutate(mutate)

    async def _mutate[ResultT](self, mutator: Callable[[HomePassStorageData], ResultT]) -> ResultT:
        try:
            async with self._lock:
                return await self._storage_manager.async_transaction(mutator)
        except (
            LifecycleOperationConflictError,
            LifecycleOperationNotFoundError,
            StorageError,
        ):
            raise
        except Exception as err:
            raise StorageError("Unable to save HomePASS lifecycle operation") from err

    @staticmethod
    def _deserialize(storage: HomePassStorageData) -> dict[UUID, LifecycleOperation]:
        operations: dict[UUID, LifecycleOperation] = {}
        for key, record in storage["data"]["lifecycle_operations"].items():
            operation = LifecycleOperation.from_dict(record)
            if str(operation.operation_id) != key:
                raise StorageError("Stored lifecycle operation identifier does not match record")
            operations[operation.operation_id] = operation
        return operations

    @staticmethod
    def _serialize(operation: LifecycleOperation) -> StorageRecord:
        return cast(StorageRecord, operation.to_dict())
