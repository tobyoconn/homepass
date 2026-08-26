"""Tests for safe access-assignment failure responses."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock
from uuid import uuid4

from custom_components.homepass.access_management_actions import (
    async_register_access_management_actions,
    async_unregister_access_management_actions,
)
from custom_components.homepass.const import DOMAIN, SERVICE_UPDATE_ACCESS
from custom_components.homepass.exceptions import AccessUpdateError, AccessUpdateStage

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


async def test_update_access_reports_pin_incompatibility_without_secret(
    hass: HomeAssistant,
) -> None:
    """The UI receives an actionable code without a PIN or provider exception."""
    person_id = uuid4()
    access_point_id = uuid4()
    service = AsyncMock()
    service.update_access.side_effect = AccessUpdateError(
        operation_id=uuid4(),
        person_id=person_id,
        access_point_id=access_point_id,
        stage=AccessUpdateStage.REQUEST_VALIDATION,
        exception_type="CredentialCompatibilityError",
        sanitized_message="Saved PIN is incompatible with the selected access provider",
    )
    async_register_access_management_actions(hass, service)

    try:
        response = await hass.services.async_call(
            DOMAIN,
            SERVICE_UPDATE_ACCESS,
            {
                "person_id": str(person_id),
                "access_point_ids": [str(access_point_id)],
            },
            blocking=True,
            return_response=True,
        )
    finally:
        async_unregister_access_management_actions(hass)

    assert response == {
        "status": "failed",
        "reason": "pin_incompatible",
        "added": [],
        "removed": [],
        "unchanged": [],
        "access_points": [
            {"access_point_id": str(access_point_id), "status": "failed"}
        ],
    }
    assert "PIN" not in repr(response)
