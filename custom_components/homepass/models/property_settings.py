"""Immutable installation identity settings."""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from typing import TypedDict

PROPERTY_SETTINGS_SCHEMA_VERSION = 1
MAX_PROPERTY_NAME_LENGTH = 60


class PropertySettingsValidationError(ValueError):
    """A homeowner-correctable Property Settings validation failure."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.user_message = message


class PropertySettingsData(TypedDict):
    """Deterministic persisted Property Settings document."""

    schema_version: int
    property_name: str


def normalize_property_name(value: object) -> str:
    """Validate and normalize one optional homeowner-facing property name."""
    if not isinstance(value, str):
        raise PropertySettingsValidationError(
            "property_name_invalid",
            "Property Name must be text.",
        )
    normalized = value.strip()
    if any(unicodedata.category(character) == "Cc" for character in normalized):
        raise PropertySettingsValidationError(
            "property_name_control_characters",
            "Property Name cannot contain control characters.",
        )
    if len(normalized) > MAX_PROPERTY_NAME_LENGTH:
        raise PropertySettingsValidationError(
            "property_name_too_long",
            f"Property Name must be {MAX_PROPERTY_NAME_LENGTH} characters or fewer.",
        )
    return normalized


@dataclass(frozen=True, slots=True)
class PropertySettings:
    """Installation identity settings with an independent schema version."""

    property_name: str
    schema_version: int = PROPERTY_SETTINGS_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if (
            isinstance(self.schema_version, bool)
            or self.schema_version != PROPERTY_SETTINGS_SCHEMA_VERSION
        ):
            raise ValueError("Unsupported Property Settings schema version")
        object.__setattr__(self, "property_name", normalize_property_name(self.property_name))

    @classmethod
    def from_dict(cls, data: object) -> PropertySettings:
        """Deserialize one strict settings document."""
        if not isinstance(data, dict) or set(data) != {"schema_version", "property_name"}:
            raise ValueError("Property Settings contain unexpected fields")
        return cls(
            property_name=data["property_name"],
            schema_version=data["schema_version"],
        )

    def to_dict(self) -> PropertySettingsData:
        """Serialize deterministically."""
        return {
            "schema_version": self.schema_version,
            "property_name": self.property_name,
        }


__all__ = [
    "MAX_PROPERTY_NAME_LENGTH",
    "PROPERTY_SETTINGS_SCHEMA_VERSION",
    "PropertySettings",
    "PropertySettingsData",
    "PropertySettingsValidationError",
    "normalize_property_name",
]
