"""Vendor-neutral provider backed by Nuki's local Bluetooth protocol."""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from typing import Protocol

from .base import (
    AccessProviderCapabilities,
    AuthorizationMutation,
    AuthorizationMutationState,
    AuthorizationProvider,
    AuthorizationRecord,
    AuthorizationRequest,
    AuthorizationSchedule,
    ProviderAuditEvent,
    ProviderCommunicationError,
)
from .nuki_pin import validate_nuki_keypad_pin


@dataclass(frozen=True, slots=True)
class NukiLocalKeypadCode:
    """One local Nuki keypad code read directly from the lock."""

    external_id: str
    display_name: str
    pin: str
    enabled: bool
    schedule: AuthorizationSchedule


class NukiLocalTransport(Protocol):
    """Secret-safe semantic boundary around one paired Nuki lock."""

    async def add_keypad_code(self, request: AuthorizationRequest) -> str:
        """Create one code and return the lock-assigned code identifier."""

    async def update_keypad_code(self, external_id: str, request: AuthorizationRequest) -> None:
        """Update one existing code."""

    async def remove_keypad_code(self, external_id: str) -> None:
        """Remove one existing code."""

    async def list_keypad_codes(self) -> tuple[NukiLocalKeypadCode, ...]:
        """Return codes from the lock without logging or persisting their PINs."""

    async def list_audit_events(self, *, limit: int) -> tuple[ProviderAuditEvent, ...]:
        """Return recent local lock audit events."""


class NukiLocalAuthorizationProvider(AuthorizationProvider):
    """Manage Ultra keypad access locally while preserving read-back truth."""

    def __init__(self, transport: NukiLocalTransport) -> None:
        self._transport = transport

    @property
    def capabilities(self) -> AccessProviderCapabilities:
        return AccessProviderCapabilities(
            local_lock_control=False,
            keypad_codes=True,
            named_authorizations=True,
            schedules=True,
            audit_events=True,
            exact_pin_readback=True,
        )

    async def create_authorization(self, request: AuthorizationRequest) -> AuthorizationMutation:
        self._validate_request(request)
        if not request.enabled:
            raise ValueError("Nuki cannot safely create a disabled keypad authorization")
        try:
            external_id = await self._transport.add_keypad_code(request)
        except ProviderCommunicationError as err:
            return self._failed(err)
        return AuthorizationMutation(
            AuthorizationMutationState.PENDING,
            external_id=external_id,
        )

    async def update_authorization(
        self, external_id: str, request: AuthorizationRequest
    ) -> AuthorizationMutation:
        self._validate_external_id(external_id)
        self._validate_request(request)
        try:
            await self._transport.update_keypad_code(external_id, request)
        except ProviderCommunicationError as err:
            return self._failed(err, external_id=external_id)
        return AuthorizationMutation(
            AuthorizationMutationState.PENDING,
            external_id=external_id,
        )

    async def delete_authorization(self, external_id: str) -> AuthorizationMutation:
        self._validate_external_id(external_id)
        try:
            await self._transport.remove_keypad_code(external_id)
        except ProviderCommunicationError as err:
            return self._failed(err, external_id=external_id)
        return AuthorizationMutation(
            AuthorizationMutationState.PENDING,
            external_id=external_id,
        )

    async def verify_authorization(
        self,
        request: AuthorizationRequest,
        *,
        external_id: str | None = None,
    ) -> AuthorizationMutation:
        self._validate_request(request)
        if external_id is not None:
            self._validate_external_id(external_id)
        try:
            records = await self._transport.list_keypad_codes()
        except ProviderCommunicationError as err:
            return self._failed(err, external_id=external_id)
        for record in records:
            if external_id is not None and record.external_id != external_id:
                continue
            if self._matches(record, request):
                return AuthorizationMutation(
                    AuthorizationMutationState.CONFIRMED,
                    external_id=record.external_id,
                )
        return AuthorizationMutation(
            AuthorizationMutationState.PENDING,
            external_id=external_id,
        )

    async def verify_authorization_deleted(self, external_id: str) -> AuthorizationMutation:
        self._validate_external_id(external_id)
        try:
            records = await self._transport.list_keypad_codes()
        except ProviderCommunicationError as err:
            return self._failed(err, external_id=external_id)
        return AuthorizationMutation(
            AuthorizationMutationState.PENDING
            if any(record.external_id == external_id for record in records)
            else AuthorizationMutationState.CONFIRMED,
            external_id=external_id,
        )

    async def list_authorizations(self) -> tuple[AuthorizationRecord, ...]:
        return tuple(
            AuthorizationRecord(
                external_id=record.external_id,
                display_name=record.display_name,
                enabled=record.enabled,
                schedule=record.schedule,
            )
            for record in await self._transport.list_keypad_codes()
        )

    async def get_authorization(self, external_id: str) -> AuthorizationRecord | None:
        self._validate_external_id(external_id)
        return next(
            (
                AuthorizationRecord(
                    external_id=record.external_id,
                    display_name=record.display_name,
                    enabled=record.enabled,
                    schedule=record.schedule,
                )
                for record in await self._transport.list_keypad_codes()
                if record.external_id == external_id
            ),
            None,
        )

    async def verify_pin(self, external_id: str, pin: str) -> AuthorizationMutation:
        self._validate_external_id(external_id)
        try:
            records = await self._transport.list_keypad_codes()
        except ProviderCommunicationError as err:
            return self._failed(err, external_id=external_id)
        for record in records:
            if record.external_id != external_id:
                continue
            return AuthorizationMutation(
                AuthorizationMutationState.CONFIRMED
                if secrets.compare_digest(record.pin, pin)
                else AuthorizationMutationState.FAILED,
                external_id=external_id,
            )
        return AuthorizationMutation(
            AuthorizationMutationState.PENDING,
            external_id=external_id,
        )

    async def list_audit_events(self, *, limit: int = 50) -> tuple[ProviderAuditEvent, ...]:
        if isinstance(limit, bool) or not 1 <= limit <= 50:
            raise ValueError("Nuki audit limit must be between 1 and 50")
        return await self._transport.list_audit_events(limit=limit)

    @staticmethod
    def _matches(record: NukiLocalKeypadCode, request: AuthorizationRequest) -> bool:
        return (
            record.display_name == request.display_name
            and record.enabled is request.enabled
            and record.schedule == request.schedule
            and secrets.compare_digest(record.pin, request.pin)
        )

    @staticmethod
    def _validate_request(request: AuthorizationRequest) -> None:
        if len(request.display_name.encode("utf-8")) > 20:
            raise ValueError("Nuki keypad names may contain at most 20 UTF-8 bytes")
        validate_nuki_keypad_pin(request.pin)

    @staticmethod
    def _validate_external_id(external_id: str) -> None:
        if not isinstance(external_id, str) or not external_id.isdecimal() or int(external_id) < 1:
            raise ValueError("Nuki keypad code identifier must be a positive number")

    @staticmethod
    def _failed(
        error: ProviderCommunicationError,
        *,
        external_id: str | None = None,
    ) -> AuthorizationMutation:
        return AuthorizationMutation(
            AuthorizationMutationState.FAILED,
            external_id=external_id,
            error_summary=str(error),
        )


__all__ = [
    "NukiLocalAuthorizationProvider",
    "NukiLocalKeypadCode",
    "NukiLocalTransport",
]
