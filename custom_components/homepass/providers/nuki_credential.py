"""Numbered credential adapter bridging Nuki into existing HomePASS workflows."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from ..drivers import (
    CredentialRemovalRequest,
    CredentialRemovalRequestResult,
    CredentialRemovalRequestStatus,
    CredentialRemovalVerificationResult,
    CredentialRemovalVerificationStatus,
    CredentialReplacementRequest,
    CredentialReplacementRequestResult,
    CredentialReplacementRequestStatus,
    CredentialReplacementVerificationResult,
    CredentialReplacementVerificationStatus,
)
from ..services.zwave_sync import (
    CreatedZWaveCredential,
    DriverCommandResult,
    DriverCommandStatus,
    OperationDiagnostic,
    VerificationStatus,
    ZWaveDriverError,
    ZWaveUser,
)
from .base import (
    AuthorizationMutation,
    AuthorizationMutationState,
    AuthorizationRequest,
    AuthorizationSchedule,
)
from .nuki_pin import validate_nuki_keypad_pin

if TYPE_CHECKING:
    from .nuki import NukiAuthorizationProvider
    from .nuki_local import NukiLocalAuthorizationProvider


class NukiNumberedCredentialDriver:
    """Adapt Nuki authIds to HomePASS's durable positive credential slot field."""

    def __init__(
        self,
        provider: NukiAuthorizationProvider | NukiLocalAuthorizationProvider,
        lock_entity_id: str,
        *,
        verification_attempts: int = 5,
        verification_delay: float = 2.0,
    ) -> None:
        if not lock_entity_id.startswith("lock."):
            raise ValueError("Nuki credential target must be a lock entity")
        if verification_attempts < 1 or verification_delay < 0:
            raise ValueError("Nuki verification policy is invalid")
        self._provider = provider
        self._lock_entity_id = lock_entity_id
        self._verification_attempts = verification_attempts
        self._verification_delay = verification_delay

    def validate_pin(self, lock_entity_id: str, pin: str) -> None:
        """Validate one candidate before any Bluetooth or API mutation."""
        self._validate_target(lock_entity_id)
        validate_nuki_keypad_pin(pin)

    async def provision_pin(
        self,
        lock_entity_id: str,
        pin: str,
        *,
        display_name: str | None = None,
        schedule: AuthorizationSchedule | None = None,
        enabled: bool = True,
    ) -> CreatedZWaveCredential:
        """Create a Nuki keypad authorization and retain only its numeric authId."""
        self._validate_target(lock_entity_id)
        request = AuthorizationRequest(
            display_name=self._authorization_name(display_name),
            pin=pin,
            schedule=schedule or AuthorizationSchedule(),
            enabled=enabled,
        )
        try:
            mutation = await self._provider.create_authorization(request)
        except ValueError as err:
            raise self._validation_error("create", err) from None
        if mutation.state is AuthorizationMutationState.FAILED:
            raise self._error("create", mutation)
        mutation = await self._await_authorization(request, mutation)
        slot = self._slot(mutation.external_id)
        return CreatedZWaveCredential(
            credential_slot=slot,
            diagnostic=self._diagnostic("create"),
            verification_status=(
                "verified"
                if mutation.state is AuthorizationMutationState.CONFIRMED
                else "inconclusive"
            ),
        )

    async def verify_pin(
        self,
        lock_entity_id: str,
        slot: int,
        pin: str,
    ) -> VerificationStatus:
        """Verify one Nuki authId without exposing the observed code."""
        self._validate_target(lock_entity_id)
        mutation = await self._provider.verify_pin(str(slot), pin)
        if mutation.state is AuthorizationMutationState.CONFIRMED:
            return "verified"
        if (
            mutation.state is AuthorizationMutationState.PENDING
            or mutation.error_summary is not None
        ):
            return "inconclusive"
        return "failed"

    async def remove_pin(self, lock_entity_id: str, slot: int) -> bool:
        """Request and read back one Nuki authorization deletion."""
        command = await self.request_remove_pin(lock_entity_id, slot)
        if command.status is not DriverCommandStatus.ACCEPTED:
            return False
        for attempt in range(self._verification_attempts):
            removed = await self.verify_pin_removed(lock_entity_id, slot)
            if removed is not None:
                return removed
            if attempt + 1 < self._verification_attempts:
                await asyncio.sleep(self._verification_delay)
        return False

    async def request_remove_pin(self, lock_entity_id: str, slot: int) -> DriverCommandResult:
        """Issue one asynchronous Nuki authorization deletion."""
        self._validate_target(lock_entity_id)
        mutation = await self._provider.delete_authorization(str(slot))
        return DriverCommandResult(
            DriverCommandStatus.FAILED
            if mutation.state is AuthorizationMutationState.FAILED
            else DriverCommandStatus.ACCEPTED
        )

    async def verify_pin_removed(self, lock_entity_id: str, slot: int) -> bool | None:
        """Return confirmed deletion or an unconfirmed asynchronous state."""
        self._validate_target(lock_entity_id)
        mutation = await self._provider.verify_authorization_deleted(str(slot))
        if mutation.state is AuthorizationMutationState.CONFIRMED:
            return True
        return None

    async def list_users(self, lock_entity_id: str) -> tuple[ZWaveUser, ...]:
        """Return Nuki authorization metadata through the existing non-secret shape."""
        self._validate_target(lock_entity_id)
        records = await self._provider.list_authorizations()
        return tuple(
            ZWaveUser(user_id=self._slot(record.external_id), display_name=record.display_name)
            for record in records
        )

    def supports_pin_replacement(self, target_device: str) -> bool:
        return target_device == self._lock_entity_id

    def supports_exact_pin_readback(self, target_device: str) -> bool:
        return target_device == self._lock_entity_id

    async def async_request_credential_replacement(
        self,
        request: CredentialReplacementRequest,
    ) -> CredentialReplacementRequestResult:
        self._validate_target(request.target_device)
        record = await self._provider.get_authorization(str(request.slot))
        if record is None:
            return CredentialReplacementRequestResult(
                CredentialReplacementRequestStatus.REJECTED,
                "Nuki authorization was not found",
            )
        try:
            mutation = await self._provider.update_authorization(
                str(request.slot),
                AuthorizationRequest(
                    display_name=record.display_name,
                    pin=request.new_pin,
                    schedule=record.schedule,
                    enabled=record.enabled,
                ),
            )
        except ValueError as err:
            return CredentialReplacementRequestResult(
                CredentialReplacementRequestStatus.REJECTED,
                str(err),
            )
        return CredentialReplacementRequestResult(
            CredentialReplacementRequestStatus.ACCEPTED
            if mutation.state is not AuthorizationMutationState.FAILED
            else CredentialReplacementRequestStatus.REJECTED,
            mutation.error_summary,
        )

    async def async_verify_credential_replacement(
        self,
        request: CredentialReplacementRequest,
    ) -> CredentialReplacementVerificationResult:
        self._validate_target(request.target_device)
        mutation = await self._provider.verify_pin(str(request.slot), request.new_pin)
        if mutation.state is AuthorizationMutationState.CONFIRMED:
            status = CredentialReplacementVerificationStatus.REPLACEMENT_CONFIRMED
        elif mutation.state is AuthorizationMutationState.PENDING:
            status = CredentialReplacementVerificationStatus.REPLACEMENT_NOT_YET_CONFIRMED
        elif mutation.error_summary is not None:
            status = CredentialReplacementVerificationStatus.RETRYABLE_FAILURE
        else:
            status = (
                CredentialReplacementVerificationStatus.PREVIOUS_OR_DIFFERENT_CREDENTIAL_PRESENT
            )
        return CredentialReplacementVerificationResult(status, mutation.error_summary)

    async def async_request_credential_removal(
        self,
        request: CredentialRemovalRequest,
    ) -> CredentialRemovalRequestResult:
        command = await self.request_remove_pin(request.target_device, request.slot)
        return CredentialRemovalRequestResult(
            CredentialRemovalRequestStatus.ACCEPTED
            if command.status is DriverCommandStatus.ACCEPTED
            else CredentialRemovalRequestStatus.REJECTED
        )

    async def async_verify_credential_removed(
        self,
        request: CredentialRemovalRequest,
    ) -> CredentialRemovalVerificationResult:
        removed = await self.verify_pin_removed(request.target_device, request.slot)
        return CredentialRemovalVerificationResult(
            CredentialRemovalVerificationStatus.REMOVED
            if removed is True
            else CredentialRemovalVerificationStatus.STILL_PRESENT
            if removed is False
            else CredentialRemovalVerificationStatus.RETRYABLE_FAILURE
        )

    async def _await_authorization(
        self,
        request: AuthorizationRequest,
        mutation: AuthorizationMutation,
    ) -> AuthorizationMutation:
        latest = mutation
        for attempt in range(self._verification_attempts):
            verification = await self._provider.verify_authorization(
                request,
                external_id=latest.external_id,
            )
            if (
                verification.state is AuthorizationMutationState.FAILED
                and latest.external_id is not None
            ):
                return AuthorizationMutation(
                    AuthorizationMutationState.PENDING,
                    external_id=latest.external_id,
                    request_id=mutation.request_id,
                    error_summary=verification.error_summary,
                )
            latest = verification
            if latest.state is not AuthorizationMutationState.PENDING:
                return latest
            if latest.external_id is not None and attempt + 1 == self._verification_attempts:
                return latest
            if attempt + 1 < self._verification_attempts:
                await asyncio.sleep(self._verification_delay)
        if latest.external_id is None:
            raise self._error("verify_create", latest)
        return latest

    def _validate_target(self, lock_entity_id: str) -> None:
        if lock_entity_id != self._lock_entity_id:
            raise ValueError("Nuki credential target does not match the configured Matter lock")

    @staticmethod
    def _authorization_name(display_name: str | None) -> str:
        name = (display_name or "HomePASS PIN").strip()
        if len(name) <= 32:
            return name
        return f"{name[:29].rstrip()}..."

    @staticmethod
    def _slot(external_id: str | None) -> int:
        if external_id is None or not external_id.isdecimal() or int(external_id) < 1:
            raise ZWaveDriverError("Nuki did not return a durable numeric authorization ID")
        return int(external_id)

    @staticmethod
    def _diagnostic(stage: str) -> OperationDiagnostic:
        return {
            "stage": stage,
            "service": "nuki_authorization",
            "request": {},
            "response": None,
            "exception": None,
        }

    def _error(self, stage: str, mutation: AuthorizationMutation) -> ZWaveDriverError:
        diagnostic = self._diagnostic(stage)
        diagnostic["exception"] = mutation.error_summary or "Nuki authorization is unconfirmed"
        return ZWaveDriverError("Nuki authorization operation failed", diagnostic)

    def _validation_error(self, stage: str, error: ValueError) -> ZWaveDriverError:
        diagnostic = self._diagnostic(stage)
        diagnostic["exception"] = str(error)
        return ZWaveDriverError(str(error), diagnostic)
