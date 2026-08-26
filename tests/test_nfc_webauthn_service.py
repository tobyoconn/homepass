"""WebAuthn registration presentation behavior."""

from __future__ import annotations

import asyncio
import base64
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

from custom_components.homepass.nfc.webauthn_service import HomePassWebAuthnService


def _decode_base64url(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def test_registration_uses_property_doors_name_and_opaque_user_handle() -> None:
    """Apple Passwords sees the Property label while identity remains UUID bytes."""
    person_id = uuid4()
    repository = SimpleNamespace(
        get_active_invite=AsyncMock(
            return_value=SimpleNamespace(
                person_id=person_id,
                person_name="HomePASS Contributors",
            )
        ),
        list_credentials_for_person=AsyncMock(return_value=()),
    )
    service = HomePassWebAuthnService(
        repository,
        public_origin="https://example.ui.nabu.casa",
    )

    result = asyncio.run(
        service.begin_registration(
            "single-use-invite",
            property_name="Example Residence",
        )
    )

    user = result["publicKey"]["user"]
    assert user["name"] == "Example Residence Doors"
    assert user["displayName"] == "HomePASS Contributors"
    assert _decode_base64url(user["id"]) == person_id.bytes
    assert str(person_id) not in {user["name"], user["displayName"]}


def test_registration_uses_homepass_doors_when_property_name_is_blank() -> None:
    """An unset optional Property Name still produces a recognizable passkey label."""
    person_id = uuid4()
    repository = SimpleNamespace(
        get_active_invite=AsyncMock(
            return_value=SimpleNamespace(person_id=person_id, person_name="Example Resident")
        ),
        list_credentials_for_person=AsyncMock(return_value=()),
    )
    service = HomePassWebAuthnService(
        repository,
        public_origin="https://example.ui.nabu.casa",
    )

    result = asyncio.run(service.begin_registration("single-use-invite", property_name=""))

    assert result["publicKey"]["user"]["name"] == "HomePASS Doors"
