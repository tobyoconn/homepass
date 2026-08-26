"""Driver contracts for physical access-control devices."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum


class DriverCapability(StrEnum):
    """Features a driver may support."""

    PIN = "pin"
    READ_SLOTS = "read_slots"
    CLEAR_SLOT = "clear_slot"
    REPLACE_PIN = "replace_pin"


class CredentialReplacementRequestStatus(StrEnum):
    """Sanitized outcome of one PIN replacement programming request."""

    ACCEPTED = "accepted"
    REJECTED = "rejected"
    AMBIGUOUS = "ambiguous"
    UNSUPPORTED = "unsupported"


class CredentialReplacementVerificationStatus(StrEnum):
    """Sanitized read-only PIN replacement verification outcomes."""

    REPLACEMENT_CONFIRMED = "replacement_confirmed"
    PREVIOUS_OR_DIFFERENT_CREDENTIAL_PRESENT = "previous_or_different_credential_present"
    REPLACEMENT_NOT_YET_CONFIRMED = "replacement_not_yet_confirmed"
    RETRYABLE_FAILURE = "retryable_failure"
    PERMANENT_FAILURE = "permanent_failure"
    UNSUPPORTED = "unsupported"


@dataclass(frozen=True, slots=True, repr=False)
class CredentialReplacementRequest:
    """Minimal transient context for replacing one numeric PIN."""

    target_device: str
    slot: int
    new_pin: str

    def __repr__(self) -> str:
        """Return safe operational context without the transient PIN."""
        return (
            f"{type(self).__name__}(target_device={self.target_device!r}, "
            f"slot={self.slot!r}, new_pin=<redacted>)"
        )


@dataclass(frozen=True, slots=True)
class CredentialReplacementRequestResult:
    """Secret-free result of submitting one replacement command."""

    status: CredentialReplacementRequestStatus
    error_summary: str | None = None


@dataclass(frozen=True, slots=True)
class CredentialReplacementVerificationResult:
    """Secret-free result of non-destructive replacement readback."""

    status: CredentialReplacementVerificationStatus
    error_summary: str | None = None


class CredentialRemovalStatus(StrEnum):
    """Standardized, exception-free credential removal outcomes."""

    SUCCESS = "success"
    RETRYABLE_FAILURE = "retryable_failure"
    PERMANENT_FAILURE = "permanent_failure"
    UNSUPPORTED = "unsupported"


class CredentialRemovalRequestStatus(StrEnum):
    """Sanitized outcome of requesting one destructive device command."""

    ACCEPTED = "accepted"
    REJECTED = "rejected"
    AMBIGUOUS = "ambiguous"


class CredentialRemovalVerificationStatus(StrEnum):
    """Sanitized read-only credential verification outcomes."""

    REMOVED = "removed"
    STILL_PRESENT = "still_present"
    RETRYABLE_FAILURE = "retryable_failure"
    PERMANENT_FAILURE = "permanent_failure"
    UNSUPPORTED = "unsupported"


@dataclass(frozen=True, slots=True)
class CredentialRemovalRequest:
    """Non-secret physical credential target."""

    target_device: str
    slot: int
    credential_identifier: str


@dataclass(frozen=True, slots=True)
class CredentialRemovalResult:
    """Sanitized result returned across the driver boundary."""

    status: CredentialRemovalStatus
    error_summary: str | None = None


@dataclass(frozen=True, slots=True)
class CredentialRemovalRequestResult:
    """Result of issuing one credential-removal command."""

    status: CredentialRemovalRequestStatus
    error_summary: str | None = None


@dataclass(frozen=True, slots=True)
class CredentialRemovalVerificationResult:
    """Result of read-only credential-removal verification."""

    status: CredentialRemovalVerificationStatus
    error_summary: str | None = None


@dataclass(frozen=True, slots=True)
class ProgramPinRequest:
    """A driver-neutral PIN programming request."""

    entity_id: str
    slot: int
    pin: str


class LockDriver(ABC):
    """Abstract driver boundary; no vendor logic may leak into core models."""

    @property
    @abstractmethod
    def capabilities(self) -> frozenset[DriverCapability]:
        """Return supported capabilities."""

    @abstractmethod
    async def async_program_pin(self, request: ProgramPinRequest) -> None:
        """Program one PIN atomically where supported."""

    @abstractmethod
    async def async_clear_slot(self, *, entity_id: str, slot: int) -> None:
        """Clear one credential slot."""

    def supports_pin_replacement(self, target_device: str) -> bool:
        """Return safe unsupported behavior for existing driver implementations."""
        return False

    def supports_exact_pin_readback(self, target_device: str) -> bool:
        """Return whether the target supports exact, non-destructive PIN readback."""
        return False

    async def async_request_credential_replacement(
        self,
        request: CredentialReplacementRequest,
    ) -> CredentialReplacementRequestResult:
        """Return unsupported without issuing a command by default."""
        return CredentialReplacementRequestResult(
            CredentialReplacementRequestStatus.UNSUPPORTED,
            "Credential replacement is not supported",
        )

    async def async_verify_credential_replacement(
        self,
        request: CredentialReplacementRequest,
    ) -> CredentialReplacementVerificationResult:
        """Return unsupported without reading or mutating by default."""
        return CredentialReplacementVerificationResult(
            CredentialReplacementVerificationStatus.UNSUPPORTED,
            "Credential replacement verification is not supported",
        )
