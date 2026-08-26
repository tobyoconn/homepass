"""Transport-neutral secure processing for HomePASS-managed keypads."""

from __future__ import annotations

import asyncio
import secrets
from collections import deque
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import TYPE_CHECKING, Protocol

from homeassistant.const import SERVICE_LOCK, SERVICE_UNLOCK

from ..models import (
    AccessDevice,
    ActivityAccessMethod,
    ActivityActorType,
    ActivityEventType,
    ActivityNavigationKind,
    ActivityNavigationReference,
    ActivityOutcome,
    ActivitySource,
    KeypadOperation,
    LockEventOrigin,
)
from .activity import ActivityEventProposal, ActivityService

if TYPE_CHECKING:
    from uuid import UUID

    from homeassistant.core import Context

    from ..vault import CredentialMetadata, CredentialVaultProtocol
    from .access_device import AccessDeviceService
    from .access_point import AccessPointService
    from .access_point_command import AccessPointCommandService
    from .authorization import AuthorizationService

_FAILURE_WINDOW = timedelta(minutes=5)
_MAX_FAILURES = 5


class CredentialMetadataStore(Protocol):
    """Load only non-secret enabled credential relationships."""

    async def list_enabled(self) -> tuple[CredentialMetadata, ...]: ...


class KeypadProcessingOutcome(StrEnum):
    """Security-safe result that a transport may translate to its protocol."""

    SUCCESS = "success"
    INVALID_CODE = "invalid_code"
    NOT_READY = "not_ready"


@dataclass(frozen=True, slots=True, repr=False)
class KeypadCommand:
    """Transport-neutral request whose transient PIN is always redacted."""

    device: AccessDevice
    button: str
    pin: str
    occurred_at: datetime
    context: Context
    source_event_key: str

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}(device_id={self.device.id!r}, "
            f"button={self.button!r}, pin=<redacted>, "
            f"source_event_key={self.source_event_key!r})"
        )


@dataclass(frozen=True, slots=True)
class KeypadProcessingResult:
    """Outcome without credentials or other secret material."""

    outcome: KeypadProcessingOutcome
    operation: KeypadOperation | None = None
    command_sent: bool = False


class KeypadCommandProcessor:
    """Apply one security policy and command path to every keypad transport."""

    def __init__(
        self,
        access_device_service: AccessDeviceService,
        credential_metadata: CredentialMetadataStore,
        credential_vault: CredentialVaultProtocol,
        authorization_service: AuthorizationService,
        access_point_service: AccessPointService,
        access_point_commands: AccessPointCommandService,
        activity_service: ActivityService,
    ) -> None:
        self._access_device_service = access_device_service
        self._credential_metadata = credential_metadata
        self._credential_vault = credential_vault
        self._authorization_service = authorization_service
        self._access_point_service = access_point_service
        self._access_point_commands = access_point_commands
        self._activity_service = activity_service
        self._locks: dict[UUID, asyncio.Lock] = {}
        self._failures: dict[UUID, deque[datetime]] = {}

    async def process(self, command: KeypadCommand) -> KeypadProcessingResult:
        """Validate and execute at most one configured operation for a keypad request."""
        lock = self._locks.setdefault(command.device.id, asyncio.Lock())
        async with lock:
            return await self._process_locked(command)

    async def _process_locked(self, command: KeypadCommand) -> KeypadProcessingResult:
        device = command.device
        if not device.enabled:
            return KeypadProcessingResult(KeypadProcessingOutcome.NOT_READY)
        operation = device.button_actions.get(command.button, KeypadOperation.NONE)
        if operation is KeypadOperation.NONE:
            return KeypadProcessingResult(KeypadProcessingOutcome.NOT_READY)

        now = command.occurred_at.astimezone(UTC)
        failures = self._current_failures(device.id, now)
        if len(failures) >= _MAX_FAILURES:
            await self._record_failure(
                device,
                now,
                len(failures),
                command.source_event_key,
            )
            return KeypadProcessingResult(KeypadProcessingOutcome.NOT_READY)

        person_id = await self._resolve_person_id(command.pin)
        if person_id is None:
            failures.append(now)
            await self._record_failure(
                device,
                now,
                len(failures),
                command.source_event_key,
            )
            return KeypadProcessingResult(KeypadProcessingOutcome.INVALID_CODE)

        relationship = await self._authorization_service.resolve_person_for_access_point(
            person_id=person_id,
            access_point_id=device.access_point_id,
            instant_utc=now,
        )
        if relationship is None or not relationship.decision.allowed:
            failures.append(now)
            await self._record_failure(
                device,
                now,
                len(failures),
                command.source_event_key,
                person_id=(relationship.person.person_id if relationship is not None else None),
                person_name=(
                    relationship.person.display_name if relationship is not None else None
                ),
            )
            return KeypadProcessingResult(KeypadProcessingOutcome.NOT_READY)

        service = SERVICE_UNLOCK if operation is KeypadOperation.UNLOCK else SERVICE_LOCK
        command_result = await self._access_point_commands.execute(
            device.access_point_id,
            service,
            origin=LockEventOrigin.HOMEPASS_KEYPAD,
            context=command.context,
            person_id=relationship.person.person_id,
            person_name=relationship.person.display_name,
        )
        self._failures.pop(device.id, None)
        await self._access_device_service.mark_ready_after_hardware_test(device.id)
        return KeypadProcessingResult(
            KeypadProcessingOutcome.SUCCESS,
            operation=operation,
            command_sent=command_result.command_sent,
        )

    async def _resolve_person_id(self, supplied_pin: str) -> UUID | None:
        matches: list[UUID] = []
        credentials = await self._credential_metadata.list_enabled()
        for metadata in credentials:
            saved_pin = await self._credential_vault.retrieve(metadata.credential_id)
            try:
                if secrets.compare_digest(saved_pin, supplied_pin):
                    matches.append(metadata.person_id)
            finally:
                saved_pin = ""
        return matches[0] if len(matches) == 1 else None

    def _current_failures(self, device_id: UUID, now: datetime) -> deque[datetime]:
        failures = self._failures.setdefault(device_id, deque())
        cutoff = now - _FAILURE_WINDOW
        while failures and failures[0] < cutoff:
            failures.popleft()
        return failures

    async def _record_failure(
        self,
        device: AccessDevice,
        occurred_at: datetime,
        attempt_count: int,
        source_event_key: str,
        *,
        person_id: UUID | None = None,
        person_name: str | None = None,
    ) -> None:
        access_point = await self._access_point_service.get_access_point(device.access_point_id)
        await self._activity_service.record(
            ActivityEventProposal(
                event_type=ActivityEventType.PIN_FAILED,
                occurred_at=occurred_at,
                source=ActivitySource.HOME_ASSISTANT,
                actor_type=(
                    ActivityActorType.PERSON
                    if person_id is not None
                    else ActivityActorType.CREDENTIAL
                ),
                actor_id=person_id,
                actor_name=person_name,
                person_id=person_id,
                person_name=person_name,
                access_method=ActivityAccessMethod.KEYPAD,
                outcome=ActivityOutcome.FAILED,
                door_id=access_point.id,
                door_name=access_point.display_name,
                attributes={"attempt_count": max(1, attempt_count)},
                navigation=(
                    ActivityNavigationReference(ActivityNavigationKind.DOOR, access_point.id),
                ),
                source_event_key=source_event_key,
            )
        )

    def reset(self) -> None:
        """Clear transient security state after all transport work has stopped."""
        self._locks.clear()
        self._failures.clear()


__all__ = [
    "CredentialMetadataStore",
    "KeypadCommand",
    "KeypadCommandProcessor",
    "KeypadProcessingOutcome",
    "KeypadProcessingResult",
]
