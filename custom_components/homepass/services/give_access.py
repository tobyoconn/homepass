"""Application service for PIN access provisioning and secure retention."""

from __future__ import annotations

import asyncio
import secrets
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Protocol
from uuid import UUID, uuid4

from ..exceptions import (
    CredentialAuthorityConflictError,
    DuplicateAccessError,
    ValidationError,
)
from ..models import (
    AccessDriver,
    AccessPoint,
    ActivityEventType,
    ActivityOutcome,
    Person,
    SynchronizationHistoryEventType,
)
from ..providers.schedule import authorization_schedule_from_homepass
from ..repositories import CredentialMetadataRepository
from ..vault import CredentialVaultProtocol, VaultCredentialId
from .access_metadata import AccessMetadataService
from .access_point import AccessPointService
from .activity_producer import ActivityProducer
from .person import PersonService
from .synchronization_history import SynchronizationHistoryService
from .zwave_sync import (
    CreatedZWaveCredential,
    DriverCommandResult,
    VerificationStatus,
    ZWaveDriverError,
)

if TYPE_CHECKING:
    from ..providers import AuthorizationSchedule
    from .schedule import ScheduleService


class NumberedUserCodeDriver(Protocol):
    """Driver boundary required by the temporary Give Access workflow."""

    def validate_pin(self, lock_entity_id: str, pin: str) -> None:
        """Validate a PIN for the adapter selected by the target lock."""

    async def provision_pin(
        self,
        lock_entity_id: str,
        pin: str,
        *,
        display_name: str | None = None,
        schedule: AuthorizationSchedule | None = None,
        enabled: bool = True,
    ) -> CreatedZWaveCredential:
        """Provision an ephemeral PIN into the first available numbered slot."""

    async def remove_pin(self, lock_entity_id: str, slot: int) -> bool:
        """Remove and verify one exact credential assignment."""

    async def request_remove_pin(self, lock_entity_id: str, slot: int) -> DriverCommandResult:
        """Issue one removal command without synchronous verification."""

    async def verify_pin_removed(self, lock_entity_id: str, slot: int) -> bool | None:
        """Return confirmed removal, confirmed occupancy, or unknown state."""

    async def verify_pin(
        self,
        lock_entity_id: str,
        slot: int,
        pin: str,
    ) -> VerificationStatus:
        """Compare one exact numbered slot with a transient candidate PIN."""


@dataclass(frozen=True, slots=True)
class GiveAccessDiagnostic:
    """PIN-safe development details for a failed driver operation."""

    stage: str
    service: str
    exception: str
    verification_status: VerificationStatus


@dataclass(frozen=True, slots=True)
class GiveAccessResult:
    """Non-secret result returned after attempting physical access provisioning."""

    status: VerificationStatus
    person_display_name: str
    access_point_display_name: str
    slot: int | None
    error: str | None = None
    diagnostic: GiveAccessDiagnostic | None = None


class GiveAccessService:
    """Coordinate person-centric PIN provisioning and vault persistence."""

    def __init__(
        self,
        person_service: PersonService,
        access_point_service: AccessPointService,
        driver: NumberedUserCodeDriver,
        access_metadata_service: AccessMetadataService,
        credential_vault: CredentialVaultProtocol,
        synchronization_history_service: SynchronizationHistoryService | None = None,
        activity_producer: ActivityProducer | None = None,
        credential_metadata_repository: CredentialMetadataRepository | None = None,
        schedule_service: ScheduleService | None = None,
    ) -> None:
        """Initialize the service with application and device boundaries."""
        self._person_service = person_service
        self._access_point_service = access_point_service
        self._driver = driver
        self._access_metadata_service = access_metadata_service
        self._credential_vault = credential_vault
        self._synchronization_history_service = synchronization_history_service
        self._activity_producer = activity_producer
        self._credential_metadata_repository = credential_metadata_repository
        self._schedule_service = schedule_service
        self._operation_lock = asyncio.Lock()

    async def give_access(
        self,
        person_id: UUID,
        access_point_id: UUID,
        pin: str,
    ) -> GiveAccessResult:
        """Provision and securely retain a PIN without returning it."""
        async with self._operation_lock:
            return await self._give_access(person_id, access_point_id, pin)

    async def _give_access(
        self,
        person_id: UUID,
        access_point_id: UUID,
        pin: str,
    ) -> GiveAccessResult:
        """Check access ownership before invoking the physical driver."""
        operation_id = uuid4()
        person = await self._person_service.get_person(person_id)
        target = await self._access_point_service.get_target(access_point_id)
        if not target.pin_capable:
            raise ValidationError(
                "This door supports HomePASS app control but does not expose PIN access"
            )
        if target.driver is None:
            raise ValidationError("PIN access driver is unavailable")
        if await self._access_metadata_service.has_access(person_id, access_point_id):
            raise DuplicateAccessError
        self._validate_pin(pin)
        if self._credential_metadata_repository is None:
            raise CredentialAuthorityConflictError()
        existing_credential = await self._credential_metadata_repository.resolve_for_provisioning(
            person_id
        )
        if existing_credential is not None:
            if not existing_credential.enabled:
                raise ValidationError("This User's PIN is disabled")
            stored_pin = await self._credential_vault.retrieve(existing_credential.credential_id)
            try:
                if not secrets.compare_digest(pin, stored_pin):
                    raise ValidationError(
                        "This User already has a different PIN. Use Change PIN first."
                    )
            finally:
                stored_pin = ""
        provider_schedule = None
        provider_enabled = person.enabled
        if target.driver is AccessDriver.NUKI and self._schedule_service is not None:
            schedule = await self._schedule_service.get_schedule(person.schedule_id)
            provider_schedule = authorization_schedule_from_homepass(schedule)
            provider_enabled = provider_enabled and schedule.enabled
        await self._record_history(
            SynchronizationHistoryEventType.PROVISIONING_STARTED,
            person_id,
            access_point_id,
        )
        try:
            credential = await self._driver.provision_pin(
                target.lock_entity_id,
                pin,
                display_name=person.display_name,
                schedule=provider_schedule,
                enabled=provider_enabled,
            )
        except ZWaveDriverError as err:
            await self._record_history(
                SynchronizationHistoryEventType.PROVISIONING_FAILED,
                person_id,
                access_point_id,
            )
            if self._activity_producer is not None:
                await self._activity_producer.record(
                    ActivityEventType.SYNCHRONIZATION_ATTENTION_REQUIRED,
                    occurred_at=datetime.now(UTC),
                    source_event_key=f"give-access:{operation_id}:synchronization-failed",
                    person=person,
                    access_point=target.access_point,
                    correlation_id=operation_id,
                    outcome=ActivityOutcome.FAILED,
                )
            return GiveAccessResult(
                status="failed",
                person_display_name=person.display_name,
                access_point_display_name=target.access_point.display_name,
                slot=None,
                error="HomePASS could not program the lock. Try again.",
                diagnostic=self._failure_diagnostic(err, pin),
            )

        status = credential.verification_status
        if status not in {"verified", "inconclusive"}:
            await self._record_history(
                SynchronizationHistoryEventType.PROVISIONING_FAILED,
                person_id,
                access_point_id,
            )
            await self._record_history(
                SynchronizationHistoryEventType.VERIFICATION_FAILED,
                person_id,
                access_point_id,
            )
            await self._record_verification_failure(operation_id, person, target.access_point)
            return GiveAccessResult(
                status="failed",
                person_display_name=person.display_name,
                access_point_display_name=target.access_point.display_name,
                slot=credential.credential_slot,
                error="HomePASS could not confirm that access was created.",
            )
        if credential.credential_slot is None:
            await self._record_history(
                SynchronizationHistoryEventType.PROVISIONING_FAILED,
                person_id,
                access_point_id,
            )
            await self._record_verification_failure(operation_id, person, target.access_point)
            return GiveAccessResult(
                status="failed",
                person_display_name=person.display_name,
                access_point_display_name=target.access_point.display_name,
                slot=None,
                error="HomePASS could not record the lock assignment.",
            )
        created_credential = existing_credential is None
        vault_credential_id = (
            await self._credential_vault.store(pin)
            if existing_credential is None
            else existing_credential.credential_id
        )
        try:
            credential_revision = await self._credential_vault.revision(vault_credential_id)
            saved = await self._access_metadata_service.record_provisioning(
                person_id,
                access_point_id,
                target.lock_entity_id,
                credential.credential_slot,
                status,
                vault_credential_id,
                target.driver,
                credential_revision=credential_revision,
            )
        except Exception:
            removed = False
            with suppress(Exception):
                removed = await self._driver.remove_pin(
                    target.lock_entity_id,
                    credential.credential_slot,
                )
            if created_credential and removed:
                await self._delete_created_credential_if_safe(
                    person_id,
                    vault_credential_id,
                )
            raise
        if self._activity_producer is not None:
            await self._activity_producer.record(
                ActivityEventType.ACCESS_GRANTED,
                occurred_at=saved.updated_at,
                source_event_key=f"give-access:{operation_id}:access-granted",
                person=person,
                access_point=target.access_point,
                correlation_id=operation_id,
                outcome=ActivityOutcome.SUCCEEDED,
            )
            if status == "verified":
                await self._activity_producer.record(
                    ActivityEventType.CREDENTIAL_ADDED,
                    occurred_at=saved.updated_at,
                    source_event_key=f"give-access:{operation_id}:credential-added",
                    person=person,
                    access_point=target.access_point,
                    correlation_id=operation_id,
                    outcome=ActivityOutcome.SUCCEEDED,
                )
        return GiveAccessResult(
            status=status,
            person_display_name=person.display_name,
            access_point_display_name=target.access_point.display_name,
            slot=credential.credential_slot,
        )

    async def _delete_created_credential_if_safe(
        self,
        person_id: UUID,
        credential_id: VaultCredentialId,
    ) -> None:
        """Delete a new Vault secret only after every persisted reference is gone."""
        try:
            released = await self._access_metadata_service.release_orphaned_person_credential(
                person_id,
                credential_id,
            )
        except Exception:  # noqa: BLE001 - uncertainty must retain the recoverable secret
            return
        if released:
            with suppress(Exception):
                await self._credential_vault.delete(credential_id)

    async def _record_verification_failure(
        self, operation_id: UUID, person: Person, access_point: AccessPoint
    ) -> None:
        """Record a safe verification failure without carrying driver details."""
        if self._activity_producer is None:
            return
        await self._activity_producer.record(
            ActivityEventType.CREDENTIAL_VERIFICATION_FAILED,
            occurred_at=datetime.now(UTC),
            source_event_key=f"give-access:{operation_id}:credential-unverified",
            person=person,
            access_point=access_point,
            correlation_id=operation_id,
            outcome=ActivityOutcome.FAILED,
        )

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

    @staticmethod
    def _failure_diagnostic(error: ZWaveDriverError, pin: str) -> GiveAccessDiagnostic:
        """Extract only PIN-safe fields from a driver failure."""
        diagnostic = error.diagnostic
        exception = (
            diagnostic["exception"]
            if diagnostic is not None and diagnostic["exception"] is not None
            else f"{type(error).__name__}: {error}"
        )
        return GiveAccessDiagnostic(
            stage=(
                diagnostic["stage"].replace(pin, "<redacted>")
                if diagnostic is not None
                else "provision_pin"
            ),
            service=(
                diagnostic["service"].replace(pin, "<redacted>")
                if diagnostic is not None
                else "zwave_js"
            ),
            exception=exception.replace(pin, "<redacted>"),
            verification_status="failed",
        )

    @staticmethod
    def _validate_pin(pin: str) -> None:
        """Require four to ten ASCII digits without exposing the value."""
        if (
            not isinstance(pin, str)
            or not 4 <= len(pin) <= 10
            or not pin.isascii()
            or not pin.isdigit()
        ):
            raise ValueError("PIN must contain 4 to 10 ASCII digits")
