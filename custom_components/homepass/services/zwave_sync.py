"""Application service for the temporary Z-Wave synchronization spike."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Literal, Protocol, TypedDict

VerificationStatus = Literal["verified", "inconclusive", "failed"]


class DriverCommandStatus(StrEnum):
    """Immediate acknowledgement state for a physical driver command."""

    ACCEPTED = "accepted"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class DriverCommandResult:
    """PIN-safe immediate result of a physical driver command."""

    status: DriverCommandStatus


class ZWaveSyncError(Exception):
    """Base error for the temporary Z-Wave synchronization spike."""


class ZWaveSyncValidationError(ZWaveSyncError):
    """Raised when spike input is invalid."""


class OperationDiagnostic(TypedDict):
    """PIN-safe diagnostic data for one native Z-Wave action."""

    stage: str
    service: str
    request: dict[str, object]
    response: object | None
    exception: str | None


class ZWaveDriverError(ZWaveSyncError):
    """Raised when the Z-Wave driver cannot complete an operation."""

    def __init__(
        self,
        message: str,
        diagnostic: OperationDiagnostic | None = None,
    ) -> None:
        """Initialize an error with optional PIN-safe diagnostics."""
        super().__init__(message)
        self.diagnostic = diagnostic


class ZWaveInvalidTargetError(ZWaveDriverError):
    """Raised when a target is not an existing lock entity."""


@dataclass(frozen=True, slots=True)
class ZWaveUser:
    """Non-secret Z-Wave user metadata used for verification."""

    user_id: int
    display_name: str | None


@dataclass(frozen=True, slots=True)
class CreatedZWaveUser:
    """Allocated user metadata and its native action diagnostic."""

    user_id: int
    diagnostic: OperationDiagnostic


@dataclass(frozen=True, slots=True)
class CreatedZWaveCredential:
    """Allocated credential metadata and its native action diagnostic."""

    credential_slot: int | None
    diagnostic: OperationDiagnostic
    verification_status: VerificationStatus | None = None


class ZWaveLockSyncDriver(Protocol):
    """Driver boundary used by the synchronization spike."""

    async def create_user(self, lock_entity_id: str, display_name: str) -> CreatedZWaveUser:
        """Create a named active user and return its allocated identifier."""

    async def set_pin(
        self,
        lock_entity_id: str,
        user_id: int,
        pin: str,
    ) -> CreatedZWaveCredential:
        """Set a PIN and return its allocated credential slot when available."""

    async def list_users(self, lock_entity_id: str) -> tuple[ZWaveUser, ...]:
        """Return non-secret user metadata for a lock."""

    async def delete_user(self, lock_entity_id: str, user_id: int) -> bool:
        """Delete one user and return whether removal was confirmed."""


class PinSyncResponse(TypedDict):
    """Non-secret response returned by the synchronization spike."""

    lock_entity_id: str
    user_id: int | None
    credential_slot: int | None
    display_name: str
    verified: bool
    verification_status: VerificationStatus
    cleanup_attempted: bool
    cleanup_succeeded: bool | None
    error: str | None
    stage: str
    service: str
    request: dict[str, object]
    response: object | None
    exception: str | None
    diagnostics: list[OperationDiagnostic]


class DeleteUserResponse(TypedDict):
    """Non-secret response returned by the spike cleanup action."""

    lock_entity_id: str
    user_id: int
    deleted: bool


class ZWavePinSyncService:
    """Coordinate the temporary Z-Wave user and PIN synchronization spike."""

    def __init__(self, driver: ZWaveLockSyncDriver) -> None:
        """Initialize the service with its device boundary."""
        self._driver = driver

    async def sync_pin(
        self,
        lock_entity_id: str,
        display_name: str,
        pin: str,
    ) -> PinSyncResponse:
        """Create a Z-Wave user and ephemeral PIN, then verify the user."""
        lock_entity_id = self._validate_lock_entity_id(lock_entity_id)
        display_name = self._validate_display_name(display_name)
        self._validate_pin(pin)

        diagnostics: list[OperationDiagnostic] = []
        try:
            created_user = await self._driver.create_user(lock_entity_id, display_name)
        except ZWaveInvalidTargetError:
            raise
        except ZWaveDriverError as err:
            if err.diagnostic is not None:
                diagnostics.append(err.diagnostic)
            primary = self._primary_diagnostic("set_user", err.diagnostic)
            return PinSyncResponse(
                lock_entity_id=lock_entity_id,
                user_id=None,
                credential_slot=None,
                display_name=display_name,
                verified=False,
                verification_status="failed",
                cleanup_attempted=False,
                cleanup_succeeded=None,
                error="Z-Wave user creation failed.",
                **primary,
                diagnostics=diagnostics,
            )

        user_id = created_user.user_id
        diagnostics.append(created_user.diagnostic)

        try:
            created_credential = await self._driver.set_pin(
                lock_entity_id,
                user_id,
                pin,
            )
        except ZWaveDriverError as err:
            if err.diagnostic is not None:
                diagnostics.append(err.diagnostic)
            primary = self._primary_diagnostic("set_credential", err.diagnostic)
            cleanup_succeeded = await self._cleanup_user(lock_entity_id, user_id)
            return PinSyncResponse(
                lock_entity_id=lock_entity_id,
                user_id=user_id,
                credential_slot=None,
                display_name=display_name,
                verified=False,
                verification_status="failed",
                cleanup_attempted=True,
                cleanup_succeeded=cleanup_succeeded,
                error=(
                    "Credential creation failed; the new user was removed."
                    if cleanup_succeeded
                    else "Credential creation failed; the new user could not be removed."
                ),
                **primary,
                diagnostics=diagnostics,
            )

        credential_slot = created_credential.credential_slot
        diagnostics.append(created_credential.diagnostic)

        if created_credential.verification_status is not None:
            verified = created_credential.verification_status == "verified"
            return PinSyncResponse(
                lock_entity_id=lock_entity_id,
                user_id=user_id,
                credential_slot=credential_slot,
                display_name=display_name,
                verified=verified,
                verification_status=created_credential.verification_status,
                cleanup_attempted=False,
                cleanup_succeeded=None,
                error=(
                    None
                    if verified
                    else "The credential was written, but verification was inconclusive."
                ),
                **created_credential.diagnostic,
                diagnostics=diagnostics,
            )

        try:
            users = await self._driver.list_users(lock_entity_id)
        except ZWaveDriverError:
            return PinSyncResponse(
                lock_entity_id=lock_entity_id,
                user_id=user_id,
                credential_slot=credential_slot,
                display_name=display_name,
                verified=False,
                verification_status="inconclusive",
                cleanup_attempted=False,
                cleanup_succeeded=None,
                error="The credential was created, but the user could not be verified.",
                **created_credential.diagnostic,
                diagnostics=diagnostics,
            )

        verified = any(user.user_id == user_id for user in users)
        return PinSyncResponse(
            lock_entity_id=lock_entity_id,
            user_id=user_id,
            credential_slot=credential_slot,
            display_name=display_name,
            verified=verified,
            verification_status="verified" if verified else "inconclusive",
            cleanup_attempted=False,
            cleanup_succeeded=None,
            error=(
                None if verified else "The credential was created, but the user was not visible."
            ),
            **created_credential.diagnostic,
            diagnostics=diagnostics,
        )

    async def delete_user(
        self,
        lock_entity_id: str,
        user_id: int,
    ) -> DeleteUserResponse:
        """Delete exactly one requested Z-Wave user."""
        lock_entity_id = self._validate_lock_entity_id(lock_entity_id)
        if isinstance(user_id, bool) or not isinstance(user_id, int) or not 1 <= user_id <= 65535:
            raise ZWaveSyncValidationError("user_id must be an integer from 1 to 65535")
        deleted = await self._driver.delete_user(lock_entity_id, user_id)
        return DeleteUserResponse(
            lock_entity_id=lock_entity_id,
            user_id=user_id,
            deleted=deleted,
        )

    async def _cleanup_user(self, lock_entity_id: str, user_id: int) -> bool:
        """Best-effort removal of the user allocated by this invocation."""
        try:
            return await self._driver.delete_user(lock_entity_id, user_id)
        except ZWaveDriverError:
            return False

    @staticmethod
    def _primary_diagnostic(
        stage: str,
        diagnostic: OperationDiagnostic | None,
    ) -> OperationDiagnostic:
        """Return the failed operation diagnostic with a safe fallback."""
        if diagnostic is not None:
            return diagnostic
        return OperationDiagnostic(
            stage=stage,
            service=f"zwave_js.{stage}",
            request={},
            response=None,
            exception="ZWaveDriverError: action failed without diagnostic data",
        )

    @staticmethod
    def _validate_lock_entity_id(lock_entity_id: str) -> str:
        """Validate the lock entity identifier shape without Home Assistant imports."""
        if not isinstance(lock_entity_id, str) or not lock_entity_id.startswith("lock."):
            raise ZWaveSyncValidationError("lock_entity_id must be a lock entity ID")
        return lock_entity_id

    @staticmethod
    def _validate_display_name(display_name: str) -> str:
        """Validate and normalize the user display name."""
        if not isinstance(display_name, str) or not (display_name := display_name.strip()):
            raise ZWaveSyncValidationError("display_name must not be empty")
        return display_name

    @staticmethod
    def _validate_pin(pin: str) -> None:
        """Validate the ephemeral PIN without retaining or exposing it."""
        if (
            not isinstance(pin, str)
            or not pin.isascii()
            or not pin.isdigit()
            or not 4 <= len(pin) <= 8
        ):
            raise ZWaveSyncValidationError("pin must contain 4 to 8 ASCII digits")
