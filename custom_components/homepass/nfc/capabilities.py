"""Merge boundary between NFC access and generic HomePASS Doors."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from homeassistant.core import Context

from ..models import LockEventOrigin


class AccessPointNfcCapability(Protocol):
    """Answer whether one Door may safely expose NFC access."""

    async def supports_nfc_access(self, access_point_id: UUID) -> bool:
        """Return true only when the Door has a working unlock command path."""


class AccessPointCommandDispatcher(Protocol):
    """Dispatch a Door operation through its configured control profile."""

    async def execute(
        self,
        access_point_id: UUID,
        operation: str,
        *,
        origin: LockEventOrigin,
        context: Context,
        person_id: UUID | None = None,
        person_name: str | None = None,
    ) -> object:
        """Operate one Door without exposing entity-domain assumptions to NFC."""


__all__ = [
    "AccessPointNfcCapability",
    "AccessPointCommandDispatcher",
]
