"""Application service for installation identity settings."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypedDict

from ..models.property_settings import PropertySettings
from ..repositories.property_settings import PropertySettingsRepository


class PropertySettingsPresentationData(TypedDict):
    """Homeowner-safe Property Settings values."""

    property_name: str


class PropertySettingsErrorData(TypedDict):
    """Structured homeowner-correctable validation error."""

    code: str
    message: str


class PropertySettingsResponseData(TypedDict):
    """Read/save action response without persistence internals."""

    settings: PropertySettingsPresentationData | None
    error: PropertySettingsErrorData | None


@dataclass(frozen=True, slots=True)
class PropertySettingsView:
    """Presentation-safe application result."""

    settings: PropertySettings

    def to_dict(self) -> PropertySettingsResponseData:
        return {
            "settings": {"property_name": self.settings.property_name},
            "error": None,
        }


class PropertySettingsService:
    """Own one-time initialization, validation, normalization, and persistence."""

    def __init__(
        self,
        repository: PropertySettingsRepository,
    ) -> None:
        self._repository = repository

    async def load(self) -> PropertySettingsView:
        """Load settings and initialize a blank optional name once."""
        settings = await self._repository.get()
        if settings is None:
            settings = await self._repository.initialize(PropertySettings(""))
        return PropertySettingsView(settings)

    async def save(self, raw_settings: object) -> PropertySettingsView:
        """Validate, normalize, and atomically save Property Settings."""
        if not isinstance(raw_settings, dict) or set(raw_settings) != {"property_name"}:
            raise ValueError("Property Settings request is invalid")
        settings = PropertySettings(raw_settings["property_name"])
        return PropertySettingsView(await self._repository.save(settings))


__all__ = [
    "PropertySettingsErrorData",
    "PropertySettingsPresentationData",
    "PropertySettingsResponseData",
    "PropertySettingsService",
    "PropertySettingsView",
]
