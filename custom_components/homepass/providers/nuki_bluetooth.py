"""Direct, account-free Nuki Smart Lock Ultra Bluetooth transport."""

from __future__ import annotations

import asyncio
import json
import logging
import secrets
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, TypeVar
from zoneinfo import ZoneInfo

import nacl.utils
from construct import Bytes, Int16ul, Struct  # type: ignore[import-untyped]
from homeassistant.components import bluetooth
from nacl.public import PrivateKey
from pyNukiBT import (  # type: ignore[import-untyped]
    NukiConst,
    NukiDevice,
    NukiErrorException,
)

from .base import (
    AuthorizationRequest,
    AuthorizationSchedule,
    ProviderAuditEvent,
    ProviderCommunicationError,
)
from .nuki_local import NukiLocalKeypadCode

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from homeassistant.core import HomeAssistant

_NUKI_ACTIONS = {
    1: "unlock",
    2: "lock",
    3: "unlatch",
    4: "lock_n_go",
    5: "lock_n_go_unlatch",
    6: "full_lock",
}
_NUKI_SOURCES = {0: "keypad", 1: "fingerprint"}
_MIN_DATE = datetime(2000, 1, 1)
_MAX_DATE = datetime(2099, 12, 31, 23, 59, 59)
_NUKI_CONNECT_TIMEOUT = 12.0
_NUKI_COMMAND_TIMEOUT = 20.0
_NUKI_DISCONNECT_TIMEOUT = 5.0
_LOGGER = logging.getLogger(__name__)


class NukiBluetoothPairingError(ProviderCommunicationError):
    """A secret-safe, actionable Nuki pairing failure."""

    def __init__(self, translation_key: str, stage: str) -> None:
        super().__init__(translation_key)
        self.translation_key = translation_key
        self.stage = stage


class NukiBluetoothOperationError(ProviderCommunicationError):
    """A secret-safe failure stage for an already-authorized Nuki connection."""

    def __init__(self, stage: str, error_type: str) -> None:
        super().__init__(f"Nuki Bluetooth operation failed during {stage}")
        self.stage = stage
        self.error_type = error_type


async def _disconnect_safely(device: _SecretSafeNukiDevice) -> None:
    """Bound Bluetooth cleanup so it never hides the original operation result."""
    try:
        async with asyncio.timeout(_NUKI_DISCONNECT_TIMEOUT):
            await device.disconnect()
    except TimeoutError:
        _LOGGER.warning("Nuki Bluetooth disconnect timed out during cleanup")
    except Exception as err:
        _LOGGER.warning(
            "Nuki Bluetooth disconnect failed during cleanup: error_type=%s",
            type(err).__name__,
        )


@dataclass(frozen=True, slots=True, repr=False)
class NukiBluetoothCredential:
    """Encrypted-at-rest pairing material for one Nuki Ultra."""

    auth_id: str
    nuki_public_key: str
    client_public_key: str
    client_private_key: str
    app_id: int
    security_pin: str

    def __post_init__(self) -> None:
        self._validate_hex("auth_id", self.auth_id, 4)
        self._validate_hex("nuki_public_key", self.nuki_public_key, 32)
        self._validate_hex("client_public_key", self.client_public_key, 32)
        self._validate_hex("client_private_key", self.client_private_key, 32)
        if isinstance(self.app_id, bool) or not 1 <= self.app_id <= 0xFFFFFFFF:
            raise ValueError("Nuki Bluetooth app ID is invalid")
        if len(self.security_pin) != 6 or not self.security_pin.isdecimal():
            raise ValueError("Nuki Ultra Security PIN must contain six digits")

    def serialize(self) -> str:
        """Serialize only for storage inside the encrypted HomePASS vault."""
        return json.dumps(asdict(self), separators=(",", ":"), sort_keys=True)

    def __repr__(self) -> str:
        return f"{type(self).__name__}(<redacted>)"

    @classmethod
    def deserialize(cls, raw: str) -> NukiBluetoothCredential:
        """Strictly decode pairing material retrieved from the encrypted vault."""
        try:
            payload = json.loads(raw)
        except (json.JSONDecodeError, TypeError) as err:
            raise ValueError("Nuki Bluetooth credential is invalid") from err
        if not isinstance(payload, dict) or set(payload) != {
            "app_id",
            "auth_id",
            "client_private_key",
            "client_public_key",
            "nuki_public_key",
            "security_pin",
        }:
            raise ValueError("Nuki Bluetooth credential is invalid")
        try:
            return cls(**payload)
        except (TypeError, ValueError) as err:
            raise ValueError("Nuki Bluetooth credential is invalid") from err

    @staticmethod
    def _validate_hex(name: str, value: str, byte_count: int) -> None:
        if not isinstance(value, str):
            raise ValueError(f"Nuki Bluetooth {name} is invalid")
        try:
            decoded = bytes.fromhex(value)
        except ValueError as err:
            raise ValueError(f"Nuki Bluetooth {name} is invalid") from err
        if len(decoded) != byte_count:
            raise ValueError(f"Nuki Bluetooth {name} is invalid")


_T = TypeVar("_T")


class _SecretSafeNukiDevice(NukiDevice):  # type: ignore[misc]
    """Suppress the upstream library's plaintext payload logging."""

    async def _send_encrypted_command(
        self,
        cmd: Any,
        payload: dict[str, object],
        aggregate_messages: list[Any] | None = None,
        expected_response: Any = None,
        response_retry: int | None = None,
        auth_id: bytes | None = None,
        characteristic: str | None = None,
    ) -> Any:
        auth_id = self._auth_id if auth_id is None else auth_id
        characteristic = self._const.BLE_CHAR if characteristic is None else characteristic
        unencrypted = self._const.NukiMessage.build(
            {"auth_id": auth_id, "command": cmd, "payload": payload}
        )
        nonce = nacl.utils.random(24)
        encrypted = self._box.encrypt(unencrypted, nonce)[24:]
        message = nonce + auth_id + len(encrypted).to_bytes(2, "little") + encrypted
        return await self._send_command(
            characteristic,
            message,
            aggregate_messages=aggregate_messages,
            expected_response=expected_response,
            response_retry=response_retry,
        )


def _install_keypad_message_types(device: _SecretSafeNukiDevice) -> None:
    """Complete the pinned library's Ultra keypad command table."""
    const = device._const
    commands = const.NukiCommand
    const.message_types.update(
        {
            commands.KEYPAD_CODE_ID: Struct(
                "code_id" / Int16ul,
                "date_created" / const.NukiDateTime,
            ),
            commands.REQUEST_KEYPAD_CODES: Struct(
                "offset" / Int16ul,
                "count" / Int16ul,
                "nonce" / Bytes(32),
                "security_pin" / const.NukiSecurityPinDataType,
            ),
            commands.KEYPAD_CODE_COUNT: Struct("count" / Int16ul),
            commands.KEYPAD_CODE: const.KeypadCodeEntry,
            commands.UPDATE_KEYPAD_CODE: const.UpdatedKeypadCode,
            commands.REMOVE_KEYPAD_CODE: Struct(
                "code_id" / Int16ul,
                "nonce" / Bytes(32),
                "security_pin" / const.NukiSecurityPinDataType,
            ),
        }
    )


class NukiBluetoothPairer:
    """Pair HomePASS directly with a Nuki Ultra over Home Assistant Bluetooth."""

    def __init__(self, hass: HomeAssistant) -> None:
        self._hass = hass

    async def pair(self, address: str, security_pin: str) -> NukiBluetoothCredential:
        normalized_address = address.strip().upper()
        if not normalized_address:
            raise ValueError("Choose a discovered Nuki lock")
        if len(security_pin) != 6 or not security_pin.isdecimal():
            raise ValueError("Nuki Ultra Security PIN must contain six digits")
        ble_device = bluetooth.async_ble_device_from_address(
            self._hass, normalized_address, connectable=True
        )
        if ble_device is None:
            raise NukiBluetoothPairingError(
                "nuki_pairing_connection_failed",
                "discover",
            )
        private_key = PrivateKey.generate()
        public_key = bytes(private_key.public_key)
        app_id = secrets.randbelow(0xFFFFFFFF) + 1
        device = _SecretSafeNukiDevice(
            normalized_address,
            b"\0" * 4,
            b"",
            public_key,
            bytes(private_key),
            app_id,
            "HomePASS",
            ble_device=ble_device,
            get_ble_device=self._get_ble_device,
        )
        try:
            try:
                await device.connect()
            except Exception as err:
                raise self._pairing_error(err, stage="connect") from err
            if device.device_type != NukiConst.NukiDeviceType.SMARTLOCK_ULTRA:
                raise NukiBluetoothPairingError(
                    "nuki_pairing_protocol_failed",
                    "identify",
                )
            try:
                result = await device.pair(int(security_pin))
            except Exception as err:
                raise self._pairing_error(err, stage="authorize") from err
        except ProviderCommunicationError:
            raise
        finally:
            await _disconnect_safely(device)
        return NukiBluetoothCredential(
            auth_id=bytes(result["auth_id"]).hex(),
            nuki_public_key=bytes(result["nuki_public_key"]).hex(),
            client_public_key=public_key.hex(),
            client_private_key=bytes(private_key).hex(),
            app_id=app_id,
            security_pin=security_pin,
        )

    def _get_ble_device(self, address: str) -> Any:
        return bluetooth.async_ble_device_from_address(
            self._hass, address, connectable=True
        )

    @staticmethod
    def _pairing_error(err: Exception, *, stage: str) -> NukiBluetoothPairingError:
        """Map upstream errors to safe UI guidance without logging credentials."""
        error_code = getattr(err, "error_code", None)
        command = getattr(err, "command", None)
        if isinstance(err, NukiErrorException):
            if error_code == NukiConst.ErrorCode.P_ERROR_NOT_PAIRING:
                translation_key = "nuki_pairing_not_enabled"
            elif error_code == NukiConst.ErrorCode.K_ERROR_BAD_PIN:
                translation_key = "nuki_pairing_bad_pin"
            elif error_code == NukiConst.ErrorCode.P_ERROR_MAX_USER:
                translation_key = "nuki_pairing_authorization_full"
            else:
                translation_key = "nuki_pairing_protocol_failed"
        elif isinstance(err, TimeoutError):
            translation_key = "nuki_pairing_timeout"
        else:
            translation_key = "nuki_pairing_connection_failed"
        _LOGGER.warning(
            "Nuki Bluetooth pairing failed at stage %s: failure=%s, "
            "error_type=%s, error_code=%s, command=%s",
            stage,
            translation_key,
            type(err).__name__,
            error_code,
            command,
        )
        return NukiBluetoothPairingError(translation_key, stage)


class NukiBluetoothTransport:
    """Operate keypad codes and audit logs directly on one paired Ultra."""

    def __init__(
        self,
        hass: HomeAssistant,
        address: str,
        credential: NukiBluetoothCredential,
    ) -> None:
        normalized_address = address.strip().upper()
        if not normalized_address:
            raise ValueError("Nuki Bluetooth address must not be empty")
        self._hass = hass
        self._address = normalized_address
        self._credential = credential
        self._time_zone = ZoneInfo(hass.config.time_zone)
        self._operation_lock = asyncio.Lock()

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}(address={self._address!r}, "
            "credential=<redacted>)"
        )

    async def add_keypad_code(self, request: AuthorizationRequest) -> str:
        async def operation(device: _SecretSafeNukiDevice) -> str:
            challenge = await self._challenge(device)
            response = await device._send_encrypted_command(
                device._const.NukiCommand.ADD_KEYPAD_CODE,
                self._keypad_payload(request, challenge.nonce),
                expected_response=device._const.NukiCommand.KEYPAD_CODE_ID,
            )
            code_id = int(response.code_id)
            if code_id < 1:
                raise ProviderCommunicationError("Nuki returned an invalid keypad code ID")
            return str(code_id)

        return await self._run("create keypad code", operation)

    async def update_keypad_code(
        self, external_id: str, request: AuthorizationRequest
    ) -> None:
        code_id = self._code_id(external_id)

        async def operation(device: _SecretSafeNukiDevice) -> None:
            challenge = await self._challenge(device)
            payload = self._keypad_payload(request, challenge.nonce)
            payload["code_id"] = code_id
            response = await device._send_encrypted_command(
                device._const.NukiCommand.UPDATE_KEYPAD_CODE,
                payload,
                expected_response=device._const.NukiCommand.STATUS,
            )
            self._require_completed(response)

        await self._run("update keypad code", operation)

    async def remove_keypad_code(self, external_id: str) -> None:
        code_id = self._code_id(external_id)

        async def operation(device: _SecretSafeNukiDevice) -> None:
            challenge = await self._challenge(device)
            response = await device._send_encrypted_command(
                device._const.NukiCommand.REMOVE_KEYPAD_CODE,
                {
                    "code_id": code_id,
                    "nonce": challenge.nonce,
                    "security_pin": int(self._credential.security_pin),
                },
                expected_response=device._const.NukiCommand.STATUS,
            )
            self._require_completed(response)

        await self._run("remove keypad code", operation)

    async def list_keypad_codes(self) -> tuple[NukiLocalKeypadCode, ...]:
        async def operation(
            device: _SecretSafeNukiDevice,
        ) -> tuple[NukiLocalKeypadCode, ...]:
            challenge = await self._challenge(device)
            await device._send_encrypted_command(
                device._const.NukiCommand.REQUEST_KEYPAD_CODES,
                {
                    "offset": 0,
                    "count": 200,
                    "nonce": challenge.nonce,
                    "security_pin": int(self._credential.security_pin),
                },
                aggregate_messages=[
                    device._const.NukiCommand.KEYPAD_CODE_COUNT,
                    device._const.NukiCommand.KEYPAD_CODE,
                ],
                expected_response=device._const.NukiCommand.STATUS,
            )
            return tuple(
                self._keypad_record(raw)
                for raw in device._messages
                if hasattr(raw, "code_id")
            )

        return await self._run("read keypad codes", operation)

    async def list_audit_events(self, *, limit: int) -> tuple[ProviderAuditEvent, ...]:
        async def operation(
            device: _SecretSafeNukiDevice,
        ) -> tuple[ProviderAuditEvent, ...]:
            records = await device.request_log_entries(
                int(self._credential.security_pin),
                sort_order=0x01,
                count=limit,
            )
            return tuple(self._audit_event(record) for record in records)

        return await self._run("read audit log", operation)

    async def _run(
        self,
        label: str,
        operation: Callable[[_SecretSafeNukiDevice], Awaitable[_T]],
    ) -> _T:
        async with self._operation_lock:
            device = self._device()
            try:
                try:
                    async with asyncio.timeout(_NUKI_CONNECT_TIMEOUT):
                        await device.connect()
                except Exception as err:
                    raise NukiBluetoothOperationError(
                        "connection", type(err).__name__
                    ) from err
                if device.device_type != NukiConst.NukiDeviceType.SMARTLOCK_ULTRA:
                    raise NukiBluetoothOperationError(
                        "device identification", "UnexpectedDeviceType"
                    )
                try:
                    _install_keypad_message_types(device)
                    async with asyncio.timeout(_NUKI_COMMAND_TIMEOUT):
                        return await operation(device)
                except ProviderCommunicationError:
                    raise
                except Exception as err:
                    raise NukiBluetoothOperationError(
                        f"authenticated command ({label})", type(err).__name__
                    ) from err
            finally:
                await _disconnect_safely(device)

    def _device(self) -> _SecretSafeNukiDevice:
        credential = self._credential
        ble_device = bluetooth.async_ble_device_from_address(
            self._hass, self._address, connectable=True
        )
        if ble_device is None:
            raise NukiBluetoothOperationError(
                "discovery", "ConnectableDeviceUnavailable"
            )
        device = _SecretSafeNukiDevice(
            self._address,
            bytes.fromhex(credential.auth_id),
            bytes.fromhex(credential.nuki_public_key),
            bytes.fromhex(credential.client_public_key),
            bytes.fromhex(credential.client_private_key),
            credential.app_id,
            "HomePASS",
            ble_device=ble_device,
            get_ble_device=lambda address: bluetooth.async_ble_device_from_address(
                self._hass, address, connectable=True
            ),
        )
        device.send_retry = 3
        device.response_retry = 2
        device.connection_timeout = 10
        device.command_response_timeout = 10
        return device

    async def _challenge(self, device: _SecretSafeNukiDevice) -> Any:
        return await device._send_encrypted_command(
            device._const.NukiCommand.REQUEST_DATA,
            {"command": device._const.NukiCommand.CHALLENGE},
            expected_response=device._const.NukiCommand.CHALLENGE,
        )

    def _keypad_payload(
        self, request: AuthorizationRequest, nonce: bytes
    ) -> dict[str, object]:
        schedule = request.schedule
        time_limited = bool(
            schedule.valid_from is not None
            or schedule.valid_until is not None
            or schedule.from_minute is not None
            or bool(schedule.weekdays)
        )
        return {
            "code": int(request.pin),
            "name": request.display_name,
            "enabled": int(request.enabled),
            "time_limited": int(time_limited),
            "allowed_from_date": self._local_naive(schedule.valid_from) or _MIN_DATE,
            "allowed_until_date": self._local_naive(schedule.valid_until) or _MAX_DATE,
            "allowed_weekdays": self._weekday_payload(schedule.weekdays),
            "allowed_from_time": self._time_payload(schedule.from_minute),
            "allowed_until_time": self._time_payload(schedule.until_minute),
            "nonce": nonce,
            "security_pin": int(self._credential.security_pin),
        }

    def _keypad_record(self, raw: Any) -> NukiLocalKeypadCode:
        return NukiLocalKeypadCode(
            external_id=str(int(raw.code_id)),
            display_name=str(raw.name).strip(),
            pin=str(int(raw.code)).zfill(6),
            enabled=bool(raw.enabled),
            schedule=self._schedule_from_raw(raw),
        )

    def _schedule_from_raw(self, raw: Any) -> AuthorizationSchedule:
        if not bool(raw.time_limited):
            return AuthorizationSchedule()
        from_minute = int(raw.allowed_from_time.hour) * 60 + int(
            raw.allowed_from_time.minute
        )
        until_minute = int(raw.allowed_until_time.hour) * 60 + int(
            raw.allowed_until_time.minute
        )
        weekdays = frozenset(
            day
            for day, name in enumerate(
                (
                    "monday",
                    "tuesday",
                    "wednesday",
                    "thursday",
                    "friday",
                    "saturday",
                    "sunday",
                ),
                start=1,
            )
            if bool(raw.allowed_weekdays[name])
        )
        return AuthorizationSchedule(
            valid_from=self._utc_datetime(raw.allowed_from_date, lower=True),
            valid_until=self._utc_datetime(raw.allowed_until_date, lower=False),
            weekdays=weekdays if from_minute != until_minute else frozenset(),
            from_minute=from_minute if from_minute != until_minute else None,
            until_minute=until_minute if from_minute != until_minute else None,
        )

    def _audit_event(self, raw: Any) -> ProviderAuditEvent:
        event_type = int(raw.type)
        data = raw.data
        is_keypad = event_type == 5
        source_value = int(data.source) if is_keypad else None
        completion = int(data.completion_status) if hasattr(data, "completion_status") else 0
        code_id = int(data.code_id) if is_keypad else 0
        auth_id = int.from_bytes(bytes(raw.auth_id), "little")
        occurred_at = raw.timestamp.replace(tzinfo=self._time_zone).astimezone(UTC)
        action_value = int(data.lock_action) if hasattr(data, "lock_action") else 0
        return ProviderAuditEvent(
            external_id=str(int(raw.index)),
            occurred_at=occurred_at,
            action=_NUKI_ACTIONS.get(action_value, str(action_value)),
            outcome="success" if completion == 0 else "failed",
            authorization_external_id=str(code_id or auth_id) if code_id or auth_id else None,
            authorization_name=str(raw.name).strip() or None,
            source=_NUKI_SOURCES.get(source_value, str(source_value))
            if source_value is not None
            else None,
        )

    @staticmethod
    def _weekday_payload(weekdays: frozenset[int]) -> dict[str, bool]:
        names = (
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
        )
        return {name: index in weekdays for index, name in enumerate(names, start=1)}

    @staticmethod
    def _time_payload(value: int | None) -> dict[str, int]:
        hour, minute = divmod(value or 0, 60)
        return {"hour": hour, "minute": minute}

    def _local_naive(self, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return value.astimezone(self._time_zone).replace(tzinfo=None)

    def _utc_datetime(self, value: datetime | None, *, lower: bool) -> datetime | None:
        if value is None:
            return None
        if lower and value <= _MIN_DATE:
            return None
        if not lower and value >= _MAX_DATE:
            return None
        return value.replace(tzinfo=self._time_zone).astimezone(UTC)

    @staticmethod
    def _code_id(value: str) -> int:
        if not value.isdecimal() or int(value) < 1 or int(value) > 0xFFFF:
            raise ValueError("Nuki keypad code identifier is invalid")
        return int(value)

    @staticmethod
    def _require_completed(response: Any) -> None:
        if int(response.status) not in {0, 1}:
            raise ProviderCommunicationError("Nuki did not accept the keypad operation")


__all__ = [
    "NukiBluetoothCredential",
    "NukiBluetoothPairer",
    "NukiBluetoothTransport",
]
