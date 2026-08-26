"""Nuki Web API authorization and audit provider."""

from __future__ import annotations

import asyncio
import secrets
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any, Protocol

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

_NUKI_KEYPAD_AUTH_TYPE = 13
_WEEKDAY_BITS = {1: 64, 2: 32, 3: 16, 4: 8, 5: 4, 6: 2, 7: 1}
_ACTION_NAMES = {1: "unlock", 2: "lock", 3: "unlatch", 4: "lock_n_go", 5: "lock_n_go_unlatch"}
_SOURCE_NAMES = {0: "default", 1: "keypad", 2: "fingerprint"}


class NukiApiTransport(Protocol):
    """Small injectable HTTP boundary for the Nuki Web API."""

    async def request(
        self,
        method: str,
        path: str,
        *,
        payload: object | None = None,
    ) -> object:
        """Perform one authenticated API request and return decoded JSON."""


class NukiWebApiClient:
    """Authenticated Nuki Web API transport with secret-safe errors and repr."""

    def __init__(
        self,
        session: Any,
        bearer_token: str,
        *,
        base_url: str = "https://api.nuki.io",
        timeout_seconds: float = 15.0,
    ) -> None:
        token = bearer_token.strip()
        if not token:
            raise ValueError("Nuki bearer token must not be empty")
        self._session = session
        self._bearer_token = token
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds

    def __repr__(self) -> str:
        return f"{type(self).__name__}(base_url={self._base_url!r}, bearer_token=<redacted>)"

    async def request(
        self,
        method: str,
        path: str,
        *,
        payload: object | None = None,
    ) -> object:
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self._bearer_token}",
        }
        if payload is not None:
            headers["Content-Type"] = "application/json"
        try:
            async with asyncio.timeout(self._timeout_seconds):
                async with self._session.request(
                    method,
                    f"{self._base_url}{path}",
                    headers=headers,
                    json=payload,
                ) as response:
                    if response.status < 200 or response.status >= 300:
                        raise ProviderCommunicationError(
                            f"Nuki API request failed with HTTP {response.status}"
                        )
                    if response.status == 204 or response.content_length == 0:
                        return None
                    return await response.json(content_type=None)
        except ProviderCommunicationError:
            raise
        except TimeoutError as err:
            raise ProviderCommunicationError("Nuki API request timed out") from err
        except Exception as err:
            raise ProviderCommunicationError("Nuki API request failed") from err


class NukiAuthorizationProvider(AuthorizationProvider):
    """Manage Nuki keypad authorizations while exposing asynchronous truth."""

    def __init__(self, transport: NukiApiTransport, smartlock_id: str | int) -> None:
        normalized_id = str(smartlock_id).strip()
        if not normalized_id.isdecimal() or int(normalized_id) <= 0:
            raise ValueError("Nuki smartlock_id must be a positive decimal identifier")
        self._transport = transport
        self._smartlock_id = normalized_id

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
            raise ValueError(
                "Nuki cannot safely create an authorization while its HomePASS schedule is disabled"
            )
        try:
            response = await self._transport.request(
                "PUT",
                "/smartlock/auth",
                payload=self._request_payload(request, include_targets=True),
            )
        except ProviderCommunicationError as err:
            return self._failed(err)
        external_id, request_id = self._mutation_identifiers(response)
        return AuthorizationMutation(
            AuthorizationMutationState.PENDING,
            external_id=external_id,
            request_id=request_id,
        )

    async def update_authorization(
        self, external_id: str, request: AuthorizationRequest
    ) -> AuthorizationMutation:
        self._validate_external_id(external_id)
        self._validate_request(request)
        try:
            raw_records = await self._raw_authorizations()
            provider_record_id = next(
                (
                    str(raw["id"])
                    for raw in raw_records
                    if self._external_id(raw) == external_id and raw.get("id") is not None
                ),
                None,
            )
            if provider_record_id is None:
                return AuthorizationMutation(
                    AuthorizationMutationState.FAILED,
                    external_id=external_id,
                    error_summary="Nuki authorization was not found",
                )
            response = await self._transport.request(
                "POST",
                f"/smartlock/{self._smartlock_id}/auth/{provider_record_id}",
                payload=self._request_payload(request, include_targets=False),
            )
        except ProviderCommunicationError as err:
            return self._failed(err, external_id=external_id)
        _, request_id = self._mutation_identifiers(response)
        return AuthorizationMutation(
            AuthorizationMutationState.PENDING,
            external_id=external_id,
            request_id=request_id,
        )

    async def delete_authorization(self, external_id: str) -> AuthorizationMutation:
        self._validate_external_id(external_id)
        try:
            raw_records = await self._raw_authorizations()
            provider_record_id = next(
                (
                    str(raw["id"])
                    for raw in raw_records
                    if self._external_id(raw) == external_id and raw.get("id") is not None
                ),
                None,
            )
            if provider_record_id is None:
                return AuthorizationMutation(
                    AuthorizationMutationState.CONFIRMED,
                    external_id=external_id,
                )
            response = await self._transport.request(
                "DELETE",
                "/smartlock/auth",
                payload=[provider_record_id],
            )
        except ProviderCommunicationError as err:
            return self._failed(err, external_id=external_id)
        _, request_id = self._mutation_identifiers(response)
        return AuthorizationMutation(
            AuthorizationMutationState.PENDING,
            external_id=external_id,
            request_id=request_id,
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
            raw_records = await self._raw_authorizations()
        except ProviderCommunicationError as err:
            return self._failed(err, external_id=external_id)
        for raw in raw_records:
            record_id = self._external_id(raw)
            if external_id is not None and record_id != external_id:
                continue
            if self._matches(raw, request):
                return AuthorizationMutation(
                    AuthorizationMutationState.CONFIRMED,
                    external_id=record_id,
                )
        return AuthorizationMutation(
            AuthorizationMutationState.PENDING,
            external_id=external_id,
        )

    async def verify_authorization_deleted(self, external_id: str) -> AuthorizationMutation:
        self._validate_external_id(external_id)
        try:
            raw_records = await self._raw_authorizations()
        except ProviderCommunicationError as err:
            return self._failed(err, external_id=external_id)
        if any(self._external_id(raw) == external_id for raw in raw_records):
            return AuthorizationMutation(
                AuthorizationMutationState.PENDING,
                external_id=external_id,
            )
        return AuthorizationMutation(
            AuthorizationMutationState.CONFIRMED,
            external_id=external_id,
        )

    async def list_authorizations(self) -> tuple[AuthorizationRecord, ...]:
        return tuple(self._safe_record(raw) for raw in await self._raw_authorizations())

    async def get_authorization(self, external_id: str) -> AuthorizationRecord | None:
        """Return one safe authorization record by Nuki authId."""
        self._validate_external_id(external_id)
        return next(
            (
                self._safe_record(raw)
                for raw in await self._raw_authorizations()
                if self._external_id(raw) == external_id
            ),
            None,
        )

    async def verify_pin(self, external_id: str, pin: str) -> AuthorizationMutation:
        """Compare a transient PIN inside the adapter without returning it."""
        self._validate_external_id(external_id)
        try:
            raw_records = await self._raw_authorizations()
        except ProviderCommunicationError as err:
            return self._failed(err, external_id=external_id)
        for raw in raw_records:
            if self._external_id(raw) != external_id:
                continue
            raw_code = raw.get("code")
            code = str(raw_code) if isinstance(raw_code, str | int) else ""
            return AuthorizationMutation(
                AuthorizationMutationState.CONFIRMED
                if secrets.compare_digest(code, pin)
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
        response = await self._transport.request(
            "GET",
            f"/smartlock/{self._smartlock_id}/log?limit={limit}",
        )
        records = self._record_list(response, "Nuki log response")
        return tuple(self._audit_record(raw) for raw in records[:limit])

    async def _raw_authorizations(self) -> tuple[Mapping[str, object], ...]:
        response = await self._transport.request(
            "GET", f"/smartlock/{self._smartlock_id}/auth?types={_NUKI_KEYPAD_AUTH_TYPE}"
        )
        return self._record_list(response, "Nuki authorization response")

    def _request_payload(
        self, request: AuthorizationRequest, *, include_targets: bool
    ) -> dict[str, object]:
        payload: dict[str, object] = {
            "name": request.display_name,
            "code": int(request.pin),
            "remoteAllowed": False,
        }
        if include_targets:
            payload["type"] = _NUKI_KEYPAD_AUTH_TYPE
            payload["smartlockIds"] = [int(self._smartlock_id)]
        else:
            payload["enabled"] = request.enabled
        schedule = request.schedule
        if schedule.valid_from is not None:
            payload["allowedFromDate"] = self._nuki_datetime(schedule.valid_from)
        if schedule.valid_until is not None:
            payload["allowedUntilDate"] = self._nuki_datetime(schedule.valid_until)
        if schedule.weekdays:
            payload["allowedWeekDays"] = sum(_WEEKDAY_BITS[day] for day in schedule.weekdays)
        if schedule.from_minute is not None:
            payload["allowedFromTime"] = schedule.from_minute
            payload["allowedUntilTime"] = schedule.until_minute
        return payload

    @staticmethod
    def _validate_request(request: AuthorizationRequest) -> None:
        if len(request.display_name) > 32:
            raise ValueError("Nuki authorization names may contain at most 32 characters")
        validate_nuki_keypad_pin(request.pin)

    @staticmethod
    def _validate_external_id(external_id: str) -> None:
        if not isinstance(external_id, str) or not external_id.strip():
            raise ValueError("Nuki authorization identifier must not be empty")

    def _matches(self, raw: Mapping[str, object], request: AuthorizationRequest) -> bool:
        raw_code = raw.get("code")
        code = str(raw_code) if isinstance(raw_code, str | int) else ""
        return (
            raw.get("type") in {_NUKI_KEYPAD_AUTH_TYPE, str(_NUKI_KEYPAD_AUTH_TYPE)}
            and raw.get("name") == request.display_name
            and bool(raw.get("enabled", raw.get("enable", True))) is request.enabled
            and secrets.compare_digest(code, request.pin)
            and self._schedule_from_raw(raw) == request.schedule
        )

    def _safe_record(self, raw: Mapping[str, object]) -> AuthorizationRecord:
        external_id = self._external_id(raw)
        display_name = raw.get("name")
        if not isinstance(display_name, str) or not display_name.strip():
            raise ProviderCommunicationError("Nuki authorization response is invalid")
        return AuthorizationRecord(
            external_id=external_id,
            display_name=display_name.strip(),
            enabled=bool(raw.get("enabled", raw.get("enable", True))),
            schedule=self._schedule_from_raw(raw),
        )

    @classmethod
    def _schedule_from_raw(cls, raw: Mapping[str, object]) -> AuthorizationSchedule:
        weekdays_value = raw.get("allowedWeekDays")
        weekdays_mask = weekdays_value if isinstance(weekdays_value, int) else 0
        raw_from_minute = raw.get("allowedFromTime")
        raw_until_minute = raw.get("allowedUntilTime")
        if (
            isinstance(raw_from_minute, int)
            and isinstance(raw_until_minute, int)
            and raw_from_minute != raw_until_minute
        ):
            from_minute: int | None = raw_from_minute
            until_minute: int | None = raw_until_minute
        else:
            from_minute = None
            until_minute = None
        return AuthorizationSchedule(
            valid_from=cls._parse_datetime(raw.get("allowedFromDate")),
            valid_until=cls._parse_datetime(raw.get("allowedUntilDate")),
            weekdays=(
                frozenset(day for day, bit in _WEEKDAY_BITS.items() if weekdays_mask & bit)
                if from_minute is not None
                else frozenset()
            ),
            from_minute=from_minute,
            until_minute=until_minute,
        )

    @classmethod
    def _audit_record(cls, raw: Mapping[str, object]) -> ProviderAuditEvent:
        raw_id = raw.get("id", raw.get("index"))
        timestamp = cls._parse_datetime(raw.get("date", raw.get("timestamp")))
        if raw_id is None or timestamp is None:
            raise ProviderCommunicationError("Nuki log response is invalid")
        action_value = raw.get("action")
        state_value = raw.get("state")
        source_value = raw.get("source")
        auth_id = raw.get("authId")
        name = raw.get("name")
        return ProviderAuditEvent(
            external_id=str(raw_id),
            occurred_at=timestamp,
            action=(
                _ACTION_NAMES.get(action_value, str(action_value))
                if isinstance(action_value, int)
                else str(action_value)
            ),
            outcome="success" if state_value == 0 else "failed",
            authorization_external_id=str(auth_id) if auth_id is not None else None,
            authorization_name=name if isinstance(name, str) else None,
            source=(
                _SOURCE_NAMES.get(source_value, str(source_value))
                if isinstance(source_value, int)
                else str(source_value)
                if source_value is not None
                else None
            ),
        )

    def _mutation_identifiers(self, response: object) -> tuple[str | None, str | None]:
        if not isinstance(response, Mapping):
            return None, None
        request_id = response.get("requestId")
        external_id: str | None = None
        detail = response.get("detail")
        if isinstance(detail, list):
            for item in detail:
                if not isinstance(item, Mapping):
                    continue
                if str(item.get("smartlockId", "")) != self._smartlock_id:
                    continue
                identifier = item.get("authId", item.get("id"))
                if identifier is not None:
                    external_id = str(identifier)
                    break
        return external_id, str(request_id) if request_id is not None else None

    @staticmethod
    def _external_id(raw: Mapping[str, object]) -> str:
        identifier = raw.get("authId", raw.get("id"))
        if identifier is None:
            raise ProviderCommunicationError("Nuki authorization response is invalid")
        return str(identifier)

    @staticmethod
    def _record_list(response: object, description: str) -> tuple[Mapping[str, object], ...]:
        if not isinstance(response, list) or not all(
            isinstance(item, Mapping) for item in response
        ):
            raise ProviderCommunicationError(f"{description} is invalid")
        return tuple(response)

    @staticmethod
    def _nuki_datetime(value: datetime) -> str:
        return value.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")

    @staticmethod
    def _parse_datetime(value: object) -> datetime | None:
        if value is None or value == "":
            return None
        if not isinstance(value, str):
            raise ProviderCommunicationError("Nuki timestamp is invalid")
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)
        except ValueError as err:
            raise ProviderCommunicationError("Nuki timestamp is invalid") from err

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
