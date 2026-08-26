"""Device-first Person deletion orchestration."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import replace
from datetime import UTC, datetime
from typing import Protocol, cast
from uuid import UUID

from ..drivers import (
    CredentialRemovalRequest,
    CredentialRemovalRequestResult,
    CredentialRemovalRequestStatus,
    CredentialRemovalVerificationResult,
    CredentialRemovalVerificationStatus,
)
from ..exceptions import LifecycleOperationExecutionError, PersonNotFoundError
from ..lifecycle import LifecycleOperationManager
from ..models import (
    AccessDriver,
    AccessGrant,
    AccessMetadata,
    LifecycleOperation,
    LifecycleOperationStatus,
    LifecyclePayloadValue,
    Person,
)
from ..repositories.person import PersonRepository
from ..storage import HomePassStorageData, HomePassStorageManager, StorageRecord
from ..vault import CredentialMetadata, CredentialVaultProtocol, VaultCredentialId
from .synchronization_status import SynchronizationStatusService


class CredentialRemovalDriver(Protocol):
    """Driver boundary used by device-first lifecycle deletion."""

    async def async_request_credential_removal(
        self, request: CredentialRemovalRequest
    ) -> CredentialRemovalRequestResult: ...

    async def async_verify_credential_removed(
        self, request: CredentialRemovalRequest
    ) -> CredentialRemovalVerificationResult: ...


type CredentialRemovalDriverResolver = Callable[[AccessDriver], CredentialRemovalDriver | None]
type PersonDeleteHook = Callable[[UUID], Awaitable[object]]


class PersonDeletionService:
    """Remove device credentials before finalizing local Person deletion."""

    OPERATION_TYPE = "delete_person"

    def __init__(
        self,
        storage: HomePassStorageManager,
        lifecycle_manager: LifecycleOperationManager,
        driver_resolver: CredentialRemovalDriverResolver,
        synchronization_status_service: SynchronizationStatusService | None = None,
        credential_vault: CredentialVaultProtocol | None = None,
        before_delete: PersonDeleteHook | None = None,
    ) -> None:
        self._storage = storage
        self._lifecycle_manager = lifecycle_manager
        self._driver_resolver = driver_resolver
        self._synchronization_status_service = synchronization_status_service
        self._credential_vault = credential_vault
        self._before_delete = before_delete

    async def delete_person(self, person_id: UUID) -> LifecycleOperation:
        operation = await self._active_operation(person_id)
        if operation is None:
            operation = await self._create_operation(person_id)
        else:
            operation = await self._normalize_incomplete_operation(operation)
        operation = await self._lifecycle_manager.checkpoint(
            operation.operation_id,
            status=LifecycleOperationStatus.RUNNING,
        )
        while operation.current_step < len(self._targets(operation)):
            operation = await self._process_target(operation, operation.current_step)
        return await self._finalize(person_id, operation)

    async def _process_target(
        self, operation: LifecycleOperation, index: int
    ) -> LifecycleOperation:
        targets = self._targets(operation)
        target = targets[index]
        state = cast(str, target.get("state", "removal_not_requested"))
        if state in {"removal_not_requested", "removal_request_rejected"}:
            if self._driver(target) is None:
                target.update(
                    state="verification_failed",
                    request_result="rejected",
                    timestamp=datetime.now(UTC).isoformat(),
                    error_summary="Credential removal is not supported for this device",
                )
                await self._pause(operation, targets, index, retryable=False)
            target.update(
                state="removal_requesting",
                request_result="ambiguous",
                timestamp=datetime.now(UTC).isoformat(),
                error_summary=None,
            )
            operation = await self._checkpoint_target(operation, targets, index)
            request_result = await self._request_removal(target)
            target.update(
                request_result=request_result.status.value,
                timestamp=datetime.now(UTC).isoformat(),
                error_summary=request_result.error_summary,
            )
            if request_result.status is CredentialRemovalRequestStatus.REJECTED:
                target["state"] = "removal_request_rejected"
                await self._pause(operation, targets, index, retryable=True)
            target["state"] = "removal_requested"
            operation = await self._checkpoint_target(operation, targets, index)
            targets = self._targets(operation)
            targets[index]["state"] = "verification_pending"
            operation = await self._checkpoint_target(operation, targets, index)
        elif state in {"removal_requesting", "removal_requested"}:
            target.update(
                state="verification_pending",
                request_result=(
                    "ambiguous" if state == "removal_requesting" else target["request_result"]
                ),
                timestamp=datetime.now(UTC).isoformat(),
                error_summary=(
                    "Credential removal request outcome is unknown"
                    if state == "removal_requesting"
                    else target.get("error_summary")
                ),
            )
            operation = await self._checkpoint_target(operation, targets, index)

        target = self._targets(operation)[index]
        verification_result = await self._verify_removal(target)
        target.update(
            timestamp=datetime.now(UTC).isoformat(),
            error_summary=verification_result.error_summary,
        )
        targets = self._targets(operation)
        targets[index] = target
        if verification_result.status is CredentialRemovalVerificationStatus.REMOVED:
            target["state"] = "removal_confirmed"
            return await self._checkpoint_target(
                operation,
                targets,
                index,
                current_step=index + 1,
                retry_count=0,
            )
        if verification_result.status is CredentialRemovalVerificationStatus.RETRYABLE_FAILURE:
            target["state"] = "verification_pending"
            await self._pause(operation, targets, index, retryable=True)
        if verification_result.status is CredentialRemovalVerificationStatus.STILL_PRESENT:
            target["state"] = "verification_failed"
            await self._pause(operation, targets, index, retryable=True)
        target["state"] = "verification_failed"
        await self._pause(operation, targets, index, retryable=False)
        raise AssertionError("Lifecycle pause must raise")

    async def _active_operation(self, person_id: UUID) -> LifecycleOperation | None:
        for operation in await self._lifecycle_manager.load_incomplete():
            if operation.operation_type == self.OPERATION_TYPE and operation.payload.get(
                "person_id"
            ) == str(person_id):
                return operation
        return None

    async def _create_operation(self, person_id: UUID) -> LifecycleOperation:
        snapshot = await self._storage.async_load()
        person_record = snapshot["data"]["people"].get(str(person_id))
        if person_record is None:
            raise PersonNotFoundError(str(person_id))
        Person.from_dict(person_record)
        metadata_by_key = snapshot["data"]["access_metadata"]
        targets: list[LifecyclePayloadValue] = []
        for key, record in snapshot["data"]["access_grants"].items():
            grant = AccessGrant.from_dict(record)
            if grant.person_id != person_id:
                continue
            metadata_record = metadata_by_key.get(key)
            metadata = (
                AccessMetadata.from_dict(metadata_record) if metadata_record is not None else None
            )
            targets.append(
                {
                    "access_point_id": str(grant.access_point_id),
                    "target_device": metadata.lock_entity_id if metadata else "unavailable",
                    "credential_identifier": str(grant.credential_id),
                    "driver": metadata.driver.value if metadata else "unsupported",
                    "slot": metadata.slot if metadata else 0,
                    "state": "removal_not_requested",
                    "request_result": None,
                    "timestamp": datetime.now(UTC).isoformat(),
                    "error_summary": None,
                }
            )
        targets.sort(
            key=lambda target: str(
                cast(dict[str, LifecyclePayloadValue], target)["access_point_id"]
            )
        )
        return await self._lifecycle_manager.create(
            self.OPERATION_TYPE,
            {"person_id": str(person_id), "targets": targets},
        )

    async def _request_removal(
        self, target: dict[str, LifecyclePayloadValue]
    ) -> CredentialRemovalRequestResult:
        driver = self._driver(target)
        if driver is None:
            return CredentialRemovalRequestResult(
                CredentialRemovalRequestStatus.REJECTED,
                "Credential removal is not supported for this device",
            )
        try:
            return await driver.async_request_credential_removal(self._request(target))
        except Exception:
            return CredentialRemovalRequestResult(
                CredentialRemovalRequestStatus.AMBIGUOUS,
                "Credential removal request outcome is unknown",
            )

    async def _verify_removal(
        self, target: dict[str, LifecyclePayloadValue]
    ) -> CredentialRemovalVerificationResult:
        driver = self._driver(target)
        if driver is None:
            return CredentialRemovalVerificationResult(
                CredentialRemovalVerificationStatus.UNSUPPORTED,
                "Credential removal verification is not supported for this device",
            )
        try:
            return await driver.async_verify_credential_removed(self._request(target))
        except Exception:
            return CredentialRemovalVerificationResult(
                CredentialRemovalVerificationStatus.RETRYABLE_FAILURE,
                "Credential removal could not be verified",
            )

    def _driver(self, target: dict[str, LifecyclePayloadValue]) -> CredentialRemovalDriver | None:
        try:
            return self._driver_resolver(AccessDriver(cast(str, target["driver"])))
        except (KeyError, TypeError, ValueError):
            return None

    @staticmethod
    def _request(target: dict[str, LifecyclePayloadValue]) -> CredentialRemovalRequest:
        return CredentialRemovalRequest(
            target_device=cast(str, target["target_device"]),
            slot=cast(int, target["slot"]),
            credential_identifier=cast(str, target["credential_identifier"]),
        )

    async def _normalize_incomplete_operation(
        self, operation: LifecycleOperation
    ) -> LifecycleOperation:
        """Conservatively upgrade incomplete PE-005D target journals."""
        targets = self._targets(operation)
        changed = False
        current_step = 0
        for target in targets:
            state = cast(str, target.get("state", "pending"))
            if "request_result" not in target:
                changed = True
                if state == "success":
                    target["state"] = "removal_confirmed"
                    target["request_result"] = "accepted"
                elif state == "retryable_failure":
                    target["state"] = "verification_pending"
                    target["request_result"] = "ambiguous"
                    target["error_summary"] = "Credential removal could not be verified"
                elif state == "pending":
                    target["state"] = "removal_not_requested"
                    target["request_result"] = None
                else:
                    target["state"] = "verification_failed"
                    target["request_result"] = "ambiguous"
            if target["state"] == "removal_confirmed":
                current_step += 1
            else:
                break
        if not changed:
            return operation
        payload = dict(operation.payload)
        payload["targets"] = cast(LifecyclePayloadValue, targets)
        return await self._lifecycle_manager.checkpoint(
            operation.operation_id,
            payload=payload,
            current_step=current_step,
        )

    async def _checkpoint_target(
        self,
        operation: LifecycleOperation,
        targets: list[dict[str, LifecyclePayloadValue]],
        index: int,
        *,
        current_step: int | None = None,
        retry_count: int | None = None,
    ) -> LifecycleOperation:
        payload = dict(operation.payload)
        payload["targets"] = cast(LifecyclePayloadValue, targets)
        return await self._lifecycle_manager.checkpoint(
            operation.operation_id,
            payload=payload,
            status=LifecycleOperationStatus.RUNNING,
            current_step=index if current_step is None else current_step,
            retry_count=retry_count,
        )

    async def _pause(
        self,
        operation: LifecycleOperation,
        targets: list[dict[str, LifecyclePayloadValue]],
        index: int,
        *,
        retryable: bool,
    ) -> None:
        payload = dict(operation.payload)
        payload["targets"] = cast(LifecyclePayloadValue, targets)
        await self._lifecycle_manager.record_failure(
            operation.operation_id,
            payload=payload,
            retryable=retryable,
        )
        raise LifecycleOperationExecutionError(
            f"Credential removal target {index + 1} did not complete"
        )

    async def _finalize(self, person_id: UUID, operation: LifecycleOperation) -> LifecycleOperation:
        owned_credentials = await self._owned_vault_credentials(person_id)
        if self._before_delete is not None:
            await self._before_delete(person_id)
        completed = replace(
            operation,
            status=LifecycleOperationStatus.COMPLETED,
            current_step=operation.current_step + 1,
            updated_at=datetime.now(UTC),
        )

        def mutate(snapshot: HomePassStorageData) -> LifecycleOperation:
            record = snapshot["data"]["lifecycle_operations"].get(str(operation.operation_id))
            if record is None:
                raise ValueError("Lifecycle operation disappeared before finalization")
            current = LifecycleOperation.from_dict(record)
            if current.updated_at != operation.updated_at:
                raise ValueError("Lifecycle operation changed before finalization")
            expected_relationships = {
                (
                    cast(str, target["access_point_id"]),
                    cast(str, target["credential_identifier"]),
                )
                for target in self._targets(operation)
            }
            current_relationships = {
                (str(grant.access_point_id), str(grant.credential_id))
                for raw_grant in snapshot["data"]["access_grants"].values()
                if (grant := AccessGrant.from_dict(raw_grant)).person_id == person_id
            }
            if current_relationships != expected_relationships:
                targets = self._targets(operation)
                metadata_records = snapshot["data"]["access_metadata"]
                for key, raw_grant in snapshot["data"]["access_grants"].items():
                    grant = AccessGrant.from_dict(raw_grant)
                    relationship = (str(grant.access_point_id), str(grant.credential_id))
                    if grant.person_id != person_id or relationship in expected_relationships:
                        continue
                    raw_metadata = metadata_records.get(key)
                    metadata = (
                        AccessMetadata.from_dict(raw_metadata) if raw_metadata is not None else None
                    )
                    targets.append(
                        {
                            "access_point_id": str(grant.access_point_id),
                            "target_device": (
                                metadata.lock_entity_id if metadata else "unavailable"
                            ),
                            "credential_identifier": str(grant.credential_id),
                            "driver": metadata.driver.value if metadata else "unsupported",
                            "slot": metadata.slot if metadata else 0,
                            "state": "removal_not_requested",
                            "request_result": None,
                            "timestamp": datetime.now(UTC).isoformat(),
                            "error_summary": None,
                        }
                    )
                expanded_payload = dict(operation.payload)
                expanded_payload["targets"] = cast(LifecyclePayloadValue, targets)
                expanded = replace(
                    operation,
                    status=LifecycleOperationStatus.WAITING_RETRY,
                    payload=expanded_payload,
                    updated_at=datetime.now(UTC),
                )
                snapshot["data"]["lifecycle_operations"][str(operation.operation_id)] = cast(
                    StorageRecord, expanded.to_dict()
                )
                return expanded
            PersonRepository.remove_from_snapshot(snapshot, person_id)
            snapshot["data"]["lifecycle_operations"][str(operation.operation_id)] = cast(
                StorageRecord, completed.to_dict()
            )
            return completed

        finalized = await self._storage.async_transaction(mutate)
        if finalized.status is not LifecycleOperationStatus.COMPLETED:
            raise LifecycleOperationExecutionError(
                "Person access changed during credential removal"
            )
        if self._synchronization_status_service is not None:
            await self._synchronization_status_service.lifecycle_changed(finalized)
        await self._delete_unshared_vault_credentials(owned_credentials)
        return finalized

    async def _owned_vault_credentials(self, person_id: UUID) -> set[VaultCredentialId]:
        """Capture Vault identifiers owned before the final local removal."""
        if self._credential_vault is None:
            return set()
        snapshot = await self._storage.async_load()
        owned: set[VaultCredentialId] = set()
        credential_record = snapshot["data"]["credential_metadata"].get(str(person_id))
        if credential_record is not None:
            owned.add(CredentialMetadata.from_dict(credential_record).credential_id)
        for record in snapshot["data"]["access_metadata"].values():
            metadata = AccessMetadata.from_dict(record)
            if metadata.person_id == person_id and metadata.vault_credential_id is not None:
                owned.add(metadata.vault_credential_id)
        for record in snapshot["data"]["access_grants"].values():
            grant = AccessGrant.from_dict(record)
            if grant.person_id == person_id:
                owned.add(VaultCredentialId(grant.credential_id))
        return owned

    async def _delete_unshared_vault_credentials(self, owned: set[VaultCredentialId]) -> None:
        """Best-effort delete unreachable secrets only after local authority is removed."""
        if self._credential_vault is None or not owned:
            return
        snapshot = await self._storage.async_load()
        referenced_elsewhere: set[VaultCredentialId] = set()
        for record in snapshot["data"]["credential_metadata"].values():
            referenced_elsewhere.add(CredentialMetadata.from_dict(record).credential_id)
        for record in snapshot["data"]["access_metadata"].values():
            metadata = AccessMetadata.from_dict(record)
            if metadata.vault_credential_id is not None:
                referenced_elsewhere.add(metadata.vault_credential_id)
        for record in snapshot["data"]["access_grants"].values():
            referenced_elsewhere.add(VaultCredentialId(AccessGrant.from_dict(record).credential_id))

        for credential_id in sorted(owned - referenced_elsewhere, key=str):
            try:
                if await self._credential_vault.exists(credential_id):
                    await self._credential_vault.delete(credential_id)
            except Exception:
                # Local authority is already gone. An encrypted, unreachable orphan
                # is safer than restoring a deleted User or reporting false access.
                continue

    @staticmethod
    def _targets(operation: LifecycleOperation) -> list[dict[str, LifecyclePayloadValue]]:
        raw_targets = operation.payload.get("targets")
        if not isinstance(raw_targets, list) or not all(
            isinstance(target, dict) for target in raw_targets
        ):
            raise ValueError("Lifecycle operation targets are invalid")
        return [dict(cast(dict[str, LifecyclePayloadValue], target)) for target in raw_targets]
