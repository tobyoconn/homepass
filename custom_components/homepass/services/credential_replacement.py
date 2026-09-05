"""Restart-safe lifecycle orchestration for numeric PIN replacement."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime
from typing import Literal, NoReturn, Protocol, TypedDict, cast
from uuid import UUID

from ..drivers import (
    CredentialReplacementRequest,
    CredentialReplacementRequestResult,
    CredentialReplacementRequestStatus,
    CredentialReplacementVerificationResult,
    CredentialReplacementVerificationStatus,
)
from ..exceptions import (
    ConcurrentCredentialReplacementError,
    CredentialReplacementError,
    LifecycleOperationExecutionError,
    PersonNotFoundError,
    ValidationError,
)
from ..lifecycle import LifecycleOperationManager
from ..models import (
    AccessDriver,
    AccessGrant,
    AccessMetadata,
    AccessPoint,
    ActivityEventType,
    ActivityOutcome,
    LifecycleOperation,
    LifecycleOperationStatus,
    LifecyclePayloadValue,
    Person,
    SynchronizationStatus,
)
from ..storage import HomePassStorageData, HomePassStorageManager, StorageRecord
from ..vault import (
    CredentialMetadata,
    CredentialVaultProtocol,
    StagedSecretHandle,
    VaultCredentialId,
    VaultPromotionReceipt,
)
from .activity_producer import ActivityProducer
from .synchronization_status import SynchronizationStatusService

_LOGGER = logging.getLogger(__name__)


class CredentialReplacementDriver(Protocol):
    """Driver operations used by replacement orchestration."""

    async def async_request_credential_replacement(
        self, request: CredentialReplacementRequest
    ) -> CredentialReplacementRequestResult: ...

    async def async_verify_credential_replacement(
        self, request: CredentialReplacementRequest
    ) -> CredentialReplacementVerificationResult: ...

    def supports_pin_replacement(self, target_device: str) -> bool: ...

    def supports_exact_pin_readback(self, target_device: str) -> bool: ...


class CredentialReplacementCapabilities(TypedDict):
    """JSON-safe runtime capabilities for one authoritative access target."""

    status: Literal["supported", "unsupported", "unavailable"]
    replace_pin: bool
    exact_readback: bool


type CredentialReplacementDriverResolver = Callable[
    [AccessDriver], CredentialReplacementDriver | None
]
type RevealRateLimitReset = Callable[[UUID, UUID | None], None]


class CredentialReplacementLifecycleService:
    """Coordinate Vault, driver, and registry replacement checkpoints."""

    OPERATION_TYPE = "credential_replacement"

    def __init__(
        self,
        storage: HomePassStorageManager,
        lifecycle_manager: LifecycleOperationManager,
        vault: CredentialVaultProtocol,
        driver_resolver: CredentialReplacementDriverResolver,
        reveal_rate_limit_reset: RevealRateLimitReset | None = None,
        synchronization_status_service: SynchronizationStatusService | None = None,
        activity_producer: ActivityProducer | None = None,
    ) -> None:
        self._storage = storage
        self._lifecycle_manager = lifecycle_manager
        self._vault = vault
        self._driver_resolver = driver_resolver
        self._reveal_rate_limit_reset = reveal_rate_limit_reset
        self._synchronization_status_service = synchronization_status_service
        self._activity_producer = activity_producer

    def capabilities_for(self, metadata: AccessMetadata) -> CredentialReplacementCapabilities:
        """Resolve current non-secret replacement capabilities for one target."""
        try:
            driver = self._driver_resolver(metadata.driver)
        except Exception:
            return {
                "status": "unavailable",
                "replace_pin": False,
                "exact_readback": False,
            }
        if driver is None:
            return {
                "status": "unsupported",
                "replace_pin": False,
                "exact_readback": False,
            }
        try:
            exact_readback = driver.supports_exact_pin_readback(metadata.lock_entity_id)
            replace_pin = driver.supports_pin_replacement(metadata.lock_entity_id)
        except Exception:
            return {
                "status": "unavailable",
                "replace_pin": False,
                "exact_readback": False,
            }
        return {
            "status": "supported" if replace_pin else "unsupported",
            "replace_pin": replace_pin,
            "exact_readback": exact_readback,
        }

    async def replace_pin(self, person_id: UUID, new_pin: str) -> LifecycleOperation:
        """Validate, stage, journal, and execute one Person credential replacement."""
        self._validate_pin(new_pin)
        if await self._active_operation(person_id) is not None:
            raise CredentialReplacementError("Credential replacement is already in progress")
        context = await self._capture_context(person_id)
        credential_id = VaultCredentialId.from_string(cast(str, context["credential_id"]))
        current_pin = await self._vault.retrieve(credential_id)
        try:
            if current_pin == new_pin:
                raise ValidationError("Replacement PIN must differ from the current PIN")
        finally:
            current_pin = ""
        handle = await self._vault.stage(credential_id, new_pin)
        new_pin = ""
        payload = dict(context)
        payload.update(
            {
                "phase": "staged",
                "staged_handle": str(handle),
                "resumable": True,
                "error_summary": None,
            }
        )
        try:
            operation = await self._lifecycle_manager.create(self.OPERATION_TYPE, payload)
        except Exception:
            await self._vault.discard(handle)
            raise
        operation = await self._checkpoint(
            operation,
            phase="intent_persisted",
            status=LifecycleOperationStatus.RUNNING,
        )
        return await self.resume(operation.operation_id)

    async def validate_pin_candidate(self, person_id: UUID, new_pin: str) -> bool:
        """Validate a replacement candidate without staging or exposing credentials."""
        self._validate_pin(new_pin)
        snapshot = await self._storage.async_load()
        if str(person_id) not in snapshot["data"]["people"]:
            raise PersonNotFoundError(str(person_id))
        raw_authority = snapshot["data"]["credential_metadata"].get(str(person_id))
        if raw_authority is None:
            raise ValidationError("Person has no credential to replace")
        authority = CredentialMetadata.from_dict(raw_authority)
        if not authority.enabled:
            raise ValidationError("This User's PIN is disabled")
        credential_id = authority.credential_id
        current_pin = await self._vault.retrieve(credential_id)
        try:
            return current_pin != new_pin
        finally:
            current_pin = ""

    async def retry_pin(self, person_id: UUID) -> LifecycleOperation:
        """Resume a retryable replacement without restaging plaintext."""
        operation = await self._active_operation(person_id)
        if operation is None or not bool(operation.payload.get("resumable")):
            raise CredentialReplacementError("No retryable credential replacement exists")
        return await self.resume(operation.operation_id)

    async def resume(self, operation_id: UUID) -> LifecycleOperation:
        """Resume from the last durable checkpoint without repeating completed I/O."""
        operation = await self._lifecycle_manager.load(operation_id)
        if operation.operation_type != self.OPERATION_TYPE:
            raise CredentialReplacementError("Lifecycle operation type is invalid")
        if operation.status is LifecycleOperationStatus.COMPLETED:
            return operation
        if operation.status is LifecycleOperationStatus.FAILED and not bool(
            operation.payload.get("resumable")
        ):
            raise LifecycleOperationExecutionError("Credential replacement cannot be resumed")
        operation = await self._lifecycle_manager.checkpoint(
            operation.operation_id,
            status=LifecycleOperationStatus.RUNNING,
        )
        phase = cast(str, operation.payload.get("phase"))
        if phase not in {"promotion_pending", "vault_promoted"}:
            operation = await self._resume_targets(operation)
            phase = cast(str, operation.payload.get("phase"))
        if phase == "verification_confirmed":
            await self._revalidate(operation, include_vault=True)
            operation = await self._checkpoint(operation, phase="promotion_pending")
            phase = "promotion_pending"
        if phase == "promotion_pending":
            operation = await self._promote(operation)
            phase = cast(str, operation.payload.get("phase"))
        if phase == "vault_promoted":
            return await self._finalize(operation)
        return operation

    async def _resume_targets(self, operation: LifecycleOperation) -> LifecycleOperation:
        targets = self._targets(operation)
        for index, target in enumerate(targets):
            state = cast(str, target.get("state", "request_not_started"))
            if state == "confirmed":
                continue
            if state == "request_dispatching":
                target.update(
                    state="verification_pending",
                    request_result="ambiguous",
                    error_summary="Credential replacement request outcome is unknown",
                    timestamp=self._timestamp(),
                )
                targets[index] = target
                operation = await self._checkpoint_targets(operation, targets, index)
                state = "verification_pending"
            if state in {"request_not_started", "request_rejected"}:
                await self._revalidate(operation, include_vault=True)
                target.update(state="request_dispatching", timestamp=self._timestamp())
                targets[index] = target
                operation = await self._checkpoint_targets(operation, targets, index)
                request_result = await self._request(operation, target)
                target.update(
                    request_result=request_result.status.value,
                    error_summary=request_result.error_summary,
                    timestamp=self._timestamp(),
                )
                if request_result.status is CredentialReplacementRequestStatus.REJECTED:
                    target["state"] = "request_rejected"
                    targets[index] = target
                    await self._pause(operation, targets, index, retryable=True)
                if request_result.status is CredentialReplacementRequestStatus.UNSUPPORTED:
                    target["state"] = "unsupported"
                    targets[index] = target
                    await self._pause(operation, targets, index, retryable=False)
                target["state"] = "verification_pending"
                targets[index] = target
                operation = await self._checkpoint_targets(operation, targets, index)
            verification_result = await self._verify(operation, target)
            target.update(
                verification_result=verification_result.status.value,
                error_summary=verification_result.error_summary,
                timestamp=self._timestamp(),
            )
            if (
                verification_result.status
                is CredentialReplacementVerificationStatus.REPLACEMENT_CONFIRMED
            ):
                target["state"] = "confirmed"
                targets[index] = target
                operation = await self._checkpoint_targets(
                    operation,
                    targets,
                    index + 1,
                )
                continue
            target["state"] = (
                "unsupported"
                if verification_result.status is CredentialReplacementVerificationStatus.UNSUPPORTED
                else "verification_pending"
            )
            targets[index] = target
            retryable = verification_result.status in {
                CredentialReplacementVerificationStatus.REPLACEMENT_NOT_YET_CONFIRMED,
                CredentialReplacementVerificationStatus.RETRYABLE_FAILURE,
                CredentialReplacementVerificationStatus.PREVIOUS_OR_DIFFERENT_CREDENTIAL_PRESENT,
            }
            await self._pause(operation, targets, index, retryable=retryable)
        return await self._checkpoint(
            operation,
            phase="verification_confirmed",
            current_step=len(targets),
        )

    async def _request(
        self,
        operation: LifecycleOperation,
        target: dict[str, LifecyclePayloadValue],
    ) -> CredentialReplacementRequestResult:
        driver = self._driver(target)
        if driver is None:
            return CredentialReplacementRequestResult(
                CredentialReplacementRequestStatus.UNSUPPORTED,
                "Credential replacement is not supported for this device",
            )
        pin = await self._vault.retrieve_staged(self._handle(operation))
        try:
            return await driver.async_request_credential_replacement(
                self._driver_request(target, pin)
            )
        except Exception:
            return CredentialReplacementRequestResult(
                CredentialReplacementRequestStatus.AMBIGUOUS,
                "Credential replacement request outcome is unknown",
            )
        finally:
            pin = ""

    async def _verify(
        self,
        operation: LifecycleOperation,
        target: dict[str, LifecyclePayloadValue],
    ) -> CredentialReplacementVerificationResult:
        driver = self._driver(target)
        if driver is None:
            return CredentialReplacementVerificationResult(
                CredentialReplacementVerificationStatus.UNSUPPORTED,
                "Credential replacement verification is not supported for this device",
            )
        pin = await self._vault.retrieve_staged(self._handle(operation))
        try:
            return await driver.async_verify_credential_replacement(
                self._driver_request(target, pin)
            )
        except Exception:
            return CredentialReplacementVerificationResult(
                CredentialReplacementVerificationStatus.RETRYABLE_FAILURE,
                "Credential replacement could not be verified",
            )
        finally:
            pin = ""

    async def _promote(self, operation: LifecycleOperation) -> LifecycleOperation:
        try:
            handle = self._handle(operation)
            receipt = await self._vault.promotion_receipt(handle)
            if receipt is None:
                receipt = await self._vault.promote(handle)
        except Exception:
            await self._pause_operation(
                operation,
                "Vault promotion could not be completed",
                retryable=True,
            )
        try:
            self._validate_receipt(operation, receipt)
        except ConcurrentCredentialReplacementError:
            await self._pause_stale(operation)
            raise
        return await self._checkpoint(
            operation,
            phase="vault_promoted",
            current_step=len(self._targets(operation)) + 1,
            updates={"credential_revision": receipt.revision},
        )

    async def _finalize(self, operation: LifecycleOperation) -> LifecycleOperation:
        credential_id = VaultCredentialId.from_string(cast(str, operation.payload["credential_id"]))
        if await self._vault.revision(credential_id) != operation.payload.get(
            "credential_revision"
        ):
            await self._pause_stale(operation)
            raise ConcurrentCredentialReplacementError(
                "Credential changed before replacement finalization"
            )
        now = datetime.now(UTC)

        def mutate(snapshot: HomePassStorageData) -> LifecycleOperation:
            raw_operation = snapshot["data"]["lifecycle_operations"].get(
                str(operation.operation_id)
            )
            if raw_operation is None:
                raise ValueError("Credential replacement operation disappeared")
            current = LifecycleOperation.from_dict(raw_operation)
            if current.updated_at != operation.updated_at:
                raise ConcurrentCredentialReplacementError(
                    "Credential replacement changed concurrently"
                )
            self._validate_snapshot(snapshot, operation)
            revision = cast(int, operation.payload["credential_revision"])
            for target in self._targets(operation):
                key = f"{operation.payload['person_id']}:{target['access_point_id']}"
                metadata = AccessMetadata.from_dict(snapshot["data"]["access_metadata"][key])
                grant = AccessGrant.from_dict(snapshot["data"]["access_grants"][key])
                snapshot["data"]["access_metadata"][key] = cast(
                    StorageRecord,
                    replace(
                        metadata,
                        synchronization_status=SynchronizationStatus.SYNCHRONIZED,
                        credential_revision=revision,
                        updated_at=now,
                    ).to_dict(),
                )
                snapshot["data"]["access_grants"][key] = cast(
                    StorageRecord,
                    replace(
                        grant,
                        synchronization_status=SynchronizationStatus.SYNCHRONIZED,
                        updated_at=now,
                    ).to_dict(),
                )
            credential_record = snapshot["data"]["credential_metadata"].get(
                cast(str, operation.payload["person_id"])
            )
            if credential_record is not None:
                credential = CredentialMetadata.from_dict(credential_record)
                if credential.credential_id != credential_id:
                    raise ConcurrentCredentialReplacementError(
                        "Person credential metadata changed concurrently"
                    )
                snapshot["data"]["credential_metadata"][str(credential.person_id)] = cast(
                    StorageRecord,
                    replace(credential, updated_at=now).to_dict(),
                )
            payload = dict(operation.payload)
            payload.update(phase="completed", error_summary=None, resumable=False)
            completed = replace(
                operation,
                status=LifecycleOperationStatus.COMPLETED,
                payload=payload,
                current_step=len(self._targets(operation)) + 2,
                retry_count=0,
                updated_at=now,
            )
            snapshot["data"]["lifecycle_operations"][str(operation.operation_id)] = cast(
                StorageRecord, completed.to_dict()
            )
            return completed

        try:
            completed = await self._storage.async_transaction(mutate)
        except ConcurrentCredentialReplacementError:
            await self._pause_stale(operation)
            raise
        except Exception:
            await self._pause_operation(
                operation,
                "Credential replacement finalization could not be completed",
                retryable=True,
            )
        self._reset_reveal_rate_limits(operation)
        if self._synchronization_status_service is not None:
            await self._synchronization_status_service.lifecycle_changed(completed)
        await self._record_completed_activity(completed)
        return completed

    def _reset_reveal_rate_limits(self, operation: LifecycleOperation) -> None:
        """Clear only prior-authority buckets after durable finalization."""
        if self._reveal_rate_limit_reset is None:
            return
        person_id = UUID(cast(str, operation.payload["person_id"]))
        for target in self._targets(operation):
            self._reveal_rate_limit_reset(
                person_id,
                UUID(cast(str, target["access_point_id"])),
            )
        self._reveal_rate_limit_reset(person_id, None)

    async def _capture_context(self, person_id: UUID) -> dict[str, LifecyclePayloadValue]:
        snapshot = await self._storage.async_load()
        raw_person = snapshot["data"]["people"].get(str(person_id))
        if raw_person is None:
            raise PersonNotFoundError(str(person_id))
        person = Person.from_dict(raw_person)
        grants = sorted(
            (
                AccessGrant.from_dict(record)
                for record in snapshot["data"]["access_grants"].values()
                if UUID(cast(str, record["person_id"])) == person_id
            ),
            key=lambda grant: str(grant.access_point_id),
        )
        credential_record = snapshot["data"]["credential_metadata"].get(str(person_id))
        credential_ids = {grant.credential_id for grant in grants}
        if len(credential_ids) > 1:
            raise ConcurrentCredentialReplacementError("Person access credentials are inconsistent")
        authority = (
            None if credential_record is None else CredentialMetadata.from_dict(credential_record)
        )
        if authority is not None and not authority.enabled:
            raise ValidationError("This User's PIN is disabled")
        if credential_ids:
            credential_id = VaultCredentialId(next(iter(credential_ids)))
            if authority is not None and authority.credential_id != credential_id:
                raise ConcurrentCredentialReplacementError(
                    "Person credential authority is inconsistent"
                )
        elif authority is not None:
            credential_id = authority.credential_id
        else:
            raise ValidationError("Person has no credential to replace")
        self._validate_credential_exclusivity(snapshot, person_id, credential_id)
        vault_revision = await self._vault.revision(credential_id)
        targets: list[LifecyclePayloadValue] = []
        expected_grants: list[LifecyclePayloadValue] = []
        for grant in grants:
            key = f"{person_id}:{grant.access_point_id}"
            raw_metadata = snapshot["data"]["access_metadata"].get(key)
            if raw_metadata is None:
                raise ConcurrentCredentialReplacementError(
                    "Access synchronization metadata is missing"
                )
            metadata = AccessMetadata.from_dict(raw_metadata)
            if metadata.vault_credential_id != credential_id:
                raise ConcurrentCredentialReplacementError(
                    "Access credential state is inconsistent"
                )
            if metadata.credential_revision != vault_revision:
                await self._verify_current_credential(metadata, credential_id)
            expected_grants.append(
                {
                    "access_point_id": str(grant.access_point_id),
                    "access_grant_id": str(grant.access_grant_id),
                    "updated_at": grant.updated_at.isoformat(),
                }
            )
            targets.append(
                {
                    "access_point_id": str(grant.access_point_id),
                    "target_device": metadata.lock_entity_id,
                    "driver": metadata.driver.value,
                    "slot": metadata.slot,
                    "expected_credential_revision": metadata.credential_revision,
                    "expected_metadata_updated_at": metadata.updated_at.isoformat(),
                    "state": "request_not_started",
                    "request_result": None,
                    "verification_result": None,
                    "timestamp": self._timestamp(),
                    "error_summary": None,
                }
            )
        return {
            "person_id": str(person_id),
            "expected_person_updated_at": person.updated_at.isoformat(),
            "credential_id": str(credential_id),
            "expected_vault_revision": vault_revision,
            "expected_grants": expected_grants,
            "targets": targets,
        }

    async def _verify_current_credential(
        self,
        metadata: AccessMetadata,
        credential_id: VaultCredentialId,
    ) -> None:
        """Confirm a legacy revision mismatch without changing the device."""
        try:
            driver = self._driver_resolver(metadata.driver)
            if driver is None or not driver.supports_exact_pin_readback(metadata.lock_entity_id):
                raise ConcurrentCredentialReplacementError(
                    "Access credential revision could not be verified"
                )
            current_pin = await self._vault.retrieve(credential_id)
            try:
                result = await driver.async_verify_credential_replacement(
                    CredentialReplacementRequest(
                        target_device=metadata.lock_entity_id,
                        slot=metadata.slot,
                        new_pin=current_pin,
                    )
                )
            finally:
                current_pin = ""
        except ConcurrentCredentialReplacementError:
            raise
        except Exception as err:
            raise ConcurrentCredentialReplacementError(
                "Access credential revision could not be verified"
            ) from err
        if result.status is not CredentialReplacementVerificationStatus.REPLACEMENT_CONFIRMED:
            raise ConcurrentCredentialReplacementError(
                "Access credential revision could not be verified"
            )

    async def _revalidate(self, operation: LifecycleOperation, *, include_vault: bool) -> None:
        snapshot = await self._storage.async_load()
        try:
            self._validate_snapshot(snapshot, operation)
            if include_vault:
                credential_id = VaultCredentialId.from_string(
                    cast(str, operation.payload["credential_id"])
                )
                revision = await self._vault.revision(credential_id)
                if revision != operation.payload["expected_vault_revision"]:
                    raise ConcurrentCredentialReplacementError(
                        "Credential changed during replacement"
                    )
        except ConcurrentCredentialReplacementError:
            await self._pause_stale(operation)
            raise

    @staticmethod
    def _validate_snapshot(snapshot: HomePassStorageData, operation: LifecycleOperation) -> None:
        person_id = cast(str, operation.payload["person_id"])
        raw_person = snapshot["data"]["people"].get(person_id)
        if raw_person is None:
            raise ConcurrentCredentialReplacementError("Person changed during replacement")
        person = Person.from_dict(raw_person)
        if person.updated_at.isoformat() != operation.payload["expected_person_updated_at"]:
            raise ConcurrentCredentialReplacementError("Person changed during replacement")
        expected_grants = {
            cast(str, item["access_point_id"]): item
            for item in cast(list[LifecyclePayloadValue], operation.payload["expected_grants"])
            if isinstance(item, dict)
        }
        targets = {
            cast(str, target["access_point_id"]): target
            for target in CredentialReplacementLifecycleService._targets(operation)
        }
        current_grants = {
            str(grant.access_point_id): grant
            for record in snapshot["data"]["access_grants"].values()
            if (grant := AccessGrant.from_dict(record)).person_id == person.person_id
        }
        if set(current_grants) != set(expected_grants) or set(targets) != set(expected_grants):
            raise ConcurrentCredentialReplacementError("Access changed during replacement")
        credential_id = cast(str, operation.payload["credential_id"])
        CredentialReplacementLifecycleService._validate_credential_exclusivity(
            snapshot,
            person.person_id,
            VaultCredentialId.from_string(credential_id),
        )
        expected_revision = cast(int, operation.payload["expected_vault_revision"])
        for access_point_id, grant in current_grants.items():
            expected_grant = expected_grants[access_point_id]
            if (
                str(grant.access_grant_id) != expected_grant["access_grant_id"]
                or grant.updated_at.isoformat() != expected_grant["updated_at"]
                or str(grant.credential_id) != credential_id
            ):
                raise ConcurrentCredentialReplacementError("Access changed during replacement")
            key = f"{person_id}:{access_point_id}"
            raw_metadata = snapshot["data"]["access_metadata"].get(key)
            if raw_metadata is None:
                raise ConcurrentCredentialReplacementError("Access changed during replacement")
            metadata = AccessMetadata.from_dict(raw_metadata)
            target = targets[access_point_id]
            expected_metadata_revision = cast(
                int,
                target.get("expected_credential_revision", expected_revision),
            )
            if (
                metadata.updated_at.isoformat() != target["expected_metadata_updated_at"]
                or str(metadata.vault_credential_id) != credential_id
                or metadata.credential_revision != expected_metadata_revision
                or metadata.lock_entity_id != target["target_device"]
                or metadata.slot != target["slot"]
                or metadata.driver.value != target["driver"]
            ):
                raise ConcurrentCredentialReplacementError("Access changed during replacement")

    @staticmethod
    def _validate_credential_exclusivity(
        snapshot: HomePassStorageData,
        person_id: UUID,
        credential_id: VaultCredentialId,
    ) -> None:
        """Reject replacement when Vault authority is inconsistent or shared."""
        for record in snapshot["data"]["access_grants"].values():
            grant = AccessGrant.from_dict(record)
            if grant.person_id != person_id and grant.credential_id == credential_id.value:
                raise ConcurrentCredentialReplacementError(
                    "Credential is referenced by another Person"
                )
        for record in snapshot["data"]["access_metadata"].values():
            metadata = AccessMetadata.from_dict(record)
            if metadata.person_id != person_id and metadata.vault_credential_id == credential_id:
                raise ConcurrentCredentialReplacementError(
                    "Credential is referenced by another Person"
                )
        for record in snapshot["data"]["credential_metadata"].values():
            credential = CredentialMetadata.from_dict(record)
            if credential.person_id == person_id:
                if credential.credential_id != credential_id:
                    raise ConcurrentCredentialReplacementError(
                        "Person credential authority is inconsistent"
                    )
            elif credential.credential_id == credential_id:
                raise ConcurrentCredentialReplacementError("Credential is owned by another Person")

    async def _active_operation(self, person_id: UUID) -> LifecycleOperation | None:
        for operation in await self._lifecycle_manager.load_incomplete():
            if operation.operation_type == self.OPERATION_TYPE and operation.payload.get(
                "person_id"
            ) == str(person_id):
                return operation
        return None

    async def _checkpoint(
        self,
        operation: LifecycleOperation,
        *,
        phase: str,
        status: LifecycleOperationStatus = LifecycleOperationStatus.RUNNING,
        current_step: int | None = None,
        updates: dict[str, LifecyclePayloadValue] | None = None,
    ) -> LifecycleOperation:
        payload = dict(operation.payload)
        payload["phase"] = phase
        if updates:
            payload.update(updates)
        return await self._lifecycle_manager.checkpoint(
            operation.operation_id,
            payload=payload,
            status=status,
            current_step=current_step,
            retry_count=0,
        )

    async def _checkpoint_targets(
        self,
        operation: LifecycleOperation,
        targets: list[dict[str, LifecyclePayloadValue]],
        current_step: int,
    ) -> LifecycleOperation:
        payload = dict(operation.payload)
        payload["targets"] = cast(LifecyclePayloadValue, targets)
        return await self._lifecycle_manager.checkpoint(
            operation.operation_id,
            payload=payload,
            status=LifecycleOperationStatus.RUNNING,
            current_step=current_step,
            retry_count=0,
        )

    async def _pause(
        self,
        operation: LifecycleOperation,
        targets: list[dict[str, LifecyclePayloadValue]],
        target_index: int,
        *,
        retryable: bool,
    ) -> NoReturn:
        payload = dict(operation.payload)
        payload.update(
            targets=cast(LifecyclePayloadValue, targets),
            resumable=retryable,
        )
        await self._lifecycle_manager.record_failure(
            operation.operation_id,
            payload=payload,
            retryable=retryable,
        )
        await self._record_target_activity(
            ActivityEventType.CREDENTIAL_VERIFICATION_FAILED,
            operation,
            (target_index,),
            suffix="verification-failed",
        )
        raise LifecycleOperationExecutionError("Credential replacement did not complete")

    async def _pause_operation(
        self, operation: LifecycleOperation, message: str, *, retryable: bool
    ) -> NoReturn:
        payload = dict(operation.payload)
        payload.update(error_summary=message, resumable=retryable)
        await self._lifecycle_manager.record_failure(
            operation.operation_id,
            payload=payload,
            retryable=retryable,
        )
        await self._record_target_activity(
            ActivityEventType.SYNCHRONIZATION_ATTENTION_REQUIRED,
            operation,
            tuple(range(len(self._targets(operation)))),
            suffix="synchronization-attention",
        )
        raise LifecycleOperationExecutionError("Credential replacement did not complete")

    async def _pause_stale(self, operation: LifecycleOperation) -> None:
        payload = dict(operation.payload)
        payload.update(
            error_summary="Credential state changed during replacement",
            resumable=False,
        )
        await self._lifecycle_manager.record_failure(
            operation.operation_id,
            payload=payload,
            retryable=False,
        )
        await self._record_target_activity(
            ActivityEventType.SYNCHRONIZATION_ATTENTION_REQUIRED,
            operation,
            tuple(range(len(self._targets(operation)))),
            suffix="stale-attention",
        )

    async def _record_completed_activity(self, operation: LifecycleOperation) -> None:
        await self._record_target_activity(
            ActivityEventType.CREDENTIAL_UPDATED,
            operation,
            tuple(range(len(self._targets(operation)))),
            suffix="credential-updated",
            succeeded=True,
        )

    async def _record_target_activity(
        self,
        event_type: ActivityEventType,
        operation: LifecycleOperation,
        target_indexes: tuple[int, ...],
        *,
        suffix: str,
        succeeded: bool = False,
    ) -> None:
        """Record safe lifecycle milestones using one stable operation identity."""
        if self._activity_producer is None:
            return
        try:
            snapshot = await self._storage.async_load()
            person_id = UUID(cast(str, operation.payload["person_id"]))
            raw_person = snapshot["data"]["people"].get(str(person_id))
            if raw_person is None:
                return
            person = Person.from_dict(raw_person)
            access_points = {
                access_point.id: access_point
                for record in snapshot["data"]["access_points"].values()
                for access_point in (AccessPoint.from_dict(record),)
            }
            targets = self._targets(operation)
            for index in target_indexes:
                access_point_id = UUID(cast(str, targets[index]["access_point_id"]))
                access_point = access_points.get(access_point_id)
                if access_point is None:
                    continue
                await self._activity_producer.record(
                    event_type,
                    occurred_at=operation.updated_at,
                    source_event_key=(
                        f"credential-replacement:{operation.operation_id}:"
                        f"{access_point_id}:{suffix}"
                    ),
                    person=person,
                    access_point=access_point,
                    correlation_id=operation.operation_id,
                    outcome=(ActivityOutcome.SUCCEEDED if succeeded else ActivityOutcome.FAILED),
                )
        except Exception:  # noqa: BLE001 - Activity context cannot affect lifecycle state
            _LOGGER.error("Activity context was unavailable for credential replacement")

    def _driver(
        self, target: dict[str, LifecyclePayloadValue]
    ) -> CredentialReplacementDriver | None:
        try:
            return self._driver_resolver(AccessDriver(cast(str, target["driver"])))
        except KeyError, TypeError, ValueError:
            return None

    @staticmethod
    def _driver_request(
        target: dict[str, LifecyclePayloadValue], pin: str
    ) -> CredentialReplacementRequest:
        return CredentialReplacementRequest(
            target_device=cast(str, target["target_device"]),
            slot=cast(int, target["slot"]),
            new_pin=pin,
        )

    @staticmethod
    def _targets(operation: LifecycleOperation) -> list[dict[str, LifecyclePayloadValue]]:
        raw_targets = operation.payload.get("targets")
        if not isinstance(raw_targets, list) or not all(
            isinstance(target, dict) for target in raw_targets
        ):
            raise CredentialReplacementError("Credential replacement targets are invalid")
        return [dict(cast(dict[str, LifecyclePayloadValue], target)) for target in raw_targets]

    @staticmethod
    def _handle(operation: LifecycleOperation) -> StagedSecretHandle:
        try:
            return StagedSecretHandle.from_string(cast(str, operation.payload["staged_handle"]))
        except (KeyError, TypeError, ValueError) as err:
            raise CredentialReplacementError(
                "Credential replacement staging handle is invalid"
            ) from err

    @staticmethod
    def _validate_receipt(operation: LifecycleOperation, receipt: VaultPromotionReceipt) -> None:
        if str(receipt.credential_id) != operation.payload["credential_id"]:
            raise ConcurrentCredentialReplacementError(
                "Vault promotion target changed during replacement"
            )
        if receipt.revision != cast(int, operation.payload["expected_vault_revision"]) + 1:
            raise ConcurrentCredentialReplacementError(
                "Vault promotion revision changed during replacement"
            )

    @staticmethod
    def _validate_pin(pin: str) -> None:
        if (
            not isinstance(pin, str)
            or not 4 <= len(pin) <= 10
            or not pin.isascii()
            or not pin.isdigit()
        ):
            raise ValidationError("PIN must contain 4 to 10 digits")

    @staticmethod
    def _timestamp() -> str:
        return datetime.now(UTC).isoformat()
