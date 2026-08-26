"""Home Assistant Z-Wave JS adapter for the synchronization spike."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from enum import StrEnum
from typing import Any, cast

from homeassistant.components.zwave_js.helpers import async_get_node_from_entity_id
from homeassistant.core import HomeAssistant, ServiceResponse

from ..services.zwave_sync import (
    CreatedZWaveCredential,
    CreatedZWaveUser,
    DriverCommandResult,
    DriverCommandStatus,
    OperationDiagnostic,
    VerificationStatus,
    ZWaveDriverError,
    ZWaveInvalidTargetError,
    ZWaveUser,
)
from .base import (
    CredentialRemovalRequest,
    CredentialRemovalRequestResult,
    CredentialRemovalRequestStatus,
    CredentialRemovalResult,
    CredentialRemovalStatus,
    CredentialRemovalVerificationResult,
    CredentialRemovalVerificationStatus,
    CredentialReplacementRequest,
    CredentialReplacementRequestResult,
    CredentialReplacementRequestStatus,
    CredentialReplacementVerificationResult,
    CredentialReplacementVerificationStatus,
    DriverCapability,
)

ZWAVE_DOMAIN = "zwave_js"
SERVICE_DELETE_USER = "delete_user"
SERVICE_CLEAR_LOCK_USERCODE = "clear_lock_usercode"
SERVICE_GET_CREDENTIAL_CAPABILITIES = "get_credential_capabilities"
SERVICE_GET_LOCK_USERCODE = "get_lock_usercode"
SERVICE_GET_USERS = "get_users"
SERVICE_SET_LOCK_USERCODE = "set_lock_usercode"
SERVICE_SET_CREDENTIAL = "set_credential"
SERVICE_SET_USER = "set_user"

USER_CODE_READ_ATTEMPTS = 3
USER_CODE_READ_DELAY = 0.2
PIN_VERIFICATION_ATTEMPTS = 9
PIN_VERIFICATION_DELAY = 0.5
CREDENTIAL_REMOVAL_VERIFICATION_ATTEMPTS = 9
CREDENTIAL_REMOVAL_VERIFICATION_DELAY = 1.0
CREDENTIAL_REPLACEMENT_VERIFICATION_ATTEMPTS = 5
CREDENTIAL_REPLACEMENT_VERIFICATION_DELAY = 0.5


class _LockAccessPath(StrEnum):
    """Z-Wave access-control path selected for a lock."""

    USER_CODE_SLOTS = "user_code_slots"


class _SlotState(StrEnum):
    """Observed state of a numbered User Code slot."""

    OCCUPIED = "occupied"
    CLEAR = "clear"
    UNKNOWN = "unknown"


class _ReplacementSlotState(StrEnum):
    """Secret-free comparison of exact-slot readback with the candidate PIN."""

    CONFIRMED = "confirmed"
    DIFFERENT = "different"
    NOT_YET_CONFIRMED = "not_yet_confirmed"


class HomeAssistantZWaveLockDriver:
    """Call native Home Assistant Z-Wave JS actions for one lock target."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the adapter."""
        self._hass = hass
        self._lock_access_paths: dict[str, _LockAccessPath] = {}
        self._pending_user_code_slots: set[tuple[str, int]] = set()

    @property
    def capabilities(self) -> frozenset[DriverCapability]:
        """Return capabilities implemented by the Z-Wave lock adapter."""
        return frozenset(
            {
                DriverCapability.PIN,
                DriverCapability.READ_SLOTS,
                DriverCapability.CLEAR_SLOT,
                DriverCapability.REPLACE_PIN,
            }
        )

    def supports_pin_replacement(self, target_device: str) -> bool:
        """Require exact numbered-slot programming and readable PIN readback."""
        try:
            self._validate_target(target_device)
        except Exception:
            return False
        return self._hass.services.has_service(
            ZWAVE_DOMAIN, SERVICE_SET_LOCK_USERCODE
        ) and self.supports_exact_pin_readback(target_device)

    def supports_exact_pin_readback(self, target_device: str) -> bool:
        """Return whether exact numbered-slot PIN readback is available."""
        try:
            self._validate_target(target_device)
        except Exception:
            return False
        return self._hass.services.has_service(ZWAVE_DOMAIN, SERVICE_GET_LOCK_USERCODE)

    async def async_request_credential_replacement(
        self,
        request: CredentialReplacementRequest,
    ) -> CredentialReplacementRequestResult:
        """Overwrite one numbered User Code slot without clearing it first.

        Yale-style Z-Wave User Code slots are replaced by sending ``set_lock_usercode`` for
        the existing slot. Once dispatch begins, an exception is ambiguous because Home
        Assistant may already have forwarded the command to the device. An in-place
        overwrite may stop the previous PIN working before HomePASS finalization, so this
        driver does not promise continued physical validity of the previous PIN.
        """
        if not self._valid_replacement_request(request):
            return CredentialReplacementRequestResult(
                CredentialReplacementRequestStatus.REJECTED,
                "Credential replacement request was rejected",
            )
        if not self.supports_pin_replacement(request.target_device):
            return CredentialReplacementRequestResult(
                CredentialReplacementRequestStatus.UNSUPPORTED,
                "Credential replacement is not supported for this device",
            )
        try:
            await self._request_replace_user_code(
                request.target_device,
                request.slot,
                request.new_pin,
            )
        except Exception:
            return CredentialReplacementRequestResult(
                CredentialReplacementRequestStatus.AMBIGUOUS,
                "Credential replacement request outcome is unknown",
            )
        return CredentialReplacementRequestResult(CredentialReplacementRequestStatus.ACCEPTED)

    async def async_verify_credential_replacement(
        self,
        request: CredentialReplacementRequest,
    ) -> CredentialReplacementVerificationResult:
        """Poll exact readback briefly without programming or clearing any slot.

        A two-second window covers normal Home Assistant propagation while leaving longer
        retry scheduling to the future lifecycle coordinator. Missing or incomplete exact
        readback cannot distinguish a propagation delay from device limitations and is
        therefore reported as not yet confirmed.
        """
        if not self._valid_replacement_request(request):
            return CredentialReplacementVerificationResult(
                CredentialReplacementVerificationStatus.PERMANENT_FAILURE,
                "Credential replacement verification request is invalid",
            )
        if not self.supports_pin_replacement(request.target_device):
            return CredentialReplacementVerificationResult(
                CredentialReplacementVerificationStatus.UNSUPPORTED,
                "Credential replacement verification is not supported for this device",
            )
        observed: _ReplacementSlotState | None = None
        for attempt in range(CREDENTIAL_REPLACEMENT_VERIFICATION_ATTEMPTS):
            try:
                observed = await self._read_replacement_slot(
                    request.target_device,
                    request.slot,
                    request.new_pin,
                )
            except Exception:
                observed = None
            if observed is _ReplacementSlotState.CONFIRMED:
                return CredentialReplacementVerificationResult(
                    CredentialReplacementVerificationStatus.REPLACEMENT_CONFIRMED
                )
            if attempt + 1 < CREDENTIAL_REPLACEMENT_VERIFICATION_ATTEMPTS:
                await asyncio.sleep(CREDENTIAL_REPLACEMENT_VERIFICATION_DELAY)
        if observed is _ReplacementSlotState.DIFFERENT:
            return CredentialReplacementVerificationResult(
                CredentialReplacementVerificationStatus.PREVIOUS_OR_DIFFERENT_CREDENTIAL_PRESENT,
                "A different credential is still reported by the device",
            )
        if observed is _ReplacementSlotState.NOT_YET_CONFIRMED:
            return CredentialReplacementVerificationResult(
                CredentialReplacementVerificationStatus.REPLACEMENT_NOT_YET_CONFIRMED,
                "Credential replacement is not yet confirmed",
            )
        return CredentialReplacementVerificationResult(
            CredentialReplacementVerificationStatus.RETRYABLE_FAILURE,
            "Credential replacement could not be verified",
        )

    async def create_user(self, lock_entity_id: str, display_name: str) -> CreatedZWaveUser:
        """Create a named user in the first available Z-Wave user slot."""
        self._validate_target(lock_entity_id)
        if self._is_user_code_lock(lock_entity_id) or await self._detect_user_code_lock(
            lock_entity_id
        ):
            return await self._reserve_user_code_slot(lock_entity_id)

        service_data: dict[str, Any] = {
            "user_name": display_name,
            "active": True,
        }
        capabilities: Mapping[str, Any] = {}
        if self._hass.services.has_service(
            ZWAVE_DOMAIN,
            SERVICE_GET_CREDENTIAL_CAPABILITIES,
        ):
            capabilities = await self._call_response(
                SERVICE_GET_CREDENTIAL_CAPABILITIES,
                lock_entity_id,
                {},
            )
            if "general" in self._string_list(capabilities.get("supported_user_types")):
                service_data["user_type"] = "general"
            if "single" in self._string_list(capabilities.get("supported_credential_rules")):
                service_data["credential_rule"] = "single"
        try:
            response, diagnostic = await self._call_traced_response(
                SERVICE_SET_USER,
                lock_entity_id,
                service_data,
            )
        except ZWaveDriverError as err:
            if not self._requires_user_code_slots(err):
                raise
            self._lock_access_paths[lock_entity_id] = _LockAccessPath.USER_CODE_SLOTS
            return await self._reserve_user_code_slot(
                lock_entity_id,
                capabilities,
                cast(OperationDiagnostic, err.diagnostic),
            )
        try:
            user_id = self._positive_int(response.get("user_id"), "set_user response")
        except ZWaveDriverError as err:
            diagnostic["exception"] = f"{type(err).__name__}: {err}"
            raise ZWaveDriverError(str(err), diagnostic) from None
        return CreatedZWaveUser(user_id=user_id, diagnostic=diagnostic)

    async def set_pin(
        self,
        lock_entity_id: str,
        user_id: int,
        pin: str,
    ) -> CreatedZWaveCredential:
        """Create a PIN in the first available credential slot."""
        self._validate_target(lock_entity_id)
        pending_slot = (lock_entity_id, user_id)
        if pending_slot in self._pending_user_code_slots:
            self._pending_user_code_slots.remove(pending_slot)
            return await self._set_user_code(lock_entity_id, user_id, pin)
        response, diagnostic = await self._call_traced_response(
            SERVICE_SET_CREDENTIAL,
            lock_entity_id,
            {
                "user_id": user_id,
                "credential_type": "pin_code",
                "credential_data": pin,
            },
            secret=pin,
        )
        try:
            slot = response.get("credential_slot")
            credential_slot = (
                None if slot is None else self._positive_int(slot, "set_credential response")
            )
        except ZWaveDriverError as err:
            diagnostic["exception"] = f"{type(err).__name__}: {err}"
            raise ZWaveDriverError(str(err), diagnostic) from None
        return CreatedZWaveCredential(
            credential_slot=credential_slot,
            diagnostic=diagnostic,
        )

    async def provision_pin(
        self,
        lock_entity_id: str,
        pin: str,
        *,
        display_name: str | None = None,
        schedule: object | None = None,
        enabled: bool = True,
    ) -> CreatedZWaveCredential:
        """Provision a PIN through the numbered User Code slot path."""
        del display_name, schedule, enabled
        self._validate_target(lock_entity_id)
        capabilities = await self._call_response(
            SERVICE_GET_CREDENTIAL_CAPABILITIES,
            lock_entity_id,
            {},
        )
        users = await self._call_response(SERVICE_GET_USERS, lock_entity_id, {})
        reserved_slots = {
            slot for entity_id, slot in self._pending_user_code_slots if entity_id == lock_entity_id
        }
        slot = self._first_free_user_code_slot(capabilities, users, reserved_slots)
        self._lock_access_paths[lock_entity_id] = _LockAccessPath.USER_CODE_SLOTS
        return await self._set_user_code(lock_entity_id, slot, pin)

    async def verify_pin(
        self,
        lock_entity_id: str,
        slot: int,
        pin: str,
    ) -> VerificationStatus:
        """Verify an exact PIN without exposing or retaining either observed value."""
        self._validate_target(lock_entity_id)
        if not self.supports_exact_pin_readback(lock_entity_id):
            return "inconclusive"
        observed: _ReplacementSlotState | None = None
        for attempt in range(PIN_VERIFICATION_ATTEMPTS):
            try:
                observed = await self._read_replacement_slot(lock_entity_id, slot, pin)
            except Exception:
                observed = None
            if observed is _ReplacementSlotState.CONFIRMED:
                return "verified"
            if attempt + 1 < PIN_VERIFICATION_ATTEMPTS:
                await asyncio.sleep(PIN_VERIFICATION_DELAY)
        return "failed" if observed is _ReplacementSlotState.DIFFERENT else "inconclusive"

    async def remove_pin(self, lock_entity_id: str, slot: int) -> bool:
        """Clear and verify one exact numbered User Code assignment."""
        self._validate_target(lock_entity_id)
        return await self._clear_user_code(lock_entity_id, slot)

    async def async_remove_credential(
        self, request: CredentialRemovalRequest
    ) -> CredentialRemovalResult:
        """Clear and verify one credential without leaking adapter exceptions."""
        try:
            removed = await self.remove_pin(request.target_device, request.slot)
        except Exception:
            return CredentialRemovalResult(
                CredentialRemovalStatus.RETRYABLE_FAILURE,
                "Credential removal could not be confirmed",
            )
        if not removed:
            return CredentialRemovalResult(
                CredentialRemovalStatus.RETRYABLE_FAILURE,
                "Credential removal could not be confirmed",
            )
        return CredentialRemovalResult(CredentialRemovalStatus.SUCCESS)

    async def async_request_credential_removal(
        self, request: CredentialRemovalRequest
    ) -> CredentialRemovalRequestResult:
        """Issue one clear command without conflating it with readback."""
        try:
            self._validate_target(request.target_device)
        except Exception:
            return CredentialRemovalRequestResult(
                CredentialRemovalRequestStatus.REJECTED,
                "Credential removal request was rejected",
            )
        try:
            await self._request_clear_user_code(request.target_device, request.slot)
        except Exception:
            return CredentialRemovalRequestResult(
                CredentialRemovalRequestStatus.AMBIGUOUS,
                "Credential removal request outcome is unknown",
            )
        return CredentialRemovalRequestResult(CredentialRemovalRequestStatus.ACCEPTED)

    async def async_verify_credential_removed(
        self, request: CredentialRemovalRequest
    ) -> CredentialRemovalVerificationResult:
        """Poll readback for a bounded period without issuing another clear command."""
        removed: bool | None = None
        for attempt in range(CREDENTIAL_REMOVAL_VERIFICATION_ATTEMPTS):
            try:
                removed = await self.verify_pin_removed(request.target_device, request.slot)
            except Exception:
                removed = None
            if removed is True:
                return CredentialRemovalVerificationResult(
                    CredentialRemovalVerificationStatus.REMOVED
                )
            if attempt + 1 < CREDENTIAL_REMOVAL_VERIFICATION_ATTEMPTS:
                await asyncio.sleep(CREDENTIAL_REMOVAL_VERIFICATION_DELAY)
        if removed is False:
            return CredentialRemovalVerificationResult(
                CredentialRemovalVerificationStatus.STILL_PRESENT,
                "Credential is still reported by the device",
            )
        return CredentialRemovalVerificationResult(
            CredentialRemovalVerificationStatus.RETRYABLE_FAILURE,
            "Credential removal could not be verified",
        )

    async def request_remove_pin(self, lock_entity_id: str, slot: int) -> DriverCommandResult:
        """Issue one numbered User Code clear and return its acknowledgement."""
        self._validate_target(lock_entity_id)
        try:
            await self._request_clear_user_code(lock_entity_id, slot)
        except ZWaveDriverError:
            return DriverCommandResult(DriverCommandStatus.FAILED)
        return DriverCommandResult(DriverCommandStatus.ACCEPTED)

    async def verify_pin_removed(self, lock_entity_id: str, slot: int) -> bool | None:
        """Read one slot without issuing another physical clear command."""
        self._validate_target(lock_entity_id)
        state = await self._read_user_code_slot(lock_entity_id, slot)
        if state is _SlotState.CLEAR:
            return True
        if state is _SlotState.OCCUPIED:
            return False
        return None

    async def list_users(self, lock_entity_id: str) -> tuple[ZWaveUser, ...]:
        """Return non-secret user metadata from a lock."""
        self._validate_target(lock_entity_id)
        response = await self._call_response(SERVICE_GET_USERS, lock_entity_id, {})
        raw_users = response.get("users")
        if not isinstance(raw_users, list):
            raise ZWaveDriverError("Z-Wave JS get_users returned an invalid response")

        users: list[ZWaveUser] = []
        for raw_user in raw_users:
            if not isinstance(raw_user, Mapping):
                raise ZWaveDriverError("Z-Wave JS get_users returned an invalid response")
            user_id = self._positive_int(raw_user.get("user_id"), "get_users response")
            user_name = raw_user.get("user_name")
            if user_name is not None and not isinstance(user_name, str):
                raise ZWaveDriverError("Z-Wave JS get_users returned an invalid response")
            users.append(ZWaveUser(user_id=user_id, display_name=user_name))
        return tuple(users)

    async def delete_user(self, lock_entity_id: str, user_id: int) -> bool:
        """Delete exactly one requested Z-Wave user."""
        self._validate_target(lock_entity_id)
        if self._is_user_code_lock(lock_entity_id) or await self._detect_user_code_lock(
            lock_entity_id
        ):
            return await self._clear_user_code(lock_entity_id, user_id)
        try:
            await self._hass.services.async_call(
                ZWAVE_DOMAIN,
                SERVICE_DELETE_USER,
                {"user_id": user_id},
                target={"entity_id": lock_entity_id},
                blocking=True,
            )
        except Exception:
            raise ZWaveDriverError("Z-Wave JS delete_user action failed") from None
        return True

    def _validate_target(self, lock_entity_id: str) -> None:
        """Require an existing lock entity before calling Z-Wave JS."""
        if not lock_entity_id.startswith("lock.") or self._hass.states.get(lock_entity_id) is None:
            raise ZWaveInvalidTargetError("Target must be an existing lock entity")

    async def _call_response(
        self,
        service: str,
        lock_entity_id: str,
        service_data: dict[str, Any],
    ) -> Mapping[str, Any]:
        """Call a response-only Z-Wave action and extract the target result."""
        try:
            response = await self._hass.services.async_call(
                ZWAVE_DOMAIN,
                service,
                service_data,
                target={"entity_id": lock_entity_id},
                blocking=True,
                return_response=True,
            )
        except Exception:
            raise ZWaveDriverError(f"Z-Wave JS {service} action failed") from None
        return self._entity_response(response, lock_entity_id, service)

    async def _call_traced_response(
        self,
        service: str,
        lock_entity_id: str,
        service_data: dict[str, Any],
        *,
        secret: str | None = None,
    ) -> tuple[Mapping[str, Any], OperationDiagnostic]:
        """Call a native action and retain a complete PIN-safe diagnostic."""
        request = {
            "entity_id": lock_entity_id,
            **{
                key: self._sanitize(value, secret)
                for key, value in service_data.items()
                if key != "credential_data"
            },
        }
        try:
            response = await self._hass.services.async_call(
                ZWAVE_DOMAIN,
                service,
                service_data,
                target={"entity_id": lock_entity_id},
                blocking=True,
                return_response=True,
            )
        except Exception as err:
            diagnostic = OperationDiagnostic(
                stage=service,
                service=f"{ZWAVE_DOMAIN}.{service}",
                request=request,
                response=None,
                exception=self._redact(f"{type(err).__name__}: {err}", secret),
            )
            raise ZWaveDriverError(f"Z-Wave JS {service} action failed", diagnostic) from None

        diagnostic = OperationDiagnostic(
            stage=service,
            service=f"{ZWAVE_DOMAIN}.{service}",
            request=request,
            response=self._sanitize(response, secret),
            exception=None,
        )
        try:
            entity_response = self._entity_response(response, lock_entity_id, service)
        except ZWaveDriverError as err:
            diagnostic["exception"] = f"{type(err).__name__}: {err}"
            raise ZWaveDriverError(str(err), diagnostic) from None
        return entity_response, diagnostic

    @staticmethod
    def _entity_response(
        response: ServiceResponse,
        lock_entity_id: str,
        service: str,
    ) -> Mapping[str, Any]:
        """Parse the entity-keyed response returned by platform actions."""
        if not isinstance(response, Mapping):
            raise ZWaveDriverError(f"Z-Wave JS {service} returned an invalid response")
        raw_response = cast(Mapping[str, Any], response)
        entity_response = raw_response.get(lock_entity_id)
        if not isinstance(entity_response, Mapping):
            raise ZWaveDriverError(f"Z-Wave JS {service} returned an invalid response")
        return cast(Mapping[str, Any], entity_response)

    @staticmethod
    def _positive_int(value: object, source: str) -> int:
        """Parse a positive integer without accepting booleans."""
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ZWaveDriverError(f"Z-Wave JS {source} did not contain a valid identifier")
        return value

    @staticmethod
    def _string_list(value: object) -> tuple[str, ...]:
        """Return string capability values, ignoring unsupported response shapes."""
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            return ()
        return tuple(value)

    @staticmethod
    def _requires_user_code_slots(error: ZWaveDriverError) -> bool:
        """Detect Z-Wave error 322 for devices using coupled User Code slots."""
        if error.diagnostic is None or error.diagnostic["exception"] is None:
            return False
        exception = error.diagnostic["exception"].lower()
        return "322" in exception and ("stored together" in exception or "adduser" in exception)

    def _is_user_code_lock(self, lock_entity_id: str) -> bool:
        """Return whether a lock uses numbered User Code slots."""
        return self._lock_access_paths.get(lock_entity_id) is _LockAccessPath.USER_CODE_SLOTS

    async def _detect_user_code_lock(self, lock_entity_id: str) -> bool:
        """Detect the coupled User Code capability without sending person metadata."""
        try:
            node = async_get_node_from_entity_id(self._hass, lock_entity_id)
            capabilities = await node.access_control.get_user_capabilities_cached()
        except Exception:
            return False
        if capabilities.supports_users_without_credentials:
            return False
        self._lock_access_paths[lock_entity_id] = _LockAccessPath.USER_CODE_SLOTS
        return True

    async def _reserve_user_code_slot(
        self,
        lock_entity_id: str,
        capabilities: Mapping[str, Any] | None = None,
        diagnostic: OperationDiagnostic | None = None,
    ) -> CreatedZWaveUser:
        """Reserve the first free shared user/PIN slot for a User Code lock."""
        if capabilities is None:
            capabilities = await self._call_response(
                SERVICE_GET_CREDENTIAL_CAPABILITIES,
                lock_entity_id,
                {},
            )
        users = await self._call_response(SERVICE_GET_USERS, lock_entity_id, {})
        reserved_slots = {
            slot for entity_id, slot in self._pending_user_code_slots if entity_id == lock_entity_id
        }
        slot = self._first_free_user_code_slot(capabilities, users, reserved_slots)
        self._pending_user_code_slots.add((lock_entity_id, slot))
        if diagnostic is None:
            diagnostic = OperationDiagnostic(
                stage="select_usercode_slot",
                service=f"{ZWAVE_DOMAIN}.{SERVICE_GET_USERS}",
                request={"entity_id": lock_entity_id},
                response={
                    "lock_entity_id": lock_entity_id,
                    "slot": slot,
                    "verified": False,
                },
                exception=None,
            )
        return CreatedZWaveUser(user_id=slot, diagnostic=diagnostic)

    @classmethod
    def _first_free_user_code_slot(
        cls,
        capabilities: Mapping[str, Any],
        users_response: Mapping[str, Any],
        reserved_slots: set[int],
    ) -> int:
        """Return the first slot unused as both a user and PIN credential."""
        max_users = cls._positive_int(capabilities.get("max_users"), "capabilities")
        credential_types = capabilities.get("supported_credential_types")
        pin_capabilities = (
            credential_types.get("pin_code") if isinstance(credential_types, Mapping) else None
        )
        if not isinstance(pin_capabilities, Mapping):
            raise ZWaveDriverError("The lock did not report PIN credential capabilities")
        max_slots = cls._positive_int(pin_capabilities.get("num_slots"), "capabilities")
        users = users_response.get("users")
        if not isinstance(users, list):
            raise ZWaveDriverError("Z-Wave JS get_users returned an invalid response")
        occupied_slots = set(reserved_slots)
        for user in users:
            if not isinstance(user, Mapping):
                continue
            user_id = user.get("user_id")
            if isinstance(user_id, int) and not isinstance(user_id, bool):
                occupied_slots.add(user_id)
            credentials = user.get("credentials")
            if not isinstance(credentials, list):
                continue
            occupied_slots.update(
                slot
                for credential in credentials
                if isinstance(credential, Mapping)
                and credential.get("type") == "pin_code"
                and isinstance((slot := credential.get("slot")), int)
                and not isinstance(slot, bool)
            )
        slot = next(
            (
                value
                for value in range(1, min(max_users, max_slots) + 1)
                if value not in occupied_slots
            ),
            None,
        )
        if slot is None:
            raise ZWaveDriverError("The lock has no available User Code slots")
        return slot

    async def _set_user_code(
        self,
        lock_entity_id: str,
        slot: int,
        pin: str,
    ) -> CreatedZWaveCredential:
        """Program and verify one numbered User Code slot without retaining its PIN."""
        request: dict[str, object] = {
            "entity_id": lock_entity_id,
            "code_slot": slot,
        }

        diagnostic = OperationDiagnostic(
            stage=SERVICE_SET_LOCK_USERCODE,
            service=f"{ZWAVE_DOMAIN}.{SERVICE_SET_LOCK_USERCODE}",
            request=request,
            response=None,
            exception=None,
        )
        try:
            await self._hass.services.async_call(
                ZWAVE_DOMAIN,
                SERVICE_SET_LOCK_USERCODE,
                {"code_slot": slot, "usercode": pin},
                target={"entity_id": lock_entity_id},
                blocking=True,
            )
            verification_status = await self.verify_pin(lock_entity_id, slot, pin)
            diagnostic["response"] = {
                "lock_entity_id": lock_entity_id,
                "slot": slot,
                "verification_status": verification_status,
            }
        except Exception as err:
            diagnostic["exception"] = self._redact(
                f"{type(err).__name__}: {err}",
                pin,
            )
            raise ZWaveDriverError(
                "Z-Wave JS set_lock_usercode action failed",
                diagnostic,
            ) from None

        return CreatedZWaveCredential(
            credential_slot=slot,
            diagnostic=diagnostic,
            verification_status=verification_status,
        )

    @staticmethod
    def _user_code_slot_from_users(users_response: Mapping[str, Any], slot: int) -> _SlotState:
        """Read a numbered slot state from non-secret get_users metadata."""
        users = users_response.get("users")
        if not isinstance(users, list):
            return _SlotState.UNKNOWN
        for user in users:
            if not isinstance(user, Mapping):
                continue
            if user.get("user_id") == slot and user.get("active") is not False:
                return _SlotState.OCCUPIED
            credentials = user.get("credentials")
            if isinstance(credentials, list) and any(
                isinstance(credential, Mapping)
                and credential.get("type") == "pin_code"
                and credential.get("slot") == slot
                for credential in credentials
            ):
                return _SlotState.OCCUPIED
        return _SlotState.CLEAR

    @staticmethod
    def _user_code_slot_from_exact_read(response: Mapping[str, Any], slot: int) -> _SlotState:
        """Read occupancy without retaining the secret returned by Home Assistant."""
        raw_slot = response.get(str(slot))
        if not isinstance(raw_slot, Mapping):
            return _SlotState.UNKNOWN
        in_use = raw_slot.get("in_use")
        if not isinstance(in_use, bool):
            return _SlotState.UNKNOWN
        return _SlotState.OCCUPIED if in_use else _SlotState.CLEAR

    async def _read_user_code_slot(self, lock_entity_id: str, slot: int) -> _SlotState:
        """Prefer an exact slot read and fall back to non-secret user metadata."""
        if self._hass.services.has_service(ZWAVE_DOMAIN, SERVICE_GET_LOCK_USERCODE):
            try:
                response = await self._call_response(
                    SERVICE_GET_LOCK_USERCODE,
                    lock_entity_id,
                    {"code_slot": slot},
                )
            except ZWaveDriverError:
                pass
            else:
                state = self._user_code_slot_from_exact_read(response, slot)
                if state is not _SlotState.UNKNOWN:
                    return state
        try:
            users = await self._call_response(SERVICE_GET_USERS, lock_entity_id, {})
        except ZWaveDriverError:
            return _SlotState.UNKNOWN
        return self._user_code_slot_from_users(users, slot)

    async def _poll_user_code_slot(
        self,
        lock_entity_id: str,
        slot: int,
        *,
        expected: _SlotState,
    ) -> _SlotState:
        """Poll a slot briefly to allow lock state to propagate to Home Assistant."""
        state = _SlotState.UNKNOWN
        for attempt in range(USER_CODE_READ_ATTEMPTS):
            state = await self._read_user_code_slot(lock_entity_id, slot)
            if state is expected:
                return state
            if attempt + 1 < USER_CODE_READ_ATTEMPTS:
                await asyncio.sleep(USER_CODE_READ_DELAY)
        return state

    async def _clear_user_code(self, lock_entity_id: str, slot: int) -> bool:
        """Clear one numbered User Code slot and confirm its removal."""
        await self._request_clear_user_code(lock_entity_id, slot)
        state = await self._poll_user_code_slot(
            lock_entity_id,
            slot,
            expected=_SlotState.CLEAR,
        )
        return state is _SlotState.CLEAR

    async def _request_clear_user_code(self, lock_entity_id: str, slot: int) -> None:
        """Issue one numbered User Code clear without performing readback."""
        try:
            await self._hass.services.async_call(
                ZWAVE_DOMAIN,
                SERVICE_CLEAR_LOCK_USERCODE,
                {"code_slot": slot},
                target={"entity_id": lock_entity_id},
                blocking=True,
            )
        except Exception:
            raise ZWaveDriverError("Z-Wave JS clear_lock_usercode action failed") from None

    @staticmethod
    def _valid_replacement_request(request: CredentialReplacementRequest) -> bool:
        """Validate transient numeric PIN context without reflecting its values."""
        return (
            isinstance(request, CredentialReplacementRequest)
            and isinstance(request.target_device, str)
            and request.target_device.startswith("lock.")
            and isinstance(request.slot, int)
            and not isinstance(request.slot, bool)
            and request.slot > 0
            and isinstance(request.new_pin, str)
            and 4 <= len(request.new_pin) <= 10
            and request.new_pin.isascii()
            and request.new_pin.isdigit()
        )

    async def _request_replace_user_code(
        self,
        lock_entity_id: str,
        slot: int,
        pin: str,
    ) -> None:
        """Issue one in-place User Code overwrite without readback or clearing."""
        try:
            await self._hass.services.async_call(
                ZWAVE_DOMAIN,
                SERVICE_SET_LOCK_USERCODE,
                {"code_slot": slot, "usercode": pin},
                target={"entity_id": lock_entity_id},
                blocking=True,
            )
        except Exception:
            raise ZWaveDriverError("Z-Wave JS set_lock_usercode action failed") from None

    async def _read_replacement_slot(
        self,
        lock_entity_id: str,
        slot: int,
        expected_pin: str,
    ) -> _ReplacementSlotState:
        """Compare exact slot readback without returning or retaining its PIN."""
        response = await self._call_response(
            SERVICE_GET_LOCK_USERCODE,
            lock_entity_id,
            {"code_slot": slot},
        )
        raw_slot = response.get(str(slot))
        if not isinstance(raw_slot, Mapping):
            return _ReplacementSlotState.NOT_YET_CONFIRMED
        in_use = raw_slot.get("in_use")
        if in_use is not True:
            return _ReplacementSlotState.NOT_YET_CONFIRMED
        observed_pin = raw_slot.get("usercode")
        if not isinstance(observed_pin, str):
            return _ReplacementSlotState.NOT_YET_CONFIRMED
        if observed_pin == expected_pin:
            return _ReplacementSlotState.CONFIRMED
        return _ReplacementSlotState.DIFFERENT

    @classmethod
    def _sanitize(cls, value: object, secret: str | None) -> object:
        """Return JSON-compatible debug data with the invocation PIN redacted."""
        if isinstance(value, str):
            return cls._redact(value, secret)
        if isinstance(value, Mapping):
            return {str(key): cls._sanitize(item, secret) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [cls._sanitize(item, secret) for item in value]
        return value

    @staticmethod
    def _redact(value: str, secret: str | None) -> str:
        """Redact the PIN from exception and response strings."""
        return value.replace(secret, "<redacted>") if secret else value

    @staticmethod
    def validate_pin(_lock_entity_id: str, pin: str) -> None:
        """Validate the shared Yale/Z-Wave PIN shape before device I/O."""
        if not 4 <= len(pin) <= 10 or not pin.isascii() or not pin.isdigit():
            raise ValueError("PIN must contain 4 to 10 ASCII digits")
