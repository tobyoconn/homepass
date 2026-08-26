"""Bounded in-memory correlation for confirmed HomePASS lock commands."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from uuid import UUID

from ..models import LockEventOrigin

_DEFAULT_EXPIRY = timedelta(seconds=10)
_HOMEPASS_COMMAND_ORIGINS = frozenset(
    {
        LockEventOrigin.HOMEPASS_MANUAL,
        LockEventOrigin.HOMEPASS_AUTOMATIC,
        LockEventOrigin.HOMEPASS_KEYPAD,
        LockEventOrigin.NFC_PASSKEY,
    }
)


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _normalize_timestamp(value: datetime, field_name: str) -> datetime:
    if not isinstance(value, datetime):
        raise TypeError(f"Lock command {field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"Lock command {field_name} must be timezone-aware")
    return value.astimezone(UTC)


class LockStableState(StrEnum):
    """Stable lock states that a HomePASS command may request."""

    LOCKED = "locked"
    UNLOCKED = "unlocked"


class LockCommandCorrelationError(ValueError):
    """Raised when a command cannot be correlated without ambiguity."""


@dataclass(frozen=True, slots=True)
class PendingLockCommand:
    """One exact HomePASS command awaiting a stable physical confirmation."""

    access_point_id: UUID
    requested_state: LockStableState
    origin: LockEventOrigin
    command_id: UUID
    initiated_at: datetime
    expires_at: datetime
    person_id: UUID | None = None
    person_name: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.access_point_id, UUID):
            raise TypeError("Lock command access_point_id must be a UUID")
        if not isinstance(self.requested_state, LockStableState):
            raise TypeError("Lock command requested_state is invalid")
        if self.origin not in _HOMEPASS_COMMAND_ORIGINS:
            raise ValueError("Lock command origin must be a HomePASS command origin")
        if not isinstance(self.command_id, UUID):
            raise TypeError("Lock command command_id must be a UUID")
        if self.person_id is not None and not isinstance(self.person_id, UUID):
            raise TypeError("Lock command person_id must be a UUID")
        if (self.person_id is None) != (self.person_name is None):
            raise ValueError("Lock command Person identity and name must be supplied together")
        if self.person_name is not None:
            if not isinstance(self.person_name, str):
                raise TypeError("Lock command person_name must be a string")
            person_name = self.person_name.strip()
            if (
                not person_name
                or len(person_name) > 100
                or any(ord(character) < 32 for character in person_name)
            ):
                raise ValueError("Lock command person_name is not safe display text")
            object.__setattr__(self, "person_name", person_name)
        initiated_at = _normalize_timestamp(self.initiated_at, "initiated_at")
        expires_at = _normalize_timestamp(self.expires_at, "expires_at")
        if expires_at <= initiated_at:
            raise ValueError("Lock command expiry must follow initiation")
        object.__setattr__(self, "initiated_at", initiated_at)
        object.__setattr__(self, "expires_at", expires_at)


class LockCommandCorrelationService:
    """Match one pending HomePASS command to one exact stable lock transition."""

    def __init__(
        self,
        *,
        clock: Callable[[], datetime] = _utcnow,
        expiry: timedelta = _DEFAULT_EXPIRY,
    ) -> None:
        if not isinstance(expiry, timedelta):
            raise TypeError("Lock command expiry must be a timedelta")
        if expiry <= timedelta(0):
            raise ValueError("Lock command expiry must be positive")
        self._clock = clock
        self._expiry = expiry
        self._pending_by_access_point: dict[UUID, PendingLockCommand] = {}

    @property
    def pending_count(self) -> int:
        """Return the number of unexpired confirmations still awaited."""
        self._expire_before(self._now())
        return len(self._pending_by_access_point)

    def register(
        self,
        *,
        access_point_id: UUID,
        requested_state: LockStableState,
        origin: LockEventOrigin,
        command_id: UUID,
        person_id: UUID | None = None,
        person_name: str | None = None,
    ) -> PendingLockCommand:
        """Register one command before dispatch, rejecting ambiguous overlap."""
        now = self._now()
        self._expire_before(now)
        candidate = PendingLockCommand(
            access_point_id=access_point_id,
            requested_state=requested_state,
            origin=origin,
            command_id=command_id,
            initiated_at=now,
            expires_at=now + self._expiry,
            person_id=person_id,
            person_name=person_name,
        )
        for pending in self._pending_by_access_point.values():
            if pending.command_id == command_id:
                if (
                    pending.access_point_id == access_point_id
                    and pending.requested_state is requested_state
                    and pending.origin is origin
                    and pending.person_id == person_id
                    and pending.person_name == person_name
                ):
                    return pending
                raise LockCommandCorrelationError("Lock command ID is already in use")
        if access_point_id in self._pending_by_access_point:
            raise LockCommandCorrelationError(
                "HomePASS is already waiting for this Door to confirm a command"
            )
        self._pending_by_access_point[access_point_id] = candidate
        return candidate

    def consume(
        self,
        *,
        access_point_id: UUID,
        confirmed_state: LockStableState,
        confirmed_at: datetime,
    ) -> PendingLockCommand | None:
        """Consume one exact, timely, matching stable confirmation."""
        if not isinstance(access_point_id, UUID):
            raise TypeError("Lock confirmation access_point_id must be a UUID")
        if not isinstance(confirmed_state, LockStableState):
            raise TypeError("Lock confirmation state is invalid")
        confirmation_time = _normalize_timestamp(confirmed_at, "confirmed_at")
        now = self._now()
        self._expire_before(now)
        pending = self._pending_by_access_point.get(access_point_id)
        if pending is None or pending.requested_state is not confirmed_state:
            return None
        if not pending.initiated_at <= confirmation_time < pending.expires_at:
            if confirmation_time >= pending.expires_at:
                self._pending_by_access_point.pop(access_point_id, None)
            return None
        self._pending_by_access_point.pop(access_point_id, None)
        return pending

    def cancel(self, command_id: UUID) -> None:
        """Remove only the failed command identified by the dispatch boundary."""
        if not isinstance(command_id, UUID):
            raise TypeError("Lock command command_id must be a UUID")
        for access_point_id, pending in tuple(self._pending_by_access_point.items()):
            if pending.command_id == command_id:
                self._pending_by_access_point.pop(access_point_id, None)
                return

    def clear(self) -> None:
        """Forget all unconfirmed commands during config-entry unload or restart."""
        self._pending_by_access_point.clear()

    def _now(self) -> datetime:
        return _normalize_timestamp(self._clock(), "clock")

    def _expire_before(self, now: datetime) -> None:
        for access_point_id, pending in tuple(self._pending_by_access_point.items()):
            if pending.expires_at <= now:
                self._pending_by_access_point.pop(access_point_id, None)


__all__ = [
    "LockCommandCorrelationError",
    "LockCommandCorrelationService",
    "LockStableState",
    "PendingLockCommand",
]
