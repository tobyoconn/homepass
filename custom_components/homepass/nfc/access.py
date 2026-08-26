"""Policy-gated NFC access orchestration."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from homeassistant.const import SERVICE_LOCK, SERVICE_UNLOCK
from homeassistant.core import Context, HomeAssistant

from ..models import LockEventOrigin
from ..services import AccessPointService, AuthorizationService
from ..vault import CredentialVaultProtocol, VaultCredentialId
from .capabilities import AccessPointCommandDispatcher, AccessPointNfcCapability
from .repository import NfcAccessRepository
from .sessions import ExpiringTokenStore
from .sun import verify_encrypted_picc_sun

_LOGGER = logging.getLogger(__name__)

TAP_SESSION_TTL_SECONDS = 30


@dataclass(frozen=True, slots=True)
class _TapSession:
    public_id: str
    access_point_id: UUID
    counter: int | None
    test_mode: bool
    operation: str
    action: str


@dataclass(frozen=True, slots=True)
class NfcTapReady:
    tap_session: str
    door_name: str
    action: str


@dataclass(frozen=True, slots=True)
class NfcAccessResult:
    allowed: bool
    door_name: str
    message: str
    test_mode: bool = False
    action: str = "unlock"


class NfcAccessService:
    """Bind a genuine tag tap, passkey identity, policy, and one Door."""

    def __init__(
        self,
        hass: HomeAssistant,
        repository: NfcAccessRepository,
        vault: CredentialVaultProtocol,
        authorization: AuthorizationService,
        access_points: AccessPointService,
        capabilities: AccessPointNfcCapability,
        command_dispatcher: AccessPointCommandDispatcher,
    ) -> None:
        self._hass = hass
        self._repository = repository
        self._vault = vault
        self._authorization = authorization
        self._access_points = access_points
        self._capabilities = capabilities
        self._command_dispatcher = command_dispatcher
        self._taps = ExpiringTokenStore[_TapSession](ttl=timedelta(seconds=TAP_SESSION_TTL_SECONDS))

    async def begin_tap(self, *, public_id: str, encrypted_picc: str, mac: str) -> NfcTapReady:
        tag = await self._repository.get_tag(public_id)
        if not tag.enabled:
            raise ValueError("This NFC tag is disabled")
        if not await self._capabilities.supports_nfc_access(tag.access_point_id):
            raise ValueError("This Door does not currently support NFC access")
        meta_key = bytes.fromhex(
            await self._vault.retrieve(VaultCredentialId.from_string(tag.meta_key_credential_id))
        )
        file_key = bytes.fromhex(
            await self._vault.retrieve(VaultCredentialId.from_string(tag.file_key_credential_id))
        )
        message = verify_encrypted_picc_sun(
            encrypted_picc_hex=encrypted_picc,
            mac_hex=mac,
            meta_read_key=meta_key,
            file_read_key=file_key,
            expected_uid_hex=tag.uid_hex,
        )
        await self._repository.claim_counter(public_id, message.counter)
        target = await self._access_points.get_target(tag.access_point_id)
        operation, action = await self._operation_for_target(tag.access_point_id)
        token = self._taps.issue(
            _TapSession(
                public_id,
                tag.access_point_id,
                message.counter,
                False,
                operation,
                action,
            )
        )
        return NfcTapReady(token, target.access_point.display_name, action)

    async def begin_test_tap(self, *, raw_token: str) -> NfcTapReady:
        """Begin a passkey challenge from a revocable static NTAG216 test URL."""
        tag = await self._repository.get_active_test_tag(raw_token)
        if not await self._capabilities.supports_nfc_access(tag.access_point_id):
            raise ValueError("This Door does not currently support NFC access")
        target = await self._access_points.get_target(tag.access_point_id)
        operation, action = await self._operation_for_target(tag.access_point_id)
        token = self._taps.issue(
            _TapSession(
                tag.token_hash,
                tag.access_point_id,
                None,
                True,
                operation,
                action,
            )
        )
        return NfcTapReady(token, target.access_point.display_name, action)

    def validate_tap_session(self, tap_session: str) -> None:
        """Fail before passkey verification when a tap session is absent or expired."""
        self._taps.peek(tap_session)

    async def operate(self, *, tap_session: str, person_id: UUID) -> NfcAccessResult:
        """Authorize a tap and perform its state-bound Door operation."""
        tap = self._taps.consume(tap_session)
        now = datetime.now(UTC)
        if tap.test_mode:
            if not await self._repository.test_tag_hash_is_active(
                tap.public_id, tap.access_point_id
            ):
                target = await self._access_points.get_target(tap.access_point_id)
                await self._audit(now, "denied", tap, person_id, "test_tag_inactive")
                return NfcAccessResult(
                    False,
                    target.access_point.display_name,
                    "This NTAG216 test tag has expired or been revoked.",
                    True,
                    tap.action,
                )
            relationship = await self._authorization.resolve_person_for_access_point(
                person_id=person_id,
                access_point_id=tap.access_point_id,
                instant_utc=now,
            )
        else:
            if not await self._repository.has_access_grant(person_id, tap.access_point_id):
                target = await self._access_points.get_target(tap.access_point_id)
                await self._audit(now, "denied", tap, person_id, "no_nfc_access_grant")
                return NfcAccessResult(
                    False,
                    target.access_point.display_name,
                    "Your HomePASS access is not active for this door right now.",
                    action=tap.action,
                )
            relationship = await self._authorization.resolve_person_for_access_point_with_nfc_grant(
                person_id=person_id,
                access_point_id=tap.access_point_id,
                instant_utc=now,
            )
        if not relationship.decision.allowed:
            await self._audit(now, "denied", tap, person_id, relationship.decision.value)
            return NfcAccessResult(
                False,
                relationship.access_point.display_name,
                "Your HomePASS access is not active for this door right now.",
                tap.test_mode,
                tap.action,
            )

        if not await self._capabilities.supports_nfc_access(tap.access_point_id):
            await self._audit(now, "failed", tap, person_id, "nfc_capability_unavailable")
            return NfcAccessResult(
                False,
                relationship.access_point.display_name,
                "This door cannot be operated remotely right now.",
                tap.test_mode,
                tap.action,
            )

        target = await self._access_points.get_target(tap.access_point_id)
        try:
            await self._command_dispatcher.execute(
                tap.access_point_id,
                tap.operation,
                origin=LockEventOrigin.NFC_PASSKEY,
                context=Context(),
                person_id=relationship.person.person_id,
                person_name=relationship.person.display_name,
            )
        except BaseException:
            await self._audit(now, "failed", tap, person_id, "door_command_failed")
            raise
        await self._audit(now, "allowed", tap, person_id, "allowed")
        message = {
            "close": "Access approved. The door is closing.",
            "open": "Access approved. The door is opening.",
            "unlock": "Access approved. The door is unlocking.",
        }[tap.action]
        return NfcAccessResult(
            True,
            target.access_point.display_name,
            message,
            tap.test_mode,
            tap.action,
        )

    async def _operation_for_target(self, access_point_id: UUID) -> tuple[str, str]:
        """Bind a predictable user-facing operation to the short-lived tap."""
        target = await self._access_points.get_target(access_point_id)
        if target.control_profile not in {"garage_cover", "garage_toggle"}:
            return SERVICE_UNLOCK, "unlock"
        state = await self._access_points.resolve_state(access_point_id)
        if state.door_state == "open" or state.lock_state in {
            "unlocked",
            "unlocking",
        }:
            return SERVICE_LOCK, "close"
        if state.door_state == "closed" or state.lock_state in {
            "locked",
            "locking",
        }:
            return SERVICE_UNLOCK, "open"
        raise ValueError("This roller Door's current position is unavailable")

    async def _audit(
        self, now: datetime, outcome: str, tap: _TapSession, person_id: UUID, reason: str
    ) -> None:
        try:
            await self._repository.append_audit(
                occurred_at=now,
                outcome=outcome,
                access_point_id=str(tap.access_point_id),
                person_id=str(person_id),
                reason=reason,
                counter=tap.counter,
                test_mode=tap.test_mode,
            )
            self._hass.bus.async_fire(
                "homepass_nfc_access_attempt",
                {
                    "outcome": outcome,
                    "access_point_id": str(tap.access_point_id),
                    "person_id": str(person_id),
                    "reason": reason,
                    "test_mode": tap.test_mode,
                },
            )
        except Exception:  # noqa: BLE001 - audit cannot change the physical outcome
            _LOGGER.error("An NFC access outcome could not be recorded")


__all__ = [
    "NfcAccessResult",
    "NfcAccessService",
    "NfcTapReady",
    "TAP_SESSION_TTL_SECONDS",
]
