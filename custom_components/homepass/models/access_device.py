"""HomePASS-managed device associated with a logical Door."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Self, TypedDict
from uuid import UUID, uuid4


class AccessDeviceKind(StrEnum):
    """Supported accessory-device roles."""

    KEYPAD = "keypad"


class AccessDeviceIntegration(StrEnum):
    """Home Assistant integration that owns the physical device."""

    ZHA = "zha"
    ZIGBEE2MQTT = "zigbee2mqtt"


class KeypadOperation(StrEnum):
    """Door operations a keypad function may request."""

    NONE = "none"
    UNLOCK = "unlock"
    LOCK = "lock"


class AccessDeviceSetupState(StrEnum):
    """Truthful setup state for a managed accessory."""

    PENDING_HARDWARE_TEST = "pending_hardware_test"
    READY = "ready"


class AccessDeviceData(TypedDict):
    """JSON-compatible managed-device record."""

    id: str
    display_name: str
    kind: str
    integration: str
    home_assistant_device_id: str
    zigbee_ieee_address: str | None
    zigbee2mqtt_base_topic: str | None
    zigbee2mqtt_friendly_name: str | None
    access_point_id: str
    enabled: bool
    setup_state: str
    button_actions: dict[str, str]
    created_at: str
    updated_at: str


_KEYPAD_BUTTONS = frozenset(
    {
        "disarm",
        "arm_day_zones",
        "arm_night_zones",
        "arm_all_zones",
        "emergency",
    }
)


def default_keypad_button_actions() -> dict[str, KeypadOperation]:
    """Return conservative defaults pending observation of real ZHA events."""
    return {
        "disarm": KeypadOperation.UNLOCK,
        "arm_day_zones": KeypadOperation.NONE,
        "arm_night_zones": KeypadOperation.NONE,
        "arm_all_zones": KeypadOperation.LOCK,
        "emergency": KeypadOperation.NONE,
    }


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _normalize_datetime(value: datetime, field_name: str) -> datetime:
    if not isinstance(value, datetime):
        raise TypeError(f"AccessDevice {field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"AccessDevice {field_name} must be timezone-aware")
    return value.astimezone(UTC)


def _required_string(value: object, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"AccessDevice {field_name} must be a string")
    return value


def _normalize_zigbee_ieee_address(value: str) -> str:
    """Return one canonical Zigbee IEEE address without accepting partial identities."""
    compact = value.strip().lower().removeprefix("0x")
    compact = compact.replace(":", "").replace("-", "")
    if len(compact) != 16 or any(character not in "0123456789abcdef" for character in compact):
        raise ValueError("AccessDevice Zigbee IEEE address is invalid")
    return f"0x{compact}"


def _normalize_mqtt_topic_part(value: str, field_name: str, *, allow_slash: bool) -> str:
    """Validate a stored exact MQTT topic component."""
    normalized = value.strip().strip("/")
    if (
        not normalized
        or len(normalized) > 255
        or "+" in normalized
        or "#" in normalized
        or "\x00" in normalized
        or (not allow_slash and "/" in normalized)
    ):
        raise ValueError(f"AccessDevice {field_name} is invalid")
    return normalized


@dataclass(frozen=True, slots=True)
class AccessDevice:
    """An accessory that supplies an access method to one logical Door."""

    display_name: str
    home_assistant_device_id: str
    access_point_id: UUID
    id: UUID = field(default_factory=uuid4)
    kind: AccessDeviceKind = AccessDeviceKind.KEYPAD
    integration: AccessDeviceIntegration = AccessDeviceIntegration.ZHA
    zigbee_ieee_address: str | None = None
    zigbee2mqtt_base_topic: str | None = None
    zigbee2mqtt_friendly_name: str | None = None
    enabled: bool = True
    setup_state: AccessDeviceSetupState = AccessDeviceSetupState.PENDING_HARDWARE_TEST
    button_actions: Mapping[str, KeypadOperation] = field(
        default_factory=default_keypad_button_actions
    )
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)

    def __post_init__(self) -> None:
        if not isinstance(self.id, UUID):
            raise TypeError("AccessDevice id must be a UUID")
        if not isinstance(self.access_point_id, UUID):
            raise TypeError("AccessDevice access_point_id must be a UUID")
        if not isinstance(self.kind, AccessDeviceKind):
            raise TypeError("AccessDevice kind is invalid")
        if not isinstance(self.integration, AccessDeviceIntegration):
            raise TypeError("AccessDevice integration is invalid")
        if not isinstance(self.enabled, bool):
            raise TypeError("AccessDevice enabled must be a boolean")
        if not isinstance(self.setup_state, AccessDeviceSetupState):
            raise TypeError("AccessDevice setup_state is invalid")
        display_name = self.display_name.strip()
        if not display_name or len(display_name) > 80:
            raise ValueError("AccessDevice display_name must contain 1 to 80 characters")
        device_id = self.home_assistant_device_id.strip()
        if not device_id:
            raise ValueError("AccessDevice Home Assistant device identity is required")
        mqtt_binding = (
            self.zigbee_ieee_address,
            self.zigbee2mqtt_base_topic,
            self.zigbee2mqtt_friendly_name,
        )
        if self.integration is AccessDeviceIntegration.ZHA:
            if any(value is not None for value in mqtt_binding):
                raise ValueError("AccessDevice ZHA records cannot contain Zigbee2MQTT bindings")
        else:
            if not all(isinstance(value, str) for value in mqtt_binding):
                raise ValueError("AccessDevice Zigbee2MQTT binding is required")
            object.__setattr__(
                self,
                "zigbee_ieee_address",
                _normalize_zigbee_ieee_address(self.zigbee_ieee_address or ""),
            )
            object.__setattr__(
                self,
                "zigbee2mqtt_base_topic",
                _normalize_mqtt_topic_part(
                    self.zigbee2mqtt_base_topic or "",
                    "Zigbee2MQTT base topic",
                    allow_slash=True,
                ),
            )
            object.__setattr__(
                self,
                "zigbee2mqtt_friendly_name",
                _normalize_mqtt_topic_part(
                    self.zigbee2mqtt_friendly_name or "",
                    "Zigbee2MQTT friendly name",
                    allow_slash=True,
                ),
            )
        actions = dict(self.button_actions)
        if set(actions) != _KEYPAD_BUTTONS or any(
            not isinstance(operation, KeypadOperation) for operation in actions.values()
        ):
            raise ValueError("AccessDevice keypad button actions are invalid")
        created_at = _normalize_datetime(self.created_at, "created_at")
        updated_at = _normalize_datetime(self.updated_at, "updated_at")
        if updated_at < created_at:
            raise ValueError("AccessDevice updated_at must not be earlier than created_at")
        object.__setattr__(self, "display_name", display_name)
        object.__setattr__(self, "home_assistant_device_id", device_id)
        object.__setattr__(self, "button_actions", actions)
        object.__setattr__(self, "created_at", created_at)
        object.__setattr__(self, "updated_at", updated_at)

    @property
    def zigbee2mqtt_state_topic(self) -> str | None:
        """Return the exact state topic for an adopted Zigbee2MQTT device."""
        if (
            self.integration is not AccessDeviceIntegration.ZIGBEE2MQTT
            or self.zigbee2mqtt_base_topic is None
            or self.zigbee2mqtt_friendly_name is None
        ):
            return None
        return f"{self.zigbee2mqtt_base_topic}/{self.zigbee2mqtt_friendly_name}"

    def to_dict(self) -> AccessDeviceData:
        return {
            "id": str(self.id),
            "display_name": self.display_name,
            "kind": self.kind.value,
            "integration": self.integration.value,
            "home_assistant_device_id": self.home_assistant_device_id,
            "zigbee_ieee_address": self.zigbee_ieee_address,
            "zigbee2mqtt_base_topic": self.zigbee2mqtt_base_topic,
            "zigbee2mqtt_friendly_name": self.zigbee2mqtt_friendly_name,
            "access_point_id": str(self.access_point_id),
            "enabled": self.enabled,
            "setup_state": self.setup_state.value,
            "button_actions": {
                button: operation.value for button, operation in self.button_actions.items()
            },
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> Self:
        expected = set(AccessDeviceData.__required_keys__)
        if set(data) != expected:
            raise ValueError("AccessDevice fields are invalid")
        raw_actions = data["button_actions"]
        if not isinstance(raw_actions, Mapping):
            raise TypeError("AccessDevice button_actions must be an object")
        try:
            return cls(
                id=UUID(_required_string(data["id"], "id")),
                display_name=_required_string(data["display_name"], "display_name"),
                kind=AccessDeviceKind(_required_string(data["kind"], "kind")),
                integration=AccessDeviceIntegration(
                    _required_string(data["integration"], "integration")
                ),
                home_assistant_device_id=_required_string(
                    data["home_assistant_device_id"], "home_assistant_device_id"
                ),
                zigbee_ieee_address=_optional_string(
                    data["zigbee_ieee_address"], "zigbee_ieee_address"
                ),
                zigbee2mqtt_base_topic=_optional_string(
                    data["zigbee2mqtt_base_topic"], "zigbee2mqtt_base_topic"
                ),
                zigbee2mqtt_friendly_name=_optional_string(
                    data["zigbee2mqtt_friendly_name"], "zigbee2mqtt_friendly_name"
                ),
                access_point_id=UUID(_required_string(data["access_point_id"], "access_point_id")),
                enabled=data["enabled"] if isinstance(data["enabled"], bool) else _invalid_bool(),
                setup_state=AccessDeviceSetupState(
                    _required_string(data["setup_state"], "setup_state")
                ),
                button_actions={
                    _required_string(button, "button name"): KeypadOperation(
                        _required_string(operation, "button operation")
                    )
                    for button, operation in raw_actions.items()
                },
                created_at=datetime.fromisoformat(
                    _required_string(data["created_at"], "created_at")
                ),
                updated_at=datetime.fromisoformat(
                    _required_string(data["updated_at"], "updated_at")
                ),
            )
        except (TypeError, ValueError) as err:
            raise ValueError("AccessDevice record is invalid") from err


def _invalid_bool() -> bool:
    raise TypeError("AccessDevice enabled must be a boolean")


def _optional_string(value: object, field_name: str) -> str | None:
    if value is None:
        return None
    return _required_string(value, field_name)


__all__ = [
    "AccessDevice",
    "AccessDeviceData",
    "AccessDeviceIntegration",
    "AccessDeviceKind",
    "AccessDeviceSetupState",
    "KeypadOperation",
    "default_keypad_button_actions",
]
