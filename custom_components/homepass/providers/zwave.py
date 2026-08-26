"""Adapter preserving existing Yale/Z-Wave numbered-code behavior."""

from __future__ import annotations

from typing import Protocol

from ..drivers.base import (
    CredentialReplacementRequest,
    CredentialReplacementRequestStatus,
    CredentialReplacementVerificationStatus,
)
from ..services.zwave_sync import DriverCommandStatus, VerificationStatus, ZWaveUser
from .base import (
    AccessProviderCapabilities,
    AuthorizationMutation,
    AuthorizationMutationState,
    AuthorizationProvider,
    AuthorizationRecord,
    AuthorizationRequest,
    ProviderAuditEvent,
    ProviderCommunicationError,
)


class ZWaveNumberedCodeDriver(Protocol):
    """Existing Yale/Z-Wave operations consumed by the provider adapter."""

    async def provision_pin(self, lock_entity_id: str, pin: str) -> object: ...

    async def request_remove_pin(self, lock_entity_id: str, slot: int) -> object: ...

    async def verify_pin_removed(self, lock_entity_id: str, slot: int) -> bool | None: ...

    async def verify_pin(self, lock_entity_id: str, slot: int, pin: str) -> VerificationStatus: ...

    async def list_users(self, lock_entity_id: str) -> tuple[ZWaveUser, ...]: ...

    def supports_pin_replacement(self, target_device: str) -> bool: ...

    async def async_request_credential_replacement(
        self, request: CredentialReplacementRequest
    ) -> object: ...

    async def async_verify_credential_replacement(
        self, request: CredentialReplacementRequest
    ) -> object: ...


class ZWaveAuthorizationProvider(AuthorizationProvider):
    """Expose the current Yale implementation through the common provider contract."""

    def __init__(self, driver: ZWaveNumberedCodeDriver, lock_entity_id: str) -> None:
        if not lock_entity_id.startswith("lock."):
            raise ValueError("Z-Wave provider target must be a lock entity")
        self._driver = driver
        self._lock_entity_id = lock_entity_id

    @property
    def capabilities(self) -> AccessProviderCapabilities:
        return AccessProviderCapabilities(
            local_lock_control=True,
            keypad_codes=True,
            named_authorizations=False,
            schedules=False,
            audit_events=False,
            exact_pin_readback=True,
        )

    async def create_authorization(self, request: AuthorizationRequest) -> AuthorizationMutation:
        self._validate_request(request)
        try:
            created = await self._driver.provision_pin(self._lock_entity_id, request.pin)
            slot = getattr(created, "credential_slot", None)
            verification = getattr(created, "verification_status", None)
        except Exception as err:
            return self._failed(err)
        if not isinstance(slot, int):
            return AuthorizationMutation(
                AuthorizationMutationState.FAILED,
                error_summary="Z-Wave provider did not allocate a credential slot",
            )
        return AuthorizationMutation(
            self._verification_state(verification),
            external_id=str(slot),
        )

    async def update_authorization(
        self, external_id: str, request: AuthorizationRequest
    ) -> AuthorizationMutation:
        self._validate_request(request)
        slot = self._slot(external_id)
        if not self._driver.supports_pin_replacement(self._lock_entity_id):
            return AuthorizationMutation(
                AuthorizationMutationState.FAILED,
                external_id=external_id,
                error_summary="Z-Wave credential replacement is not supported",
            )
        replacement = CredentialReplacementRequest(
            target_device=self._lock_entity_id,
            slot=slot,
            new_pin=request.pin,
        )
        try:
            result = await self._driver.async_request_credential_replacement(replacement)
        except Exception as err:
            return self._failed(err, external_id=external_id)
        status = getattr(result, "status", None)
        if status is CredentialReplacementRequestStatus.ACCEPTED:
            return AuthorizationMutation(
                AuthorizationMutationState.PENDING,
                external_id=external_id,
            )
        return AuthorizationMutation(
            AuthorizationMutationState.FAILED,
            external_id=external_id,
            error_summary=getattr(result, "error_summary", None)
            or "Z-Wave credential replacement was not accepted",
        )

    async def delete_authorization(self, external_id: str) -> AuthorizationMutation:
        slot = self._slot(external_id)
        try:
            result = await self._driver.request_remove_pin(self._lock_entity_id, slot)
        except Exception as err:
            return self._failed(err, external_id=external_id)
        if getattr(result, "status", None) is DriverCommandStatus.ACCEPTED:
            return AuthorizationMutation(
                AuthorizationMutationState.PENDING,
                external_id=external_id,
            )
        return AuthorizationMutation(
            AuthorizationMutationState.FAILED,
            external_id=external_id,
            error_summary="Z-Wave credential removal was not accepted",
        )

    async def verify_authorization(
        self,
        request: AuthorizationRequest,
        *,
        external_id: str | None = None,
    ) -> AuthorizationMutation:
        self._validate_request(request)
        if external_id is None:
            return AuthorizationMutation(
                AuthorizationMutationState.FAILED,
                error_summary="Z-Wave verification requires a credential slot",
            )
        slot = self._slot(external_id)
        try:
            if self._driver.supports_pin_replacement(self._lock_entity_id):
                result = await self._driver.async_verify_credential_replacement(
                    CredentialReplacementRequest(
                        target_device=self._lock_entity_id,
                        slot=slot,
                        new_pin=request.pin,
                    )
                )
                status = getattr(result, "status", None)
                if status is CredentialReplacementVerificationStatus.REPLACEMENT_CONFIRMED:
                    state = AuthorizationMutationState.CONFIRMED
                elif status in {
                    CredentialReplacementVerificationStatus.RETRYABLE_FAILURE,
                    CredentialReplacementVerificationStatus.REPLACEMENT_NOT_YET_CONFIRMED,
                }:
                    state = AuthorizationMutationState.PENDING
                else:
                    state = AuthorizationMutationState.FAILED
            else:
                state = self._verification_state(
                    await self._driver.verify_pin(self._lock_entity_id, slot, request.pin)
                )
        except Exception as err:
            return self._failed(err, external_id=external_id)
        return AuthorizationMutation(state, external_id=external_id)

    async def verify_authorization_deleted(self, external_id: str) -> AuthorizationMutation:
        slot = self._slot(external_id)
        try:
            removed = await self._driver.verify_pin_removed(self._lock_entity_id, slot)
        except Exception as err:
            return self._failed(err, external_id=external_id)
        return AuthorizationMutation(
            AuthorizationMutationState.CONFIRMED
            if removed is True
            else AuthorizationMutationState.FAILED
            if removed is False
            else AuthorizationMutationState.PENDING,
            external_id=external_id,
        )

    async def list_authorizations(self) -> tuple[AuthorizationRecord, ...]:
        try:
            users = await self._driver.list_users(self._lock_entity_id)
        except Exception as err:
            raise ProviderCommunicationError("Z-Wave authorization listing failed") from err
        return tuple(
            AuthorizationRecord(
                external_id=str(user.user_id),
                display_name=user.display_name or f"Slot {user.user_id}",
                enabled=True,
            )
            for user in users
        )

    async def list_audit_events(self, *, limit: int = 50) -> tuple[ProviderAuditEvent, ...]:
        if isinstance(limit, bool) or limit < 1:
            raise ValueError("Audit event limit must be positive")
        return ()

    @staticmethod
    def _validate_request(request: AuthorizationRequest) -> None:
        if request.schedule != type(request.schedule)():
            raise ValueError("The Yale/Z-Wave provider does not support authorization schedules")
        if not request.pin.isdecimal() or not 4 <= len(request.pin) <= 10:
            raise ValueError("The Yale/Z-Wave PIN must contain 4 through 10 digits")

    @staticmethod
    def _slot(external_id: str) -> int:
        try:
            slot = int(external_id)
        except (TypeError, ValueError) as err:
            raise ValueError("Z-Wave authorization identifier must be a numbered slot") from err
        if slot < 1:
            raise ValueError("Z-Wave authorization identifier must be a positive slot")
        return slot

    @staticmethod
    def _verification_state(status: object) -> AuthorizationMutationState:
        if status == "verified":
            return AuthorizationMutationState.CONFIRMED
        if status == "inconclusive":
            return AuthorizationMutationState.PENDING
        return AuthorizationMutationState.FAILED

    @staticmethod
    def _failed(error: Exception, *, external_id: str | None = None) -> AuthorizationMutation:
        return AuthorizationMutation(
            AuthorizationMutationState.FAILED,
            external_id=external_id,
            error_summary=f"Z-Wave provider operation failed ({type(error).__name__})",
        )
