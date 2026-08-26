"""Application service for editing a Person's physical access assignments."""

from __future__ import annotations

import asyncio
import logging
import secrets
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import partial
from typing import TYPE_CHECKING, Literal
from uuid import UUID, uuid4

from ..exceptions import (
    AccessUpdateError,
    AccessUpdateStage,
    CredentialAuthorityConflictError,
)
from ..models import (
    AccessDriver,
    AccessMetadata,
    AccessPoint,
    ActivityEventType,
    ActivityOutcome,
    Person,
    SynchronizationHistoryEventType,
    SynchronizationStatus,
)
from ..providers.schedule import authorization_schedule_from_homepass
from ..repositories.credential_metadata import CredentialMetadataRepository
from ..vault import CredentialVaultProtocol, VaultCredentialId
from .access_metadata import AccessMetadataService
from .access_point import AccessPointService
from .activity_producer import ActivityProducer
from .give_access import NumberedUserCodeDriver
from .person import PersonService
from .synchronization_history import SynchronizationHistoryService
from .zwave_sync import DriverCommandStatus, VerificationStatus

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Iterable

    from .schedule import ScheduleService

_LOGGER = logging.getLogger(__name__)

VERIFICATION_ATTEMPTS = 5
VERIFICATION_DELAY = 2.0

type AccessUpdateStatus = Literal[
    "completed",
    "pending_verification",
    "needs_attention",
    "out_of_sync",
]


def _next_available_keypad_slot(
    metadata: Iterable[AccessMetadata], access_point_id: UUID
) -> int:
    """Return the first unowned logical credential slot for one keypad Door."""
    occupied = {
        record.slot for record in metadata if record.access_point_id == access_point_id
    }
    slot = 1
    while slot in occupied:
        slot += 1
    return slot


@dataclass(frozen=True, slots=True)
class AccessPointUpdateResult:
    """PIN-safe result for one affected Access Point."""

    access_point_id: UUID
    status: AccessUpdateStatus


@dataclass(frozen=True, slots=True)
class AccessUpdateResult:
    """Non-secret delta applied to one Person's access assignments."""

    added: tuple[UUID, ...]
    removed: tuple[UUID, ...]
    unchanged: tuple[UUID, ...]
    status: AccessUpdateStatus
    access_points: tuple[AccessPointUpdateResult, ...]


class AccessManagementService:
    """Apply access selection deltas without exposing stored credentials."""

    def __init__(
        self,
        person_service: PersonService,
        access_point_service: AccessPointService,
        driver: NumberedUserCodeDriver,
        metadata_service: AccessMetadataService,
        credential_vault: CredentialVaultProtocol,
        synchronization_history_service: SynchronizationHistoryService | None = None,
        activity_producer: ActivityProducer | None = None,
        credential_metadata_repository: CredentialMetadataRepository | None = None,
        schedule_service: ScheduleService | None = None,
        access_removed_observer: Callable[[UUID, UUID], Awaitable[None]] | None = None,
    ) -> None:
        """Initialize the application service boundaries."""
        self._person_service = person_service
        self._access_point_service = access_point_service
        self._driver = driver
        self._metadata_service = metadata_service
        self._credential_vault = credential_vault
        self._synchronization_history_service = synchronization_history_service
        self._activity_producer = activity_producer
        self._credential_metadata_repository = credential_metadata_repository
        self._schedule_service = schedule_service
        self._access_removed_observer = access_removed_observer
        self._operation_lock = asyncio.Lock()
        self._verification_tasks: dict[tuple[UUID, UUID], asyncio.Task[None]] = {}

    async def update_access(
        self,
        person_id: UUID,
        selected_access_point_ids: tuple[UUID, ...],
    ) -> AccessUpdateResult:
        """Apply only additions and removals between current and selected access."""
        async with self._operation_lock:
            return await self._update_access(uuid4(), person_id, selected_access_point_ids)

    async def add_access(
        self,
        person_id: UUID,
        access_point_ids: tuple[UUID, ...],
        *,
        credential_id: VaultCredentialId | None = None,
        plaintext: str | None = None,
    ) -> AccessUpdateResult:
        """Add assignments without removing or overwriting existing relationships."""
        if (credential_id is None) is not (plaintext is None):
            raise ValueError("Credential ID and PIN must be supplied together")
        async with self._operation_lock:
            current = await self._metadata_service.list_for_person(person_id)
            selected = tuple(
                dict.fromkeys((*[record.access_point_id for record in current], *access_point_ids))
            )
            return await self._update_access(
                uuid4(),
                person_id,
                selected,
                credential_id=credential_id,
                plaintext=plaintext,
            )

    async def current_access_point_ids(self, person_id: UUID) -> tuple[UUID, ...]:
        """Return stable current assignment IDs without exposing driver metadata."""
        return tuple(
            record.access_point_id
            for record in await self._metadata_service.list_for_person(person_id)
        )

    async def current_access_point_statuses(
        self,
        person_id: UUID,
    ) -> dict[UUID, AccessUpdateStatus]:
        """Return safe statuses, marking any one-sided persisted relationship unsafe."""
        metadata = await self._metadata_service.list_for_person(person_id)
        grant_ids = {
            grant.access_point_id
            for grant in await self._metadata_service.list_grants_for_person(person_id)
        }
        statuses = {
            record.access_point_id: self._metadata_result_status(record) for record in metadata
        }
        for access_point_id in grant_ids - statuses.keys():
            statuses[access_point_id] = "needs_attention"
        return statuses

    async def retry_provisioning_verification(
        self,
        person_id: UUID,
        access_point_id: UUID,
        *,
        expected_updated_at: datetime,
    ) -> VerificationStatus:
        """Retry exact readback for one accepted but unconfirmed PIN write."""
        async with self._operation_lock:
            metadata = next(
                (
                    record
                    for record in await self._metadata_service.list_for_person(person_id)
                    if record.access_point_id == access_point_id
                ),
                None,
            )
            if metadata is None or metadata.updated_at != expected_updated_at:
                raise ValueError("Access synchronization context changed")
            if metadata.synchronization_status is not SynchronizationStatus.UNKNOWN:
                raise ValueError("Access is not awaiting PIN verification")
            if metadata.vault_credential_id is None:
                raise CredentialAuthorityConflictError()
            grants = await self._metadata_service.list_grants_for_person(person_id)
            grant = next(
                (item for item in grants if item.access_point_id == access_point_id),
                None,
            )
            authority = (
                None
                if self._credential_metadata_repository is None
                else await self._credential_metadata_repository.resolve_for_provisioning(person_id)
            )
            if (
                grant is None
                or authority is None
                or not authority.enabled
                or grant.credential_id != metadata.vault_credential_id.value
                or authority.credential_id != metadata.vault_credential_id
            ):
                raise CredentialAuthorityConflictError()
            target = await self._access_point_service.get_target(access_point_id)
            if target.lock_entity_id != metadata.lock_entity_id:
                raise ValueError("Access Point target changed")
            plaintext = await self._credential_vault.retrieve(metadata.vault_credential_id)
            try:
                verification_status = await self._driver.verify_pin(
                    metadata.lock_entity_id,
                    metadata.slot,
                    plaintext,
                )
            finally:
                plaintext = ""
            if verification_status == "verified":
                await self._metadata_service.update_synchronization_status(
                    metadata,
                    SynchronizationStatus.SYNCHRONIZED,
                )
                await self._record_history(
                    SynchronizationHistoryEventType.VERIFICATION_SUCCEEDED,
                    person_id,
                    access_point_id,
                )
            elif verification_status == "failed":
                await self._metadata_service.update_synchronization_status(
                    metadata,
                    SynchronizationStatus.MANUAL_ATTENTION_REQUIRED,
                )
                await self._record_history(
                    SynchronizationHistoryEventType.VERIFICATION_FAILED,
                    person_id,
                    access_point_id,
                )
            else:
                await self._record_history(
                    SynchronizationHistoryEventType.VERIFICATION_PENDING,
                    person_id,
                    access_point_id,
                )
            return verification_status

    async def retry_removal_verification(
        self,
        person_id: UUID,
        access_point_id: UUID,
        *,
        expected_updated_at: datetime,
    ) -> None:
        """Safely retry one removal after confirming the occupied slot is still ours."""
        async with self._operation_lock:
            metadata = next(
                (
                    record
                    for record in await self._metadata_service.list_for_person(person_id)
                    if record.access_point_id == access_point_id
                ),
                None,
            )
            if metadata is None or metadata.updated_at != expected_updated_at:
                raise ValueError("Access synchronization context changed")
            if metadata.synchronization_status is not SynchronizationStatus.RETRY_REQUIRED:
                raise ValueError("Access synchronization is not retryable")
            await self._retry_removal_command_if_safe(metadata)
            pending = await self._metadata_service.update_synchronization_status(
                metadata,
                SynchronizationStatus.PENDING,
            )
            await self._verify_removal(uuid4(), pending)

    async def _retry_removal_command_if_safe(self, metadata: AccessMetadata) -> None:
        """Repeat a clear only when exact readback proves the slot still belongs to HomePASS."""
        removed = await self._driver.verify_pin_removed(
            metadata.lock_entity_id,
            metadata.slot,
        )
        if removed is not False:
            # A clear slot can be finalized by normal verification. Unknown readback
            # must remain read-only because HomePASS cannot prove what occupies it.
            return
        if metadata.vault_credential_id is None:
            raise CredentialAuthorityConflictError()
        plaintext = await self._credential_vault.retrieve(metadata.vault_credential_id)
        try:
            ownership = await self._driver.verify_pin(
                metadata.lock_entity_id,
                metadata.slot,
                plaintext,
            )
        finally:
            plaintext = ""
        if ownership == "failed":
            await self._mark_verification_state(
                metadata,
                SynchronizationStatus.MANUAL_ATTENTION_REQUIRED,
            )
            raise ValueError("The lock slot no longer contains this user's HomePASS credential")
        if ownership != "verified":
            # Do not clear an occupied slot if exact credential ownership cannot be
            # established. The following verifier will preserve the retry state.
            return
        command = await self._driver.request_remove_pin(
            metadata.lock_entity_id,
            metadata.slot,
        )
        if command.status is not DriverCommandStatus.ACCEPTED:
            await self._mark_verification_state(
                metadata,
                SynchronizationStatus.MANUAL_ATTENTION_REQUIRED,
            )
            raise ValueError("The lock did not accept the removal retry")

    async def _update_access(
        self,
        operation_id: UUID,
        person_id: UUID,
        selected_access_point_ids: tuple[UUID, ...],
        *,
        credential_id: VaultCredentialId | None = None,
        plaintext: str | None = None,
    ) -> AccessUpdateResult:
        """Validate and execute one serialized access delta."""
        self._log_stage(operation_id, person_id, None, AccessUpdateStage.REQUEST_VALIDATION)
        try:
            person = await self._person_service.get_person(person_id)
            if len(set(selected_access_point_ids)) != len(selected_access_point_ids):
                raise ValueError("Access point selections must be unique")
            available = {
                access_point.id: access_point
                for access_point in await self._access_point_service.list_access_points()
            }
            if not set(selected_access_point_ids) <= available.keys():
                raise ValueError("One or more selected access points are unavailable")
        except Exception as err:
            self._log_failure(
                operation_id,
                person_id,
                None,
                AccessUpdateStage.REQUEST_VALIDATION,
                err,
            )
            raise

        self._log_stage(operation_id, person_id, None, AccessUpdateStage.DELTA_CALCULATION)
        try:
            current = await self._metadata_service.list_for_person(person_id)
            grants = await self._metadata_service.list_grants_for_person(person_id)
            if {metadata.access_point_id for metadata in current} != {
                grant.access_point_id for grant in grants
            }:
                raise ValueError("Access Grant and synchronization metadata do not match")
        except Exception as err:
            raise self._stage_error(
                operation_id,
                person_id,
                None,
                AccessUpdateStage.DELTA_CALCULATION,
                err,
            ) from err
        current_by_id = {metadata.access_point_id: metadata for metadata in current}
        selected = set(selected_access_point_ids)
        additions = tuple(
            access_point_id
            for access_point_id in available
            if access_point_id not in current_by_id and access_point_id in selected
        )
        for access_point_id in additions:
            target = await self._access_point_service.get_target(access_point_id)
            if not target.pin_capable:
                raise ValueError(
                    f"{target.access_point.display_name} supports app control but not PIN access"
                )
        removals = tuple(
            metadata for metadata in current if metadata.access_point_id not in selected
        )
        unchanged = tuple(
            access_point_id
            for access_point_id in available
            if access_point_id in current_by_id and access_point_id in selected
        )
        if not additions and not removals:
            return self._result((), (), unchanged, current_by_id)

        try:
            credential_id, plaintext, created_credential = await self._credential_for_additions(
                person_id,
                current,
                bool(additions),
                credential_id=credential_id,
                plaintext=plaintext,
            )
        except AccessUpdateError:
            raise
        except Exception as err:
            raise self._stage_error(
                operation_id,
                person_id,
                None,
                AccessUpdateStage.FINAL_PERSISTENCE,
                err,
            ) from err
        if additions:
            assert plaintext is not None
            for access_point_id in additions:
                target = await self._access_point_service.get_target(access_point_id)
                try:
                    self._driver.validate_pin(target.lock_entity_id, plaintext)
                except ValueError as err:
                    raise self._stage_error(
                        operation_id,
                        person_id,
                        access_point_id,
                        AccessUpdateStage.REQUEST_VALIDATION,
                        err,
                        exception_type="CredentialCompatibilityError",
                        sanitized_message=(
                            "Saved PIN is incompatible with the selected access provider"
                        ),
                    ) from err
        added_assignments: list[tuple[AccessDriver, UUID, str, int]] = []
        added_activity: list[tuple[AccessPoint, AccessMetadata, VerificationStatus]] = []
        addition_statuses: dict[UUID, AccessUpdateStatus] = {}
        provisioning_access_point_id: UUID | None = None
        try:
            if additions:
                assert credential_id is not None and plaintext is not None
                credential_revision = await self._credential_vault.revision(credential_id)
                for access_point_id in additions:
                    provisioning_access_point_id = access_point_id
                    target = await self._access_point_service.get_target(access_point_id)
                    await self._record_history(
                        SynchronizationHistoryEventType.PROVISIONING_STARTED,
                        person_id,
                        access_point_id,
                    )
                    if target.driver is None:
                        raise ValueError("PIN access driver is unavailable")
                    provider_schedule = None
                    provider_enabled = person.enabled
                    if (
                        target.driver is AccessDriver.NUKI
                        and self._schedule_service is not None
                    ):
                        schedule = await self._schedule_service.get_schedule(person.schedule_id)
                        provider_schedule = authorization_schedule_from_homepass(schedule)
                        provider_enabled = provider_enabled and schedule.enabled
                    if target.driver is AccessDriver.HOMEPASS_KEYPAD:
                        verification_status: VerificationStatus = "verified"
                        credential_slot = _next_available_keypad_slot(
                            await self._metadata_service.list_all(), access_point_id
                        )
                    else:
                        provisioned = await self._driver.provision_pin(
                            target.lock_entity_id,
                            plaintext,
                            display_name=person.display_name,
                            schedule=provider_schedule,
                            enabled=provider_enabled,
                        )
                        if (
                            provisioned.verification_status not in {"verified", "inconclusive"}
                            or provisioned.credential_slot is None
                        ):
                            raise self._stage_error(
                                operation_id,
                                person_id,
                                access_point_id,
                                AccessUpdateStage.FINAL_PERSISTENCE,
                            )
                        verification_status = provisioned.verification_status
                        credential_slot = provisioned.credential_slot
                    added_assignments.append(
                        (
                            target.driver,
                            access_point_id,
                            target.lock_entity_id,
                            credential_slot,
                        )
                    )
                    saved = await self._metadata_service.record_provisioning(
                        person_id,
                        access_point_id,
                        target.lock_entity_id,
                        credential_slot,
                        verification_status,
                        credential_id,
                        target.driver,
                        credential_revision=credential_revision,
                    )
                    added_activity.append((target.access_point, saved, verification_status))
                    addition_statuses[access_point_id] = self._metadata_result_status(saved)
        except Exception as err:
            if provisioning_access_point_id is not None:
                await self._record_history(
                    SynchronizationHistoryEventType.PROVISIONING_FAILED,
                    person_id,
                    provisioning_access_point_id,
                )
            await self._rollback_additions(person_id, added_assignments)
            if created_credential and credential_id is not None:
                await self._delete_created_credential_if_safe(person_id, credential_id)
            if provisioning_access_point_id is not None:
                access_point = available.get(provisioning_access_point_id)
                if access_point is not None:
                    await self._record_activity(
                        ActivityEventType.SYNCHRONIZATION_ATTENTION_REQUIRED,
                        operation_id=operation_id,
                        source_event_key=(
                            f"access-update:{operation_id}:"
                            f"{provisioning_access_point_id}:synchronization-failed"
                        ),
                        person=person,
                        access_point=access_point,
                        outcome=ActivityOutcome.FAILED,
                    )
            if isinstance(err, AccessUpdateError) and err.access_point_id is not None:
                raise
            raise self._stage_error(
                operation_id,
                person_id,
                provisioning_access_point_id,
                AccessUpdateStage.FINAL_PERSISTENCE,
                err,
            ) from err
        finally:
            plaintext = None

        for access_point, saved, verification_status in added_activity:
            await self._record_activity(
                ActivityEventType.ACCESS_GRANTED,
                operation_id=operation_id,
                source_event_key=(f"access-update:{operation_id}:{access_point.id}:access-granted"),
                person=person,
                access_point=access_point,
                occurred_at=saved.updated_at,
                outcome=ActivityOutcome.SUCCEEDED,
            )
            if verification_status == "verified":
                await self._record_activity(
                    ActivityEventType.CREDENTIAL_ADDED,
                    operation_id=operation_id,
                    source_event_key=(
                        f"access-update:{operation_id}:{access_point.id}:credential-added"
                    ),
                    person=person,
                    access_point=access_point,
                    occurred_at=saved.updated_at,
                    outcome=ActivityOutcome.SUCCEEDED,
                )

        removed_ids: list[UUID] = []
        removal_statuses: dict[UUID, AccessUpdateStatus] = {}
        for metadata in removals:
            if metadata.driver is AccessDriver.HOMEPASS_KEYPAD:
                context = await self._relationship_context(metadata)
                await self._metadata_service.remove_access(
                    metadata.person_id,
                    metadata.access_point_id,
                )
                await self._record_history(
                    SynchronizationHistoryEventType.SYNCHRONIZATION_RESTORED,
                    metadata.person_id,
                    metadata.access_point_id,
                )
                if context is not None:
                    activity_person, activity_access_point = context
                    await self._record_activity(
                        ActivityEventType.ACCESS_REVOKED,
                        operation_id=operation_id,
                        source_event_key=(
                            f"access-removal:{metadata.person_id}:"
                            f"{metadata.access_point_id}:{metadata.updated_at.isoformat()}:"
                            "access-revoked"
                        ),
                        person=activity_person,
                        access_point=activity_access_point,
                        outcome=ActivityOutcome.SUCCEEDED,
                    )
                removed_ids.append(metadata.access_point_id)
                removal_statuses[metadata.access_point_id] = "completed"
                continue
            if metadata.synchronization_status is SynchronizationStatus.PENDING:
                self._schedule_verification(operation_id, metadata)
                removed_ids.append(metadata.access_point_id)
                removal_statuses[metadata.access_point_id] = "pending_verification"
                continue
            if metadata.synchronization_status is SynchronizationStatus.SYNCHRONIZING:
                # These states represent an operation already started or one whose
                # acknowledgement is no longer certain. A repeated Save must never
                # duplicate the physical command.
                removed_ids.append(metadata.access_point_id)
                removal_statuses[metadata.access_point_id] = "needs_attention"
                continue
            if metadata.synchronization_status in {
                SynchronizationStatus.MANUAL_ATTENTION_REQUIRED,
                SynchronizationStatus.RETRY_REQUIRED,
            }:
                # An explicit repeat acts only as a verification retry. It never
                # repeats the physical clear operation.
                metadata = await self._metadata_service.update_synchronization_status(
                    metadata, SynchronizationStatus.PENDING
                )
                self._schedule_verification(operation_id, metadata)
                removed_ids.append(metadata.access_point_id)
                removal_statuses[metadata.access_point_id] = "pending_verification"
                continue
            try:
                metadata = await self._metadata_service.update_synchronization_status(
                    metadata, SynchronizationStatus.SYNCHRONIZING
                )
            except Exception as err:
                raise self._stage_error(
                    operation_id,
                    person_id,
                    metadata.access_point_id,
                    AccessUpdateStage.FINAL_PERSISTENCE,
                    err,
                ) from err
            self._log_stage(
                operation_id,
                person_id,
                metadata.access_point_id,
                AccessUpdateStage.LOCK_SLOT_REMOVAL,
                synchronization_state=SynchronizationStatus.SYNCHRONIZING,
            )
            try:
                command = await self._driver.request_remove_pin(
                    metadata.lock_entity_id, metadata.slot
                )
            except Exception as err:
                with suppress(Exception):
                    await self._metadata_service.update_synchronization_status(
                        metadata, SynchronizationStatus.MANUAL_ATTENTION_REQUIRED
                    )
                context = await self._relationship_context(metadata)
                if context is not None:
                    activity_person, activity_access_point = context
                    await self._record_activity(
                        ActivityEventType.SYNCHRONIZATION_ATTENTION_REQUIRED,
                        operation_id=operation_id,
                        source_event_key=(
                            f"access-removal:{metadata.person_id}:"
                            f"{metadata.access_point_id}:{metadata.updated_at.isoformat()}:"
                            "command-failed"
                        ),
                        person=activity_person,
                        access_point=activity_access_point,
                        outcome=ActivityOutcome.FAILED,
                    )
                raise self._stage_error(
                    operation_id,
                    person_id,
                    metadata.access_point_id,
                    AccessUpdateStage.LOCK_SLOT_REMOVAL,
                    err,
                    synchronization_state=SynchronizationStatus.MANUAL_ATTENTION_REQUIRED,
                    driver_result=DriverCommandStatus.FAILED,
                ) from err
            if command.status is DriverCommandStatus.FAILED:
                with suppress(Exception):
                    await self._metadata_service.update_synchronization_status(
                        metadata, SynchronizationStatus.MANUAL_ATTENTION_REQUIRED
                    )
                context = await self._relationship_context(metadata)
                if context is not None:
                    activity_person, activity_access_point = context
                    await self._record_activity(
                        ActivityEventType.SYNCHRONIZATION_ATTENTION_REQUIRED,
                        operation_id=operation_id,
                        source_event_key=(
                            f"access-removal:{metadata.person_id}:"
                            f"{metadata.access_point_id}:{metadata.updated_at.isoformat()}:"
                            "command-rejected"
                        ),
                        person=activity_person,
                        access_point=activity_access_point,
                        outcome=ActivityOutcome.FAILED,
                    )
                raise self._stage_error(
                    operation_id,
                    person_id,
                    metadata.access_point_id,
                    AccessUpdateStage.LOCK_SLOT_REMOVAL,
                    exception_type="DriverCommandFailed",
                    sanitized_message="Lock rejected the removal command",
                    driver_result=command.status,
                )
            try:
                metadata = await self._metadata_service.update_synchronization_status(
                    metadata, SynchronizationStatus.PENDING
                )
            except Exception as err:
                self._stage_error(
                    operation_id,
                    person_id,
                    metadata.access_point_id,
                    AccessUpdateStage.FINAL_PERSISTENCE,
                    err,
                    synchronization_state=SynchronizationStatus.SYNCHRONIZING,
                    driver_result=command.status,
                )
                # SYNCHRONIZING was persisted before the accepted command. Keep
                # that durable recovery marker and verify without issuing another
                # physical command.
            self._log_stage(
                operation_id,
                person_id,
                metadata.access_point_id,
                AccessUpdateStage.LOCK_SLOT_REMOVAL,
                synchronization_state=SynchronizationStatus.PENDING,
                driver_result=command.status,
            )
            self._schedule_verification(operation_id, metadata)
            removed_ids.append(metadata.access_point_id)
            removal_statuses[metadata.access_point_id] = "pending_verification"

        return self._result(
            additions,
            tuple(removed_ids),
            unchanged,
            current_by_id,
            addition_statuses,
            removal_statuses,
        )

    @staticmethod
    def _result(
        additions: tuple[UUID, ...],
        removals: tuple[UUID, ...],
        unchanged: tuple[UUID, ...],
        current: dict[UUID, AccessMetadata],
        addition_statuses: dict[UUID, AccessUpdateStatus] | None = None,
        removal_statuses: dict[UUID, AccessUpdateStatus] | None = None,
    ) -> AccessUpdateResult:
        """Build a deterministic non-secret result for an access update."""
        added_statuses = addition_statuses or {}
        removed_statuses = removal_statuses or {}
        access_points: list[AccessPointUpdateResult] = [
            AccessPointUpdateResult(
                access_point_id,
                added_statuses.get(access_point_id, "completed"),
            )
            for access_point_id in additions
        ]
        access_points.extend(
            AccessPointUpdateResult(
                access_point_id,
                removed_statuses.get(access_point_id, "pending_verification"),
            )
            for access_point_id in removals
        )
        access_points.extend(
            AccessPointUpdateResult(
                access_point_id,
                AccessManagementService._metadata_result_status(current[access_point_id]),
            )
            for access_point_id in unchanged
        )
        overall: AccessUpdateStatus = "completed"
        for candidate in ("out_of_sync", "needs_attention", "pending_verification"):
            if any(item.status == candidate for item in access_points):
                overall = candidate
                break
        return AccessUpdateResult(
            additions,
            removals,
            unchanged,
            overall,
            tuple(access_points),
        )

    @staticmethod
    def _metadata_result_status(metadata: AccessMetadata) -> AccessUpdateStatus:
        """Map persisted synchronization state to the public safe result vocabulary."""
        if metadata.synchronization_status in {
            SynchronizationStatus.SYNCHRONIZING,
            SynchronizationStatus.PENDING,
        }:
            return "pending_verification"
        if metadata.synchronization_status is SynchronizationStatus.RETRY_REQUIRED:
            return "out_of_sync"
        if metadata.synchronization_status in {
            SynchronizationStatus.MANUAL_ATTENTION_REQUIRED,
            SynchronizationStatus.UNKNOWN,
        }:
            return "needs_attention"
        return "completed"

    async def _credential_for_additions(
        self,
        person_id: UUID,
        current: tuple[AccessMetadata, ...],
        has_additions: bool,
        *,
        credential_id: VaultCredentialId | None = None,
        plaintext: str | None = None,
    ) -> tuple[VaultCredentialId | None, str | None, bool]:
        """Retrieve or validate one explicit authoritative PIN for new access."""
        if not has_additions:
            return None, None, False
        credential_ids = {
            metadata.vault_credential_id
            for metadata in current
            if metadata.vault_credential_id is not None
        }
        if current and len(credential_ids) != 1:
            raise ValueError("Existing access does not have one usable credential")
        current_credential_id = next(iter(credential_ids), None)
        if self._credential_metadata_repository is None:
            raise CredentialAuthorityConflictError()
        person_credential = await self._credential_metadata_repository.resolve_for_provisioning(
            person_id
        )
        if person_credential is not None and not person_credential.enabled:
            raise ValueError("This User's PIN is disabled")
        person_credential_id = (
            None if person_credential is None else person_credential.credential_id
        )
        known_ids = {
            value
            for value in (credential_id, current_credential_id, person_credential_id)
            if value is not None
        }
        if len(known_ids) > 1:
            raise ValueError("Existing User credential authority is inconsistent")
        known_credential_id = next(iter(known_ids), None)
        if credential_id is not None and plaintext is not None:
            if known_credential_id is not None:
                stored_plaintext = await self._credential_vault.retrieve(known_credential_id)
                try:
                    if not secrets.compare_digest(plaintext, stored_plaintext):
                        raise ValueError("Supplied PIN does not match this User's credential")
                finally:
                    stored_plaintext = ""
            return credential_id, plaintext, False
        if known_credential_id is not None:
            return (
                known_credential_id,
                await self._credential_vault.retrieve(known_credential_id),
                False,
            )
        raise ValueError("This User does not yet have a PIN")

    async def _rollback_additions(
        self,
        person_id: UUID,
        assignments: list[tuple[AccessDriver, UUID, str, int]],
    ) -> None:
        """Best-effort rollback of additions completed in this operation."""
        for driver, access_point_id, lock_entity_id, slot in reversed(assignments):
            try:
                persisted = next(
                    (
                        record
                        for record in await self._metadata_service.list_for_person(person_id)
                        if record.access_point_id == access_point_id
                    ),
                    None,
                )
            except Exception:
                # An unknown local state is not safe to diverge from the device.
                continue
            if persisted is not None:
                try:
                    await self._metadata_service.update_synchronization_status(
                        persisted,
                        SynchronizationStatus.MANUAL_ATTENTION_REQUIRED,
                    )
                except Exception:
                    # Keep the known local and physical assignment together when
                    # HomePASS cannot first persist its rollback intent.
                    continue
            if driver is not AccessDriver.HOMEPASS_KEYPAD:
                try:
                    removed = await self._driver.remove_pin(lock_entity_id, slot)
                except Exception:
                    continue
                if not removed:
                    continue
            try:
                await self._metadata_service.remove_access(person_id, access_point_id)
            except Exception:
                # A persisted relationship was pre-marked before device I/O; a
                # one-sided survivor is also reported as attention by status lookup.
                continue

    async def _delete_created_credential_if_safe(
        self,
        person_id: UUID,
        credential_id: VaultCredentialId,
    ) -> None:
        """Delete a newly created Vault secret only after every local reference is gone."""
        try:
            released = await self._metadata_service.release_orphaned_person_credential(
                person_id,
                credential_id,
            )
        except Exception:  # noqa: BLE001 - uncertainty must retain the recoverable secret
            return
        if released:
            with suppress(Exception):
                await self._credential_vault.delete(credential_id)

    def _schedule_verification(self, operation_id: UUID, metadata: AccessMetadata) -> None:
        """Start one idempotent background verifier per access relationship."""
        key = (metadata.person_id, metadata.access_point_id)
        existing = self._verification_tasks.get(key)
        if existing is not None and not existing.done():
            return
        task = asyncio.create_task(self._verify_removal(operation_id, metadata))
        self._verification_tasks[key] = task
        task.add_done_callback(partial(self._forget_task, key))

    def _forget_task(
        self,
        key: tuple[UUID, UUID],
        completed: asyncio.Task[None],
    ) -> None:
        """Forget only the verifier instance that actually completed."""
        if self._verification_tasks.get(key) is completed:
            self._verification_tasks.pop(key, None)

    async def _verify_removal(self, operation_id: UUID, metadata: AccessMetadata) -> None:
        """Poll readback without repeating the physical removal command."""
        last_result: bool | None = None
        try:
            for attempt in range(VERIFICATION_ATTEMPTS):
                try:
                    last_result = await self._driver.verify_pin_removed(
                        metadata.lock_entity_id, metadata.slot
                    )
                except Exception as err:
                    self._log_failure(
                        operation_id,
                        metadata.person_id,
                        metadata.access_point_id,
                        AccessUpdateStage.LOCK_SLOT_REMOVAL,
                        err,
                        synchronization_state=SynchronizationStatus.MANUAL_ATTENTION_REQUIRED,
                    )
                    await self._mark_verification_state(
                        metadata, SynchronizationStatus.MANUAL_ATTENTION_REQUIRED
                    )
                    await self._record_history(
                        SynchronizationHistoryEventType.VERIFICATION_FAILED,
                        metadata.person_id,
                        metadata.access_point_id,
                    )
                    await self._record_removal_attention(operation_id, metadata)
                    return
                self._log_stage(
                    operation_id,
                    metadata.person_id,
                    metadata.access_point_id,
                    AccessUpdateStage.LOCK_SLOT_REMOVAL,
                    synchronization_state=SynchronizationStatus.PENDING,
                    driver_result=(
                        "verified"
                        if last_result is True
                        else "occupied"
                        if last_result is False
                        else "unknown"
                    ),
                )
                if last_result is True:
                    context = await self._relationship_context(metadata)
                    await self._finalize_verified_removal(operation_id, metadata)
                    await self._record_history(
                        SynchronizationHistoryEventType.VERIFICATION_SUCCEEDED,
                        metadata.person_id,
                        metadata.access_point_id,
                    )
                    await self._record_history(
                        SynchronizationHistoryEventType.SYNCHRONIZATION_RESTORED,
                        metadata.person_id,
                        metadata.access_point_id,
                    )
                    if context is not None:
                        person, access_point = context
                        await self._record_activity(
                            ActivityEventType.ACCESS_REVOKED,
                            operation_id=operation_id,
                            source_event_key=(
                                f"access-removal:{metadata.person_id}:"
                                f"{metadata.access_point_id}:{metadata.updated_at.isoformat()}:"
                                "access-revoked"
                            ),
                            person=person,
                            access_point=access_point,
                            outcome=ActivityOutcome.SUCCEEDED,
                        )
                        await self._record_activity(
                            ActivityEventType.CREDENTIAL_REMOVED,
                            operation_id=operation_id,
                            source_event_key=(
                                f"access-removal:{metadata.person_id}:"
                                f"{metadata.access_point_id}:{metadata.updated_at.isoformat()}:"
                                "credential-removed"
                            ),
                            person=person,
                            access_point=access_point,
                            outcome=ActivityOutcome.SUCCEEDED,
                        )
                    return
                if attempt + 1 < VERIFICATION_ATTEMPTS:
                    await asyncio.sleep(VERIFICATION_DELAY)
        except AccessUpdateError:
            await self._mark_verification_state(
                metadata, SynchronizationStatus.MANUAL_ATTENTION_REQUIRED
            )
            await self._record_history(
                SynchronizationHistoryEventType.VERIFICATION_FAILED,
                metadata.person_id,
                metadata.access_point_id,
            )
            await self._record_removal_attention(operation_id, metadata)
            return

        await self._mark_verification_state(
            metadata,
            (
                SynchronizationStatus.RETRY_REQUIRED
                if last_result is False
                else SynchronizationStatus.MANUAL_ATTENTION_REQUIRED
            ),
        )
        await self._record_history(
            SynchronizationHistoryEventType.VERIFICATION_FAILED,
            metadata.person_id,
            metadata.access_point_id,
        )
        await self._record_removal_attention(operation_id, metadata)

    async def _record_history(
        self,
        event_type: SynchronizationHistoryEventType,
        person_id: UUID,
        access_point_id: UUID,
    ) -> None:
        if self._synchronization_history_service is not None:
            await self._synchronization_history_service.record(
                event_type, person_id, access_point_id
            )

    async def _record_activity(
        self,
        event_type: ActivityEventType,
        *,
        operation_id: UUID,
        source_event_key: str,
        person: Person,
        access_point: AccessPoint,
        occurred_at: datetime | None = None,
        outcome: ActivityOutcome | None = None,
    ) -> None:
        if self._activity_producer is None:
            return
        await self._activity_producer.record(
            event_type,
            occurred_at=datetime.now(UTC) if occurred_at is None else occurred_at,
            source_event_key=source_event_key,
            person=person,
            access_point=access_point,
            correlation_id=operation_id,
            outcome=outcome,
        )

    async def _relationship_context(
        self, metadata: AccessMetadata
    ) -> tuple[Person, AccessPoint] | None:
        """Load safe historical names without affecting synchronization work."""
        try:
            return (
                await self._person_service.get_person(metadata.person_id),
                await self._access_point_service.get_access_point(metadata.access_point_id),
            )
        except Exception:  # noqa: BLE001 - missing presentation context cannot block work
            _LOGGER.error("Activity context was unavailable for a completed access operation")
            return None

    async def _record_removal_attention(self, operation_id: UUID, metadata: AccessMetadata) -> None:
        context = await self._relationship_context(metadata)
        if context is None:
            return
        person, access_point = context
        await self._record_activity(
            ActivityEventType.CREDENTIAL_VERIFICATION_FAILED,
            operation_id=operation_id,
            source_event_key=(
                f"access-removal:{metadata.person_id}:{metadata.access_point_id}:"
                f"{metadata.updated_at.isoformat()}:verification-failed"
            ),
            person=person,
            access_point=access_point,
            outcome=ActivityOutcome.FAILED,
        )

    async def _finalize_verified_removal(
        self, operation_id: UUID, metadata: AccessMetadata
    ) -> None:
        """Delete persisted records only after physical removal is verified."""
        if metadata.driver is AccessDriver.NUKI and self._access_removed_observer is not None:
            await self._run_removal_stage(
                operation_id,
                metadata,
                AccessUpdateStage.FINGERPRINT_LINK_DELETION,
                self._access_removed_observer(metadata.person_id, metadata.access_point_id),
            )
        await self._run_removal_stage(
            operation_id,
            metadata,
            AccessUpdateStage.ACCESS_GRANT_DELETION,
            self._metadata_service.remove_grant(metadata.person_id, metadata.access_point_id),
        )
        remaining = await self._run_removal_stage(
            operation_id,
            metadata,
            AccessUpdateStage.VAULT_REFERENCE_CHECK,
            self._metadata_service.list_all(),
        )
        credential_relationship = (
            None
            if self._credential_metadata_repository is None
            else await self._credential_metadata_repository.get_for_person(metadata.person_id)
        )
        if (
            metadata.vault_credential_id is not None
            and (
                credential_relationship is None
                or credential_relationship.credential_id != metadata.vault_credential_id
            )
            and not any(
                record.vault_credential_id == metadata.vault_credential_id
                and (
                    record.person_id != metadata.person_id
                    or record.access_point_id != metadata.access_point_id
                )
                for record in remaining
            )
        ):
            await self._run_removal_stage(
                operation_id,
                metadata,
                AccessUpdateStage.VAULT_CREDENTIAL_DELETION,
                self._credential_vault.delete(metadata.vault_credential_id),
            )
        await self._run_removal_stage(
            operation_id,
            metadata,
            AccessUpdateStage.SYNCHRONIZATION_METADATA_DELETION,
            self._metadata_service.remove_synchronization_metadata(
                metadata.person_id, metadata.access_point_id
            ),
        )
        persisted = await self._run_removal_stage(
            operation_id,
            metadata,
            AccessUpdateStage.FINAL_PERSISTENCE,
            self._metadata_service.list_for_person(metadata.person_id),
        )
        if any(record.access_point_id == metadata.access_point_id for record in persisted):
            raise self._stage_error(
                operation_id,
                metadata.person_id,
                metadata.access_point_id,
                AccessUpdateStage.FINAL_PERSISTENCE,
                exception_type="PersistenceVerificationError",
                sanitized_message="Removed access remains in persisted metadata",
            )

    async def _run_removal_stage[ResultT](
        self,
        operation_id: UUID,
        metadata: AccessMetadata,
        stage: AccessUpdateStage,
        operation: Awaitable[ResultT],
    ) -> ResultT:
        """Run and diagnose one non-secret asynchronous removal stage."""
        self._log_stage(
            operation_id,
            metadata.person_id,
            metadata.access_point_id,
            stage,
            synchronization_state=SynchronizationStatus.PENDING,
        )
        try:
            return await operation
        except Exception as err:
            raise self._stage_error(
                operation_id,
                metadata.person_id,
                metadata.access_point_id,
                stage,
                err,
                synchronization_state=SynchronizationStatus.MANUAL_ATTENTION_REQUIRED,
            ) from err

    async def _mark_verification_state(
        self,
        metadata: AccessMetadata,
        state: SynchronizationStatus,
    ) -> None:
        """Persist a terminal verification problem without raising from the task."""
        try:
            await self._metadata_service.update_synchronization_status(metadata, state)
        except Exception as err:
            self._log_failure(
                uuid4(),
                metadata.person_id,
                metadata.access_point_id,
                AccessUpdateStage.FINAL_PERSISTENCE,
                err,
                synchronization_state=state,
            )

    async def async_resume_pending_verifications(self) -> None:
        """Resume persisted pending verification work after a restart."""
        for metadata in await self._metadata_service.list_all():
            if metadata.synchronization_status is SynchronizationStatus.PENDING:
                self._schedule_verification(uuid4(), metadata)
            elif metadata.synchronization_status is SynchronizationStatus.SYNCHRONIZING:
                # A restart can occur between recording intent and receiving the
                # driver acknowledgement. Never infer acceptance or repeat the
                # physical operation in that ambiguous state.
                await self._mark_verification_state(
                    metadata, SynchronizationStatus.MANUAL_ATTENTION_REQUIRED
                )

    async def async_wait_for_verifications(self) -> None:
        """Wait for current verification tasks; intended for orderly tests and shutdown."""
        tasks = tuple(self._verification_tasks.values())
        if tasks:
            await asyncio.gather(*tasks)

    async def async_shutdown(self) -> None:
        """Cancel background verification tasks during integration unload."""
        tasks = tuple(self._verification_tasks.values())
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    def _stage_error(
        self,
        operation_id: UUID,
        person_id: UUID,
        access_point_id: UUID | None,
        stage: AccessUpdateStage,
        error: Exception | None = None,
        *,
        exception_type: str | None = None,
        sanitized_message: str = "Access update stage did not complete",
        synchronization_state: SynchronizationStatus | None = None,
        driver_result: object | None = None,
    ) -> AccessUpdateError:
        """Create and log one typed error using only approved diagnostic fields."""
        error_type = exception_type or (type(error).__name__ if error is not None else "Error")
        self._log_failure(
            operation_id,
            person_id,
            access_point_id,
            stage,
            error,
            exception_type=error_type,
            sanitized_message=sanitized_message,
            synchronization_state=synchronization_state,
            driver_result=driver_result,
        )
        return AccessUpdateError(
            operation_id=operation_id,
            person_id=person_id,
            access_point_id=access_point_id,
            stage=stage,
            exception_type=error_type,
            sanitized_message=sanitized_message,
        )

    @staticmethod
    def _log_stage(
        operation_id: UUID,
        person_id: UUID,
        access_point_id: UUID | None,
        stage: AccessUpdateStage,
        *,
        synchronization_state: SynchronizationStatus | None = None,
        driver_result: object | None = None,
    ) -> None:
        """Log approved non-secret stage fields."""
        _LOGGER.debug(
            "Access update operation_id=%s person_id=%s access_point_id=%s stage=%s "
            "synchronization_state=%s driver_result=%s",
            operation_id,
            person_id,
            access_point_id,
            stage.value,
            synchronization_state.value if synchronization_state is not None else None,
            driver_result,
        )

    @classmethod
    def _log_failure(
        cls,
        operation_id: UUID,
        person_id: UUID,
        access_point_id: UUID | None,
        stage: AccessUpdateStage,
        error: Exception | None,
        *,
        exception_type: str | None = None,
        sanitized_message: str = "Access update stage did not complete",
        synchronization_state: SynchronizationStatus | None = None,
        driver_result: object | None = None,
    ) -> None:
        """Log a failure without interpolating the underlying exception message."""
        error_type = exception_type or (type(error).__name__ if error is not None else "Error")
        _LOGGER.error(
            "Access update operation_id=%s person_id=%s access_point_id=%s stage=%s "
            "synchronization_state=%s driver_result=%s exception_type=%s exception=%s",
            operation_id,
            person_id,
            access_point_id,
            stage.value,
            synchronization_state.value if synchronization_state is not None else None,
            driver_result,
            error_type,
            sanitized_message,
        )
