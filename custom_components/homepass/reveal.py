"""Secure credential Reveal application boundary.

This module handles only non-secret identifiers, transient plaintext retrieval, process-local
rate limits, and non-secret audit records. It never logs or persists credential material.
"""

from __future__ import annotations

import asyncio
from collections import defaultdict, deque
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from math import ceil
from time import monotonic
from typing import TypedDict
from uuid import UUID, uuid4

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .exceptions import (
    CredentialAuthorityConflictError,
    PersonNotFoundError,
    StorageError,
)
from .repositories import CredentialMetadataRepository
from .services import AccessMetadataService, PersonService
from .vault import (
    CredentialVaultProtocol,
    VaultCredentialNotFoundError,
    VaultError,
    VaultNotInitializedError,
    VaultUnavailableError,
)

REVEAL_AUDIT_STORAGE_KEY = "homepass.reveal_audit"
REVEAL_AUDIT_STORAGE_VERSION = 1
REVEAL_AUDIT_SCHEMA_VERSION = 1
REVEAL_AUDIT_RETENTION = timedelta(days=365)
REVEAL_AUDIT_MAX_EVENTS = 10_000

RevealTraceCallback = Callable[[str], None]


def _trace_stage(trace: RevealTraceCallback | None, stage: str) -> None:
    """Record one secret-free diagnostic stage when tracing is active."""
    if trace is not None:
        try:
            trace(stage)
        except Exception:
            return


def _best_effort_trace(trace: RevealTraceCallback | None) -> RevealTraceCallback | None:
    """Wrap diagnostics so they can never affect a Reveal operation."""
    if trace is None:
        return None

    def safe_trace(stage: str) -> None:
        _trace_stage(trace, stage)

    return safe_trace


class RevealOutcome(StrEnum):
    """Approved non-secret Reveal audit outcomes."""

    REVEALED = "revealed"
    DENIED = "denied"
    RATE_LIMITED = "rate_limited"
    CREDENTIAL_MISSING = "credential_missing"
    VAULT_UNAVAILABLE = "vault_unavailable"
    FAILED = "failed"


class RevealReason(StrEnum):
    """Sanitized Reveal reason codes."""

    SUCCESS = "success"
    ADMIN_REQUIRED = "admin_required"
    CREDENTIAL_RATE_LIMIT = "credential_rate_limit"
    ADMINISTRATOR_RATE_LIMIT = "administrator_rate_limit"
    CREDENTIAL_MISSING = "credential_missing"
    VAULT_UNAVAILABLE = "vault_unavailable"
    RETRIEVAL_FAILED = "retrieval_failed"


class RevealError(Exception):
    """Base class for fixed-message Reveal errors."""

    message = "Reveal failed"

    def __init__(self) -> None:
        """Initialize without caller-provided or secret-bearing text."""
        super().__init__(self.message)


class RevealCredentialUnavailableError(RevealError):
    """Raised when no retrievable credential belongs to the assignment."""

    message = "Credential unavailable"


class RevealVaultUnavailableError(RevealError):
    """Raised when secure credential storage is unavailable."""

    message = "Vault unavailable"


class RevealAuditError(RevealError):
    """Raised when the mandatory audit write cannot be committed."""


class RevealRateLimitedError(RevealError):
    """Raised with safe retry timing after an approved limit is reached."""

    message = "Too many requests"

    def __init__(self, retry_after: int) -> None:
        """Store only non-secret retry timing."""
        self.retry_after = max(1, retry_after)
        super().__init__()

    def __repr__(self) -> str:
        """Return only the fixed category and safe retry timing."""
        return f"{type(self).__name__}(retry_after={self.retry_after})"


class RevealAuditEventData(TypedDict):
    """Serialized non-secret Reveal audit event."""

    event_id: str
    timestamp: str
    ha_user_id: str
    person_id: str
    access_point_id: str | None
    outcome: str
    reason_code: str


class RevealAuditStorageData(TypedDict):
    """Versioned Reveal audit storage record."""

    schema_version: int
    events: list[RevealAuditEventData]


@dataclass(frozen=True, slots=True)
class RevealAuditEvent:
    """One immutable, non-secret Reveal audit event."""

    event_id: UUID
    timestamp: datetime
    ha_user_id: str
    person_id: UUID
    access_point_id: UUID | None
    outcome: RevealOutcome
    reason_code: RevealReason

    def __post_init__(self) -> None:
        """Validate fields and normalize the occurrence time to UTC."""
        if not isinstance(self.event_id, UUID):
            raise TypeError("Reveal audit event_id must be a UUID")
        if not isinstance(self.timestamp, datetime):
            raise TypeError("Reveal audit timestamp must be a datetime")
        if self.timestamp.tzinfo is None or self.timestamp.utcoffset() is None:
            raise ValueError("Reveal audit timestamp must be timezone-aware")
        if not isinstance(self.ha_user_id, str) or not self.ha_user_id.strip():
            raise ValueError("Reveal audit HA user ID must not be empty")
        if not isinstance(self.person_id, UUID):
            raise TypeError("Reveal audit Person identifier must be a UUID")
        if self.access_point_id is not None and not isinstance(self.access_point_id, UUID):
            raise TypeError("Reveal audit Access Point identifier must be a UUID or None")
        if not isinstance(self.outcome, RevealOutcome):
            raise TypeError("Reveal audit outcome must be a RevealOutcome")
        if not isinstance(self.reason_code, RevealReason):
            raise TypeError("Reveal audit reason_code must be a RevealReason")
        object.__setattr__(self, "timestamp", self.timestamp.astimezone(UTC))
        object.__setattr__(self, "ha_user_id", self.ha_user_id.strip())

    def to_dict(self) -> RevealAuditEventData:
        """Serialize only approved non-secret fields."""
        return {
            "event_id": str(self.event_id),
            "timestamp": self.timestamp.isoformat(),
            "ha_user_id": self.ha_user_id,
            "person_id": str(self.person_id),
            "access_point_id": (
                None if self.access_point_id is None else str(self.access_point_id)
            ),
            "outcome": self.outcome.value,
            "reason_code": self.reason_code.value,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> RevealAuditEvent:
        """Deserialize and strictly validate one audit event."""
        expected = {
            "event_id",
            "timestamp",
            "ha_user_id",
            "person_id",
            "access_point_id",
            "outcome",
            "reason_code",
        }
        string_fields = expected - {"access_point_id"}
        if (
            set(data) != expected
            or not all(isinstance(data[key], str) for key in string_fields)
            or (
                data["access_point_id"] is not None and not isinstance(data["access_point_id"], str)
            )
        ):
            raise RevealAuditError
        try:
            return cls(
                event_id=UUID(str(data["event_id"])),
                timestamp=datetime.fromisoformat(str(data["timestamp"])),
                ha_user_id=str(data["ha_user_id"]),
                person_id=UUID(str(data["person_id"])),
                access_point_id=(
                    None if data["access_point_id"] is None else UUID(str(data["access_point_id"]))
                ),
                outcome=RevealOutcome(str(data["outcome"])),
                reason_code=RevealReason(str(data["reason_code"])),
            )
        except (TypeError, ValueError) as err:
            raise RevealAuditError from err


class RevealAuditRepository:
    """Atomically persist the bounded private Reveal audit record."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the private storage adapter."""
        self._store = Store[RevealAuditStorageData](
            hass,
            REVEAL_AUDIT_STORAGE_VERSION,
            REVEAL_AUDIT_STORAGE_KEY,
            atomic_writes=True,
        )
        self._lock = asyncio.Lock()
        self._events: list[RevealAuditEvent] | None = None

    async def async_initialize(self) -> None:
        """Warm the validated audit snapshot outside the Reveal request path."""
        async with self._lock:
            await self._load_unlocked()

    async def append(
        self,
        event: RevealAuditEvent,
        *,
        trace: RevealTraceCallback | None = None,
    ) -> None:
        """Persist one event after applying approved retention limits."""
        if not isinstance(event, RevealAuditEvent):
            raise TypeError("event must be a RevealAuditEvent")
        async with self._lock:
            _trace_stage(trace, "reveal_audit_lock_acquired")
            events = await self._load_unlocked()
            cutoff = event.timestamp - REVEAL_AUDIT_RETENTION
            events = [existing for existing in events if existing.timestamp >= cutoff]
            events.append(event)
            events = sorted(events, key=lambda item: item.timestamp)[-REVEAL_AUDIT_MAX_EVENTS:]
            data: RevealAuditStorageData = {
                "schema_version": REVEAL_AUDIT_SCHEMA_VERSION,
                "events": [existing.to_dict() for existing in events],
            }
            try:
                _trace_stage(trace, "reveal_audit_write_started")
                await self._store.async_save(data)
            except Exception as err:
                raise RevealAuditError from err
            _trace_stage(trace, "reveal_audit_store_save_returned")
            self._events = events.copy()
            _trace_stage(trace, "reveal_audit_append_completed")

    async def _load_unlocked(self) -> list[RevealAuditEvent]:
        """Load and validate the private record while locked."""
        if self._events is not None:
            return self._events.copy()
        try:
            data = await self._store.async_load()
        except Exception as err:
            raise RevealAuditError from err
        if data is None:
            self._events = []
            return []
        if (
            not isinstance(data, Mapping)
            or set(data) != {"schema_version", "events"}
            or data.get("schema_version") != REVEAL_AUDIT_SCHEMA_VERSION
            or not isinstance(data.get("events"), list)
        ):
            raise RevealAuditError
        if not all(isinstance(event, Mapping) for event in data["events"]):
            raise RevealAuditError
        try:
            events = [RevealAuditEvent.from_dict(event) for event in data["events"]]
            self._events = events.copy()
            return events
        except (TypeError, ValueError) as err:
            raise RevealAuditError from err


class RevealRateLimiter:
    """Enforce integration-wide process-memory Reveal limits."""

    def __init__(self, clock: Callable[[], float] = monotonic) -> None:
        """Initialize empty counters that intentionally reset on restart."""
        self._clock = clock
        self._credential_attempts: dict[tuple[UUID, UUID | None], deque[float]] = defaultdict(deque)
        self._administrator_attempts: dict[str, deque[float]] = defaultdict(deque)

    def check_and_record(
        self,
        ha_user_id: str,
        person_id: UUID,
        access_point_id: UUID | None,
    ) -> RevealReason | None:
        """Record one attempt and return the exceeded limit, if any."""
        now = self._clock()
        credential = self._credential_attempts[(person_id, access_point_id)]
        administrator = self._administrator_attempts[ha_user_id]
        self._prune(credential, now - 60)
        self._prune(administrator, now - 600)
        if len(credential) >= 3:
            return RevealReason.CREDENTIAL_RATE_LIMIT
        if len(administrator) >= 10:
            return RevealReason.ADMINISTRATOR_RATE_LIMIT
        credential.append(now)
        administrator.append(now)
        return None

    def record_denied(self, person_id: UUID, access_point_id: UUID | None) -> None:
        """Count an identifiable denied request toward its credential-scoped limit."""
        now = self._clock()
        credential = self._credential_attempts[(person_id, access_point_id)]
        self._prune(credential, now - 60)
        credential.append(now)

    def reset_credential(
        self,
        person_id: UUID,
        access_point_id: UUID | None,
    ) -> None:
        """Forget attempts for one credential reveal authority."""
        if not isinstance(person_id, UUID) or (
            access_point_id is not None and not isinstance(access_point_id, UUID)
        ):
            raise TypeError("Reveal credential reset identifiers must be UUIDs")
        self._credential_attempts.pop((person_id, access_point_id), None)

    def retry_after(
        self,
        reason: RevealReason,
        ha_user_id: str,
        person_id: UUID,
        access_point_id: UUID | None,
    ) -> int:
        """Return safe seconds until the selected limit permits another attempt."""
        now = self._clock()
        if reason is RevealReason.CREDENTIAL_RATE_LIMIT:
            attempts = self._credential_attempts[(person_id, access_point_id)]
            limit = 3
            window = 60
        else:
            attempts = self._administrator_attempts[ha_user_id]
            limit = 10
            window = 600
        blocking = attempts[len(attempts) - limit]
        return max(1, ceil(blocking + window - now))

    @staticmethod
    def _prune(attempts: deque[float], cutoff: float) -> None:
        """Remove attempts outside one rolling window."""
        while attempts and attempts[0] <= cutoff:
            attempts.popleft()


class CredentialRevealService:
    """Authorize a target relationship, retrieve its PIN, and audit before return."""

    def __init__(
        self,
        person_service: PersonService,
        metadata_service: AccessMetadataService,
        credential_vault: CredentialVaultProtocol,
        audit_repository: RevealAuditRepository,
        rate_limiter: RevealRateLimiter | None = None,
        credential_metadata_repository: CredentialMetadataRepository | None = None,
    ) -> None:
        """Initialize Reveal dependencies."""
        self._person_service = person_service
        self._metadata_service = metadata_service
        self._credential_vault = credential_vault
        self._audit_repository = audit_repository
        self._rate_limiter = rate_limiter or RevealRateLimiter()
        self._credential_metadata_repository = credential_metadata_repository

    def reset_rate_limit_after_replacement(
        self,
        person_id: UUID,
        access_point_id: UUID | None,
    ) -> None:
        """Reset only the prior authority's bucket after finalized replacement.

        The administrator limit and durable Reveal audit are intentionally unaffected.
        """
        self._rate_limiter.reset_credential(person_id, access_point_id)

    async def reveal(
        self,
        ha_user_id: str,
        person_id: UUID,
        access_point_id: UUID | None,
        *,
        trace: RevealTraceCallback | None = None,
    ) -> str:
        """Return plaintext only after rate checks, retrieval, and durable success audit."""
        trace = _best_effort_trace(trace)
        limited = self._rate_limiter.check_and_record(
            ha_user_id,
            person_id,
            access_point_id,
        )
        _trace_stage(trace, "reveal_rate_limit_check_completed")
        if limited is not None:
            await self._audit(
                ha_user_id,
                person_id,
                access_point_id,
                RevealOutcome.RATE_LIMITED,
                limited,
                trace=trace,
            )
            raise RevealRateLimitedError(
                self._rate_limiter.retry_after(
                    limited,
                    ha_user_id,
                    person_id,
                    access_point_id,
                )
            )
        try:
            _trace_stage(trace, "person_lookup_started")
            await self._person_service.get_person(person_id)
            _trace_stage(trace, "person_lookup_completed")
        except PersonNotFoundError:
            await self._audit_missing(
                ha_user_id,
                person_id,
                access_point_id,
                trace=trace,
            )
            raise RevealCredentialUnavailableError from None
        except Exception:
            await self._audit_failed(
                ha_user_id,
                person_id,
                access_point_id,
                trace=trace,
            )
            raise RevealError from None
        try:
            credential_id = None
            if access_point_id is None and self._credential_metadata_repository is not None:
                _trace_stage(trace, "credential_metadata_lookup_started")
                credential = await self._credential_metadata_repository.resolve_for_provisioning(
                    person_id
                )
                credential_id = None if credential is None else credential.credential_id
                _trace_stage(trace, "credential_metadata_lookup_completed")
            else:
                _trace_stage(trace, "access_metadata_lookup_started")
                metadata = next(
                    (
                        record
                        for record in await self._metadata_service.list_for_person(person_id)
                        if record.access_point_id == access_point_id
                    ),
                    None,
                )
                credential_id = None if metadata is None else metadata.vault_credential_id
                _trace_stage(trace, "access_metadata_lookup_completed")
        except (CredentialAuthorityConflictError, StorageError):
            await self._audit_failed(
                ha_user_id,
                person_id,
                access_point_id,
                trace=trace,
            )
            raise RevealError from None
        if credential_id is None:
            await self._audit_missing(
                ha_user_id,
                person_id,
                access_point_id,
                trace=trace,
            )
            raise RevealCredentialUnavailableError
        try:
            _trace_stage(trace, "vault_retrieval_started")
            plaintext = await self._credential_vault.retrieve(
                credential_id,
                trace=trace,
            )
        except VaultCredentialNotFoundError:
            await self._audit_missing(
                ha_user_id,
                person_id,
                access_point_id,
                trace=trace,
            )
            raise RevealCredentialUnavailableError from None
        except (VaultNotInitializedError, VaultUnavailableError):
            await self._audit(
                ha_user_id,
                person_id,
                access_point_id,
                RevealOutcome.VAULT_UNAVAILABLE,
                RevealReason.VAULT_UNAVAILABLE,
                trace=trace,
            )
            raise RevealVaultUnavailableError from None
        except VaultError:
            await self._audit_failed(
                ha_user_id,
                person_id,
                access_point_id,
                trace=trace,
            )
            raise RevealError from None
        except Exception:
            await self._audit_failed(
                ha_user_id,
                person_id,
                access_point_id,
                trace=trace,
            )
            raise RevealError from None
        await self._audit(
            ha_user_id,
            person_id,
            access_point_id,
            RevealOutcome.REVEALED,
            RevealReason.SUCCESS,
            trace=trace,
        )
        return plaintext

    async def audit_denied(
        self,
        ha_user_id: str,
        person_id: UUID,
        access_point_id: UUID | None,
        *,
        trace: RevealTraceCallback | None = None,
    ) -> None:
        """Durably record an identifiable non-administrator request."""
        trace = _best_effort_trace(trace)
        self._rate_limiter.record_denied(person_id, access_point_id)
        await self._audit(
            ha_user_id,
            person_id,
            access_point_id,
            RevealOutcome.DENIED,
            RevealReason.ADMIN_REQUIRED,
            trace=trace,
        )

    async def _audit_missing(
        self,
        ha_user_id: str,
        person_id: UUID,
        access_point_id: UUID | None,
        *,
        trace: RevealTraceCallback | None = None,
    ) -> None:
        """Record a missing assignment or encrypted credential safely."""
        await self._audit(
            ha_user_id,
            person_id,
            access_point_id,
            RevealOutcome.CREDENTIAL_MISSING,
            RevealReason.CREDENTIAL_MISSING,
            trace=trace,
        )

    async def _audit_failed(
        self,
        ha_user_id: str,
        person_id: UUID,
        access_point_id: UUID | None,
        *,
        trace: RevealTraceCallback | None = None,
    ) -> None:
        """Record a sanitized internal retrieval failure."""
        await self._audit(
            ha_user_id,
            person_id,
            access_point_id,
            RevealOutcome.FAILED,
            RevealReason.RETRIEVAL_FAILED,
            trace=trace,
        )

    async def _audit(
        self,
        ha_user_id: str,
        person_id: UUID,
        access_point_id: UUID | None,
        outcome: RevealOutcome,
        reason: RevealReason,
        *,
        trace: RevealTraceCallback | None = None,
    ) -> None:
        """Commit one approved non-secret audit event."""
        _trace_stage(trace, "reveal_audit_append_started")
        await self._audit_repository.append(
            RevealAuditEvent(
                event_id=uuid4(),
                timestamp=datetime.now(UTC),
                ha_user_id=ha_user_id,
                person_id=person_id,
                access_point_id=access_point_id,
                outcome=outcome,
                reason_code=reason,
            ),
            trace=trace,
        )


__all__ = [
    "CredentialRevealService",
    "REVEAL_AUDIT_MAX_EVENTS",
    "REVEAL_AUDIT_RETENTION",
    "REVEAL_AUDIT_STORAGE_KEY",
    "RevealAuditError",
    "RevealAuditEvent",
    "RevealAuditRepository",
    "RevealCredentialUnavailableError",
    "RevealError",
    "RevealOutcome",
    "RevealRateLimitedError",
    "RevealRateLimiter",
    "RevealReason",
    "RevealTraceCallback",
    "RevealVaultUnavailableError",
]
