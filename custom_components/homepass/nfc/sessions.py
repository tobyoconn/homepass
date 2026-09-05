"""Short-lived, single-use NFC and WebAuthn session state."""

from __future__ import annotations

import secrets
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Generic, TypeVar

T = TypeVar("T")


class SessionError(ValueError):
    """Raised when a session is absent, expired, or already used."""


@dataclass(frozen=True, slots=True)
class _Item(Generic[T]):
    value: T
    expires_at: datetime


class ExpiringTokenStore(Generic[T]):
    """Bounded in-memory bearer tokens consumed exactly once."""

    def __init__(
        self,
        *,
        ttl: timedelta,
        max_items: int = 1024,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        if ttl <= timedelta(0) or max_items < 1:
            raise ValueError("Session limits must be positive")
        self._ttl = ttl
        self._max_items = max_items
        self._clock = clock
        self._items: dict[str, _Item[T]] = {}

    def issue(self, value: T) -> str:
        now = self._clock()
        self._expire(now)
        if len(self._items) >= self._max_items:
            oldest = min(self._items, key=lambda key: self._items[key].expires_at)
            self._items.pop(oldest, None)
        token = secrets.token_urlsafe(32)
        self._items[token] = _Item(value, now + self._ttl)
        return token

    def peek(self, token: str) -> T:
        now = self._clock()
        self._expire(now)
        item = self._items.get(token)
        if item is None:
            raise SessionError("Session is invalid or expired")
        return item.value

    def consume(self, token: str) -> T:
        value = self.peek(token)
        self._items.pop(token, None)
        return value

    def _expire(self, now: datetime) -> None:
        for token, item in tuple(self._items.items()):
            if item.expires_at <= now:
                self._items.pop(token, None)
