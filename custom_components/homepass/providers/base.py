"""Vendor-neutral contracts for lock and access authorization providers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Protocol


class AuthorizationMutationState(StrEnum):
    """Truthful state of an asynchronous provider-side authorization change."""

    PENDING = "pending"
    CONFIRMED = "confirmed"
    FAILED = "failed"


class LockState(StrEnum):
    """Provider-neutral stable and transitional lock states."""

    LOCKED = "locked"
    LOCKING = "locking"
    UNLOCKED = "unlocked"
    UNLOCKING = "unlocking"
    OPEN = "open"
    UNKNOWN = "unknown"
    UNAVAILABLE = "unavailable"


class ProviderCommunicationError(Exception):
    """Raised for sanitized provider transport or response failures."""


@dataclass(frozen=True, slots=True)
class AccessProviderCapabilities:
    """Features supported by one physical access provider."""

    local_lock_control: bool
    keypad_codes: bool
    named_authorizations: bool
    schedules: bool
    audit_events: bool
    exact_pin_readback: bool = False


@dataclass(frozen=True, slots=True)
class AuthorizationSchedule:
    """Optional provider-neutral validity and weekly access restrictions."""

    valid_from: datetime | None = None
    valid_until: datetime | None = None
    weekdays: frozenset[int] = frozenset()
    from_minute: int | None = None
    until_minute: int | None = None

    def __post_init__(self) -> None:
        """Validate timestamps and recurring time boundaries."""
        valid_from = self._normalize(self.valid_from, "valid_from")
        valid_until = self._normalize(self.valid_until, "valid_until")
        if valid_from is not None and valid_until is not None and valid_until <= valid_from:
            raise ValueError("Authorization valid_until must be later than valid_from")
        if any(day < 1 or day > 7 for day in self.weekdays):
            raise ValueError("Authorization weekdays must use ISO weekday numbers 1 through 7")
        for field_name, value in (
            ("from_minute", self.from_minute),
            ("until_minute", self.until_minute),
        ):
            if value is not None and (
                isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 1439
            ):
                raise ValueError(f"Authorization {field_name} must be a minute from midnight")
        if (self.from_minute is None) is not (self.until_minute is None):
            raise ValueError(
                "Authorization recurring start and end times must be supplied together"
            )
        if self.from_minute is not None and not self.weekdays:
            raise ValueError("Authorization recurring times require at least one weekday")
        object.__setattr__(self, "valid_from", valid_from)
        object.__setattr__(self, "valid_until", valid_until)

    @staticmethod
    def _normalize(value: datetime | None, field_name: str) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(f"Authorization {field_name} must be timezone-aware")
        return value.astimezone(UTC)


@dataclass(frozen=True, slots=True, repr=False)
class AuthorizationRequest:
    """Transient authorization input; PIN material is never represented in logs."""

    display_name: str
    pin: str
    schedule: AuthorizationSchedule = AuthorizationSchedule()
    enabled: bool = True

    def __post_init__(self) -> None:
        display_name = self.display_name.strip()
        if not display_name:
            raise ValueError("Authorization display_name must not be empty")
        if not isinstance(self.pin, str) or not self.pin:
            raise ValueError("Authorization PIN must not be empty")
        object.__setattr__(self, "display_name", display_name)

    def __repr__(self) -> str:
        """Return operational context with the credential redacted."""
        return (
            f"{type(self).__name__}(display_name={self.display_name!r}, pin=<redacted>, "
            f"schedule={self.schedule!r}, enabled={self.enabled!r})"
        )


@dataclass(frozen=True, slots=True)
class AuthorizationRecord:
    """Non-secret authorization metadata returned by a provider."""

    external_id: str
    display_name: str
    enabled: bool
    schedule: AuthorizationSchedule = AuthorizationSchedule()


@dataclass(frozen=True, slots=True)
class AuthorizationMutation:
    """Secret-free result of requesting a provider authorization mutation."""

    state: AuthorizationMutationState
    external_id: str | None = None
    request_id: str | None = None
    error_summary: str | None = None


@dataclass(frozen=True, slots=True)
class ProviderAuditEvent:
    """Non-secret access event normalized at the provider boundary."""

    external_id: str
    occurred_at: datetime
    action: str
    outcome: str
    authorization_external_id: str | None = None
    authorization_name: str | None = None
    source: str | None = None


class LockControlProvider(Protocol):
    """Local lock-state and command boundary."""

    async def get_state(self, entity_id: str) -> LockState:
        """Return the current local lock state."""

    async def lock(self, entity_id: str, *, context: object | None = None) -> None:
        """Lock through the local provider."""

    async def open(self, entity_id: str, *, context: object | None = None) -> None:
        """Release the latch through an explicit Open command."""

    async def unlock(self, entity_id: str, *, context: object | None = None) -> None:
        """Unlock through the local provider."""


class AuthorizationProvider(Protocol):
    """Provider boundary for users, keypad credentials, schedules, and audit data."""

    @property
    def capabilities(self) -> AccessProviderCapabilities:
        """Return supported provider features."""

    async def create_authorization(self, request: AuthorizationRequest) -> AuthorizationMutation:
        """Request creation without claiming asynchronous completion."""

    async def update_authorization(
        self, external_id: str, request: AuthorizationRequest
    ) -> AuthorizationMutation:
        """Request an authorization update."""

    async def delete_authorization(self, external_id: str) -> AuthorizationMutation:
        """Request authorization deletion."""

    async def verify_authorization(
        self,
        request: AuthorizationRequest,
        *,
        external_id: str | None = None,
    ) -> AuthorizationMutation:
        """Read back a create or update request without exposing credential material."""

    async def verify_authorization_deleted(self, external_id: str) -> AuthorizationMutation:
        """Read back one requested deletion."""

    async def list_authorizations(self) -> tuple[AuthorizationRecord, ...]:
        """Return safe authorization metadata."""

    async def list_audit_events(self, *, limit: int = 50) -> tuple[ProviderAuditEvent, ...]:
        """Return recent provider audit events."""


class AuthorizationProviderRegistry:
    """Resolve configured authorization providers without vendor conditionals in services."""

    def __init__(self) -> None:
        self._providers: dict[str, AuthorizationProvider] = {}

    def register(self, provider_id: str, provider: AuthorizationProvider) -> None:
        """Register one provider exactly once."""
        normalized_id = provider_id.strip()
        if not normalized_id:
            raise ValueError("Authorization provider identifier must not be empty")
        if normalized_id in self._providers:
            raise ValueError(f"Authorization provider {normalized_id!r} is already registered")
        self._providers[normalized_id] = provider

    def get(self, provider_id: str) -> AuthorizationProvider | None:
        """Return one configured provider when present."""
        return self._providers.get(provider_id)

    def require(self, provider_id: str) -> AuthorizationProvider:
        """Return one configured provider or fail without selecting a fallback vendor."""
        provider = self.get(provider_id)
        if provider is None:
            raise ValueError(f"Authorization provider {provider_id!r} is not configured")
        return provider
