"""Generic durable lifecycle operation execution framework."""

from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID

from .exceptions import LifecycleOperationExecutionError
from .models import LifecycleOperation, LifecycleOperationStatus, LifecyclePayloadValue
from .repositories import LifecycleOperationRepository

type LifecycleStepResult = Mapping[str, LifecyclePayloadValue] | None
type LifecycleStep = Callable[
    [LifecycleOperation], LifecycleStepResult | Awaitable[LifecycleStepResult]
]
type LifecycleTransitionObserver = Callable[[LifecycleOperation], Awaitable[None]]


class LifecycleStepFailure(Exception):
    """Signal a sanitized lifecycle step outcome with durable payload changes."""

    def __init__(
        self,
        message: str,
        *,
        payload: Mapping[str, LifecyclePayloadValue],
        retryable: bool,
    ) -> None:
        super().__init__(message)
        self.payload = payload
        self.retryable = retryable


_TERMINAL_STATUSES = {
    LifecycleOperationStatus.COMPLETED,
    LifecycleOperationStatus.CANCELLED,
}


class LifecycleOperationManager:
    """Create and advance restart-safe, multi-step operation journals."""

    def __init__(
        self,
        repository: LifecycleOperationRepository,
        *,
        max_retries: int = 5,
        transition_observer: LifecycleTransitionObserver | None = None,
    ) -> None:
        if isinstance(max_retries, bool) or not isinstance(max_retries, int):
            raise TypeError("Lifecycle max_retries must be an integer")
        if max_retries < 0:
            raise ValueError("Lifecycle max_retries must not be negative")
        self._repository = repository
        self._max_retries = max_retries
        self._transition_observer = transition_observer

    async def create(
        self,
        operation_type: str,
        payload: Mapping[str, LifecyclePayloadValue],
    ) -> LifecycleOperation:
        operation = LifecycleOperation(operation_type=operation_type, payload=payload)
        await self._repository.add(operation)
        await self._observe(operation)
        return operation

    async def load(self, operation_id: UUID) -> LifecycleOperation:
        return await self._repository.get(operation_id)

    async def load_incomplete(self) -> tuple[LifecycleOperation, ...]:
        """Expose restart-recoverable operations without executing them."""
        return tuple(
            operation
            for operation in await self._repository.list_all()
            if operation.status not in _TERMINAL_STATUSES
        )

    async def execute(
        self,
        operation_id: UUID,
        steps: Sequence[LifecycleStep],
        *,
        complete: bool = True,
    ) -> LifecycleOperation:
        operation = await self.load(operation_id)
        if operation.status in _TERMINAL_STATUSES:
            return operation
        operation = await self._transition(operation, status=LifecycleOperationStatus.RUNNING)
        while operation.current_step < len(steps):
            try:
                result = steps[operation.current_step](operation)
                if inspect.isawaitable(result):
                    result = await result
            except LifecycleStepFailure as err:
                retry_count = operation.retry_count + 1
                status = (
                    LifecycleOperationStatus.WAITING_RETRY
                    if err.retryable and retry_count <= self._max_retries
                    else LifecycleOperationStatus.FAILED
                )
                payload = dict(operation.payload)
                payload.update(err.payload)
                await self._transition(
                    operation,
                    status=status,
                    payload=payload,
                    retry_count=retry_count,
                )
                raise LifecycleOperationExecutionError(
                    "Lifecycle operation step did not complete"
                ) from err
            except Exception as err:
                retry_count = operation.retry_count + 1
                status = (
                    LifecycleOperationStatus.WAITING_RETRY
                    if retry_count <= self._max_retries
                    else LifecycleOperationStatus.FAILED
                )
                await self._transition(operation, status=status, retry_count=retry_count)
                raise LifecycleOperationExecutionError(
                    "Lifecycle operation step did not complete"
                ) from err
            payload = dict(operation.payload)
            if result is not None:
                payload.update(result)
            operation = await self._transition(
                operation,
                payload=payload,
                current_step=operation.current_step + 1,
                retry_count=0,
            )
        return await self.complete(operation.operation_id) if complete else operation

    async def resume(
        self,
        operation_id: UUID,
        steps: Sequence[LifecycleStep],
    ) -> LifecycleOperation:
        return await self.execute(operation_id, steps)

    async def retry(
        self,
        operation_id: UUID,
        steps: Sequence[LifecycleStep],
    ) -> LifecycleOperation:
        operation = await self.load(operation_id)
        if operation.status not in {
            LifecycleOperationStatus.WAITING_RETRY,
            LifecycleOperationStatus.FAILED,
        }:
            return operation
        return await self.execute(operation_id, steps)

    async def complete(self, operation_id: UUID) -> LifecycleOperation:
        operation = await self.load(operation_id)
        if operation.status is LifecycleOperationStatus.COMPLETED:
            return operation
        return await self._transition(operation, status=LifecycleOperationStatus.COMPLETED)

    async def cancel(self, operation_id: UUID) -> LifecycleOperation:
        operation = await self.load(operation_id)
        if operation.status in _TERMINAL_STATUSES:
            return operation
        return await self._transition(operation, status=LifecycleOperationStatus.CANCELLED)

    async def checkpoint(
        self,
        operation_id: UUID,
        *,
        payload: Mapping[str, LifecyclePayloadValue] | None = None,
        status: LifecycleOperationStatus | None = None,
        current_step: int | None = None,
        retry_count: int | None = None,
    ) -> LifecycleOperation:
        """Persist one externally orchestrated lifecycle progress checkpoint."""
        operation = await self.load(operation_id)
        return await self._transition(
            operation,
            payload=payload,
            status=status,
            current_step=current_step,
            retry_count=retry_count,
        )

    async def record_failure(
        self,
        operation_id: UUID,
        *,
        payload: Mapping[str, LifecyclePayloadValue],
        retryable: bool,
    ) -> LifecycleOperation:
        """Persist bounded retry metadata for external orchestration."""
        operation = await self.load(operation_id)
        retry_count = operation.retry_count + 1
        status = (
            LifecycleOperationStatus.WAITING_RETRY
            if retryable and retry_count <= self._max_retries
            else LifecycleOperationStatus.FAILED
        )
        return await self._transition(
            operation,
            payload=payload,
            status=status,
            retry_count=retry_count,
        )

    async def _transition(
        self,
        operation: LifecycleOperation,
        *,
        status: LifecycleOperationStatus | None = None,
        payload: Mapping[str, LifecyclePayloadValue] | None = None,
        current_step: int | None = None,
        retry_count: int | None = None,
    ) -> LifecycleOperation:
        updated = replace(
            operation,
            status=operation.status if status is None else status,
            payload=operation.payload if payload is None else payload,
            current_step=operation.current_step if current_step is None else current_step,
            retry_count=operation.retry_count if retry_count is None else retry_count,
            updated_at=datetime.now(UTC),
        )
        await self._repository.replace(
            updated,
            expected_updated_at=operation.updated_at,
        )
        await self._observe(updated)
        return updated

    async def _observe(self, operation: LifecycleOperation) -> None:
        """Notify the status boundary after each durable journal transition."""
        if self._transition_observer is not None:
            await self._transition_observer(operation)
