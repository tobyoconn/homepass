"""Device-passkey enrollment and authentication ceremonies."""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from datetime import timedelta
from typing import Any
from urllib.parse import urlsplit
from uuid import UUID

from webauthn import (generate_authentication_options, generate_registration_options,
                      options_to_json, verify_authentication_response,
                      verify_registration_response)
from webauthn.helpers.structs import (AttestationConveyancePreference,
    AuthenticatorAttachment, AuthenticatorSelectionCriteria,
    PublicKeyCredentialDescriptor, ResidentKeyRequirement,
    UserVerificationRequirement)

from .models import PasskeyCredential, utcnow
from .repository import NfcAccessRepository
from .sessions import ExpiringTokenStore


def normalize_public_origin(public_origin: str) -> str:
    """Validate and normalize the single HTTPS origin used by passkeys."""
    parsed = urlsplit(public_origin.strip())
    try:
        port = parsed.port
    except ValueError as err:
        raise ValueError("HomePASS passkeys require a valid HTTPS port") from err
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.path not in ("", "/")
        or parsed.query
        or parsed.fragment
        or parsed.username is not None
        or parsed.password is not None
    ):
        raise ValueError("HomePASS passkeys require a bare HTTPS public origin")
    host = parsed.hostname.encode("idna").decode("ascii").lower()
    if ":" in host:
        host = f"[{host}]"
    port_suffix = "" if port in (None, 443) else f":{port}"
    return f"https://{host}{port_suffix}"


def _b64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _unb64url(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


@dataclass(frozen=True, slots=True)
class _RegistrationSession:
    invite_token: str
    person_id: UUID
    challenge: bytes


@dataclass(frozen=True, slots=True)
class _AuthenticationSession:
    tap_session: str
    challenge: bytes


@dataclass(frozen=True, slots=True)
class AuthenticatedPasskey:
    person_id: UUID
    tap_session: str


class HomePassWebAuthnService:
    """Run passkey ceremonies on one fixed HTTPS origin."""

    def __init__(self, repository: NfcAccessRepository, *, public_origin: str,
                 rp_name: str = "HomePASS") -> None:
        normalized_origin = normalize_public_origin(public_origin)
        parsed = urlsplit(normalized_origin)
        self._repository = repository
        self._origin = normalized_origin
        self._rp_id = parsed.hostname
        self._rp_name = rp_name
        self._registrations = ExpiringTokenStore[_RegistrationSession](ttl=timedelta(minutes=5))
        self._authentications = ExpiringTokenStore[_AuthenticationSession](ttl=timedelta(minutes=2))

    @property
    def public_origin(self) -> str:
        return self._origin

    async def begin_registration(
        self,
        invite_token: str,
        *,
        property_name: str,
    ) -> dict[str, Any]:
        invite = await self._repository.get_active_invite(invite_token)
        existing = await self._repository.list_credentials_for_person(invite.person_id)
        normalized_property_name = property_name.strip()
        passkey_name = (
            f"{normalized_property_name} Doors"
            if normalized_property_name
            else "HomePASS Doors"
        )
        options = generate_registration_options(
            rp_id=self._rp_id, rp_name=self._rp_name, user_id=invite.person_id.bytes,
            user_name=passkey_name, user_display_name=invite.person_name,
            timeout=60_000, attestation=AttestationConveyancePreference.NONE,
            authenticator_selection=AuthenticatorSelectionCriteria(
                authenticator_attachment=AuthenticatorAttachment.PLATFORM,
                resident_key=ResidentKeyRequirement.REQUIRED,
                user_verification=UserVerificationRequirement.REQUIRED),
            exclude_credentials=[PublicKeyCredentialDescriptor(id=_unb64url(item.credential_id))
                                 for item in existing])
        ceremony = self._registrations.issue(
            _RegistrationSession(invite_token, invite.person_id, options.challenge))
        return {"ceremony": ceremony, "publicKey": json.loads(options_to_json(options))}

    async def finish_registration(self, ceremony: str,
                                  response: dict[str, Any]) -> PasskeyCredential:
        session = self._registrations.consume(ceremony)
        verified = verify_registration_response(
            credential=response, expected_challenge=session.challenge,
            expected_rp_id=self._rp_id, expected_origin=self._origin,
            require_user_verification=True)
        credential = PasskeyCredential(
            _b64url(verified.credential_id), session.person_id,
            _b64url(verified.credential_public_key), verified.sign_count,
            getattr(verified.credential_device_type, "value", str(verified.credential_device_type)),
            verified.credential_backed_up, True, utcnow())
        await self._repository.complete_enrollment(session.invite_token, credential)
        return credential

    def begin_authentication(self, tap_session: str) -> dict[str, Any]:
        options = generate_authentication_options(
            rp_id=self._rp_id, timeout=30_000,
            user_verification=UserVerificationRequirement.REQUIRED)
        ceremony = self._authentications.issue(
            _AuthenticationSession(tap_session, options.challenge))
        return {"ceremony": ceremony, "publicKey": json.loads(options_to_json(options))}

    async def finish_authentication(self, ceremony: str,
                                    response: dict[str, Any]) -> AuthenticatedPasskey:
        session = self._authentications.consume(ceremony)
        credential = await self._repository.get_credential(str(response.get("id", "")))
        verified = verify_authentication_response(
            credential=response, expected_challenge=session.challenge,
            expected_rp_id=self._rp_id, expected_origin=self._origin,
            credential_public_key=_unb64url(credential.public_key),
            credential_current_sign_count=credential.sign_count,
            require_user_verification=True)
        await self._repository.update_sign_count(credential.credential_id,
                                                 verified.new_sign_count)
        return AuthenticatedPasskey(credential.person_id, session.tap_session)


__all__ = [
    "AuthenticatedPasskey",
    "HomePassWebAuthnService",
    "normalize_public_origin",
]
