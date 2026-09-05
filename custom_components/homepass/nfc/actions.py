"""Administrator actions for passkey enrollment and NTAG 424 preparation."""

from __future__ import annotations

import asyncio
import secrets
from base64 import b64encode
from datetime import timedelta
from typing import cast
from uuid import UUID

import qrcode
import qrcode.image.svg
import voluptuous as vol
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
    callback,
)
from homeassistant.exceptions import ServiceValidationError, Unauthorized

from ..exceptions import HomePASSError
from ..const import (
    ATTR_ACCESS_POINT_IDS,
    ATTR_PERSON_ID,
    DOMAIN,
    SERVICE_CREATE_NFC_ENROLLMENT,
    SERVICE_CREATE_NFC_TEST_TAG,
    SERVICE_CONFIRM_NFC_TAG_PROTECTION,
    SERVICE_DELETE_NFC_TAG,
    SERVICE_GET_NFC_TEST_TAG_STATUS,
    SERVICE_LIST_NFC_TAGS,
    SERVICE_PREPARE_NFC_TAG,
    SERVICE_PREPARE_NFC_TAG_PROTECTION,
    SERVICE_REINSTATE_NFC_TAG,
    SERVICE_REVOKE_NFC_TAG,
    SERVICE_REVOKE_NFC_TEST_TAG,
    SERVICE_UPDATE_NFC_ACCESS,
)
from ..services import AccessPointService, PersonService
from ..vault import CredentialVaultProtocol, VaultCredentialId, VaultError
from .capabilities import AccessPointNfcCapability
from .models import EnrollmentInvite, NfcTag, NfcTestTag, utcnow
from .repository import NfcAccessRepository, hash_token
from .webauthn_service import HomePassWebAuthnService

SERVICE_GET_NFC_ENROLLMENT_STATUS = "get_nfc_enrollment_status"
SERVICE_LIST_NFC_ENROLLMENT_STATUSES = "list_nfc_enrollment_statuses"
SERVICE_REVOKE_NFC_ENROLLMENT = "revoke_nfc_enrollment"


async def _require_admin(hass: HomeAssistant, call: ServiceCall) -> None:
    if call.context.user_id is None:
        raise Unauthorized(context=call.context)
    user = await hass.auth.async_get_user(call.context.user_id)
    if user is None or not user.is_admin:
        raise Unauthorized(context=call.context)


def _aes_key(value: object | None) -> bytes:
    if value is None:
        return secrets.token_bytes(16)
    try:
        result = bytes.fromhex(str(value))
    except ValueError as err:
        raise ServiceValidationError("NTAG keys must be hexadecimal") from err
    if len(result) != 16:
        raise ServiceValidationError("NTAG keys must contain 16 bytes")
    return result


def _qr_code_data_uri(value: str) -> str:
    """Return a self-contained, scanner-friendly SVG QR code."""
    qr = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=4,
        image_factory=qrcode.image.svg.SvgPathFillImage,
    )
    qr.add_data(value)
    qr.make(fit=True)
    svg = qr.make_image().to_string()
    return f"data:image/svg+xml;base64,{b64encode(svg).decode('ascii')}"


@callback
def async_register_nfc_actions(
    hass: HomeAssistant,
    repository: NfcAccessRepository,
    webauthn: HomePassWebAuthnService,
    people: PersonService,
    access_points: AccessPointService,
    vault: CredentialVaultProtocol,
    capabilities: AccessPointNfcCapability,
) -> None:
    """Register authenticated administrator-only preparation actions."""

    async def create_enrollment(call: ServiceCall) -> ServiceResponse:
        await _require_admin(hass, call)
        try:
            person = await people.get_person(UUID(call.data["person_id"]))
        except (TypeError, ValueError) as err:
            raise ServiceValidationError("HomePASS User is invalid") from err
        token = secrets.token_urlsafe(32)
        now = utcnow()
        invite = EnrollmentInvite(
            hash_token(token),
            person.person_id,
            person.display_name,
            now + timedelta(hours=int(call.data["expires_in_hours"])),
            None,
            now,
        )
        await repository.create_invite(invite)
        enrollment_url = f"{webauthn.public_origin}/api/homepass/nfc/enroll/{token}"
        return cast(
            ServiceResponse,
            {
                "enrollment_url": enrollment_url,
                "qr_code": _qr_code_data_uri(enrollment_url),
                "expires_at": invite.expires_at.isoformat(),
            },
        )

    async def _enrollment_status(person_id: UUID) -> dict[str, object]:
        credentials = await repository.list_credentials_for_person(person_id)
        grants = await repository.list_access_grants_for_person(person_id)
        return {
            "person_id": str(person_id),
            "enrolled": bool(credentials),
            "credential_count": len(credentials),
            "access_count": len(grants),
            "access_point_ids": [str(grant.access_point_id) for grant in grants],
            "passkeys": [
                {
                    "device_type": credential.device_type,
                    "backed_up": credential.backed_up,
                    "created_at": credential.created_at.isoformat(),
                }
                for credential in credentials
            ],
        }

    async def get_enrollment_status(call: ServiceCall) -> ServiceResponse:
        await _require_admin(hass, call)
        try:
            person_id = UUID(call.data[ATTR_PERSON_ID])
            await people.get_person(person_id)
        except (TypeError, ValueError) as err:
            raise ServiceValidationError("HomePASS User is invalid") from err
        return cast(ServiceResponse, await _enrollment_status(person_id))

    async def list_enrollment_statuses(call: ServiceCall) -> ServiceResponse:
        """Return every User's NFC summary in one frontend round trip."""
        await _require_admin(hass, call)
        people_list = await people.list_people()
        statuses = await asyncio.gather(
            *(_enrollment_status(person.person_id) for person in people_list)
        )
        return cast(ServiceResponse, {"statuses": list(statuses)})

    async def list_tags(call: ServiceCall) -> ServiceResponse:
        """List non-secret physical tag identifiers registered to one Door."""
        await _require_admin(hass, call)
        try:
            access_point_id = UUID(call.data["access_point_id"])
            await access_points.get_target(access_point_id)
            tags = await repository.list_tags_for_access_point(access_point_id)
        except (HomePASSError, TypeError, ValueError) as err:
            raise ServiceValidationError("HomePASS Door is invalid") from err
        return cast(
            ServiceResponse,
            {
                "access_point_id": str(access_point_id),
                "tags": [
                    {
                        "public_id": tag.public_id,
                        "uid_hex": tag.uid_hex,
                        "enabled": tag.enabled,
                        "last_counter": tag.last_counter,
                        "created_at": tag.created_at.isoformat(),
                        "write_protected": tag.write_protected,
                        "protection_prepared": tag.admin_key_credential_id is not None,
                    }
                    for tag in tags
                ],
            },
        )

    async def revoke_tag(call: ServiceCall) -> ServiceResponse:
        """Temporarily disable one tag registered to one Door."""
        await _require_admin(hass, call)
        try:
            access_point_id = UUID(call.data["access_point_id"])
            await access_points.get_target(access_point_id)
            tag = await repository.revoke_tag(str(call.data["public_id"]), access_point_id)
        except (HomePASSError, TypeError, ValueError) as err:
            raise ServiceValidationError("HomePASS could not revoke this NFC tag") from err
        return cast(
            ServiceResponse,
            {
                "access_point_id": str(access_point_id),
                "public_id": tag.public_id,
                "uid_hex": tag.uid_hex,
                "revoked": True,
            },
        )

    async def reinstate_tag(call: ServiceCall) -> ServiceResponse:
        """Re-enable one temporarily disabled tag registered to one Door."""
        await _require_admin(hass, call)
        try:
            access_point_id = UUID(call.data["access_point_id"])
            await access_points.get_target(access_point_id)
            tag = await repository.reinstate_tag(str(call.data["public_id"]), access_point_id)
        except (HomePASSError, TypeError, ValueError) as err:
            raise ServiceValidationError("HomePASS could not reinstate this NFC tag") from err
        return cast(
            ServiceResponse,
            {
                "access_point_id": str(access_point_id),
                "public_id": tag.public_id,
                "uid_hex": tag.uid_hex,
                "enabled": True,
            },
        )

    async def delete_tag(call: ServiceCall) -> ServiceResponse:
        """Permanently delete one tag registration from HomePASS."""
        await _require_admin(hass, call)
        try:
            access_point_id = UUID(call.data["access_point_id"])
            await access_points.get_target(access_point_id)
            public_id = str(call.data["public_id"])
            tag = await repository.get_tag(public_id)
            if tag is None or tag.access_point_id != access_point_id:
                raise ValueError("NFC tag is not registered to this Door")
            for credential_id in (
                tag.meta_key_credential_id,
                tag.file_key_credential_id,
                tag.admin_key_credential_id,
            ):
                if credential_id is None:
                    continue
                stored_id = VaultCredentialId.from_string(credential_id)
                if await vault.exists(stored_id):
                    await vault.delete(stored_id)
            await repository.delete_tag(public_id, access_point_id)
        except (HomePASSError, TypeError, ValueError, VaultError) as err:
            raise ServiceValidationError("HomePASS could not delete this NFC tag") from err
        return cast(
            ServiceResponse,
            {
                "access_point_id": str(access_point_id),
                "public_id": tag.public_id,
                "uid_hex": tag.uid_hex,
                "deleted": True,
            },
        )

    async def create_test_tag(call: ServiceCall) -> ServiceResponse:
        """Create a revocable static URL for temporary NTAG216 testing."""
        await _require_admin(hass, call)
        try:
            access_point_id = UUID(call.data["access_point_id"])
        except (TypeError, ValueError) as err:
            raise ServiceValidationError("HomePASS Door is invalid") from err
        if not await capabilities.supports_nfc_access(access_point_id):
            raise ServiceValidationError("This Door cannot currently be unlocked through HomePASS")
        raw_token = secrets.token_urlsafe(32)
        now = utcnow()
        tag = NfcTestTag(
            hash_token(raw_token),
            access_point_id,
            True,
            now + timedelta(hours=int(call.data["expires_in_hours"])),
            now,
        )
        await repository.replace_test_tag(tag)
        test_url = f"{webauthn.public_origin}/api/homepass/nfc/test/{raw_token}"
        return cast(
            ServiceResponse,
            {
                "active": True,
                "test_url": test_url,
                "qr_code": _qr_code_data_uri(test_url),
                "expires_at": tag.expires_at.isoformat(),
                "warning": ("NTAG216 test URLs can be copied. Revoke this tag after testing."),
            },
        )

    async def get_test_tag_status(call: ServiceCall) -> ServiceResponse:
        await _require_admin(hass, call)
        try:
            access_point_id = UUID(call.data["access_point_id"])
        except (TypeError, ValueError) as err:
            raise ServiceValidationError("HomePASS Door is invalid") from err
        tag = await repository.active_test_tag_for_access_point(access_point_id)
        return cast(
            ServiceResponse,
            {
                "active": tag is not None,
                "expires_at": None if tag is None else tag.expires_at.isoformat(),
            },
        )

    async def revoke_test_tag(call: ServiceCall) -> ServiceResponse:
        await _require_admin(hass, call)
        try:
            access_point_id = UUID(call.data["access_point_id"])
        except (TypeError, ValueError) as err:
            raise ServiceValidationError("HomePASS Door is invalid") from err
        revoked = await repository.revoke_test_tags_for_access_point(access_point_id)
        return cast(ServiceResponse, {"active": False, "revoked_records": revoked})

    async def revoke_enrollment(call: ServiceCall) -> ServiceResponse:
        await _require_admin(hass, call)
        try:
            person_id = UUID(call.data[ATTR_PERSON_ID])
            await people.get_person(person_id)
        except (TypeError, ValueError) as err:
            raise ServiceValidationError("HomePASS User is invalid") from err
        revoked_records = await repository.disable_credentials_for_person(person_id)
        return cast(
            ServiceResponse,
            {
                "person_id": str(person_id),
                "enrolled": False,
                "credential_count": 0,
                "access_count": 0,
                "access_point_ids": [],
                "revoked_records": revoked_records,
            },
        )

    async def prepare_tag(call: ServiceCall) -> ServiceResponse:
        await _require_admin(hass, call)
        try:
            uid_hex = str(call.data["uid_hex"]).upper()
            uid = bytes.fromhex(uid_hex)
            access_point_id = UUID(call.data["access_point_id"])
        except (TypeError, ValueError) as err:
            raise ServiceValidationError("NTAG UID or Door is invalid") from err
        if len(uid) != 7:
            raise ServiceValidationError("NTAG 424 UID must contain 7 bytes")
        if not await capabilities.supports_nfc_access(access_point_id):
            raise ServiceValidationError(
                "This Door has no compatible unlock capability; NFC cannot be enabled"
            )
        meta_key = _aes_key(call.data.get("meta_read_key"))
        file_key = _aes_key(call.data.get("file_read_key"))
        admin_key = secrets.token_bytes(16)
        meta_id = await vault.store(meta_key.hex().upper())
        try:
            file_id = await vault.store(file_key.hex().upper())
        except BaseException:
            await vault.delete(meta_id)
            raise
        try:
            admin_id = await vault.store(admin_key.hex().upper())
        except BaseException:
            await vault.delete(meta_id)
            await vault.delete(file_id)
            raise
        tag = NfcTag(
            secrets.token_urlsafe(12),
            uid_hex,
            access_point_id,
            str(meta_id),
            str(file_id),
            True,
            None,
            utcnow(),
            str(admin_id),
            False,
        )
        try:
            await repository.upsert_tag(tag)
        except BaseException:
            await vault.delete(meta_id)
            await vault.delete(file_id)
            await vault.delete(admin_id)
            raise
        return cast(
            ServiceResponse,
            {
                "public_id": tag.public_id,
                "ndef_url_template": (
                    f"{webauthn.public_origin}/api/homepass/nfc/t/{tag.public_id}"
                    "?e=00000000000000000000000000000000&c=0000000000000000"
                ),
                "meta_read_key": meta_key.hex().upper(),
                "file_read_key": file_key.hex().upper(),
                "admin_key": admin_key.hex().upper(),
                "profile": "encrypted_picc_zero_length_mac",
            },
        )

    async def prepare_tag_protection(call: ServiceCall) -> ServiceResponse:
        """Return a recoverable one-row conversion package for an existing tag."""
        await _require_admin(hass, call)
        try:
            access_point_id = UUID(call.data["access_point_id"])
            public_id = str(call.data["public_id"])
            tag = await repository.get_tag(public_id)
            if tag.access_point_id != access_point_id:
                raise ValueError("NFC tag is not registered to this Door")
            if tag.write_protected:
                raise ValueError("NFC tag is already write protected")
            meta_key = await vault.retrieve(
                VaultCredentialId.from_string(tag.meta_key_credential_id)
            )
            file_key = await vault.retrieve(
                VaultCredentialId.from_string(tag.file_key_credential_id)
            )
            if tag.admin_key_credential_id is None:
                admin_key = secrets.token_bytes(16).hex().upper()
                admin_id = await vault.store(admin_key)
                try:
                    tag = await repository.set_tag_admin_key(
                        public_id, access_point_id, str(admin_id)
                    )
                except BaseException:
                    await vault.delete(admin_id)
                    raise
            else:
                admin_key = await vault.retrieve(
                    VaultCredentialId.from_string(tag.admin_key_credential_id)
                )
        except (HomePASSError, TypeError, ValueError, VaultError) as err:
            raise ServiceValidationError(
                "HomePASS could not prepare rewrite protection for this NFC tag"
            ) from err
        return cast(
            ServiceResponse,
            {
                "public_id": tag.public_id,
                "uid_hex": tag.uid_hex,
                "ndef_url_template": (
                    f"{webauthn.public_origin}/api/homepass/nfc/t/{tag.public_id}"
                    "?e=00000000000000000000000000000000&c=0000000000000000"
                ),
                "current_admin_key": "00000000000000000000000000000000",
                "admin_key": admin_key,
                "file_read_key": file_key,
                "meta_read_key": meta_key,
            },
        )

    async def confirm_tag_protection(call: ServiceCall) -> ServiceResponse:
        """Record protection only after the administrator observed VERIFIED."""
        await _require_admin(hass, call)
        try:
            access_point_id = UUID(call.data["access_point_id"])
            tag = await repository.confirm_tag_write_protected(
                str(call.data["public_id"]), access_point_id
            )
        except (TypeError, ValueError) as err:
            raise ServiceValidationError(
                "HomePASS could not confirm rewrite protection for this NFC tag"
            ) from err
        return cast(
            ServiceResponse,
            {
                "public_id": tag.public_id,
                "uid_hex": tag.uid_hex,
                "write_protected": True,
            },
        )

    async def update_access(call: ServiceCall) -> ServiceResponse:
        """Replace explicit NFC Door assignments without creating PIN records."""
        await _require_admin(hass, call)
        try:
            person_id = UUID(call.data[ATTR_PERSON_ID])
            selected = tuple(UUID(value) for value in call.data[ATTR_ACCESS_POINT_IDS])
        except (TypeError, ValueError) as err:
            raise ServiceValidationError("HomePASS User or Door is invalid") from err
        if len(set(selected)) != len(selected):
            raise ServiceValidationError("NFC Door assignments must be unique")
        try:
            await people.get_person(person_id)
            for access_point_id in selected:
                target = await access_points.get_target(access_point_id)
                if not target.nfc_capable:
                    raise ServiceValidationError(
                        f"{target.access_point.display_name} does not support NFC access"
                    )
            grants = await repository.replace_access_grants_for_person(
                person_id, frozenset(selected)
            )
        except ServiceValidationError:
            raise
        except (HomePASSError, TypeError, ValueError) as err:
            raise ServiceValidationError(
                "HomePASS could not update NFC access assignments"
            ) from err
        return cast(
            ServiceResponse,
            {
                "person_id": str(person_id),
                "access_point_ids": [str(grant.access_point_id) for grant in grants],
            },
        )

    hass.services.async_register(
        DOMAIN,
        SERVICE_CREATE_NFC_ENROLLMENT,
        create_enrollment,
        schema=vol.Schema(
            {
                vol.Required("person_id"): str,
                vol.Optional("expires_in_hours", default=24): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=168)
                ),
            }
        ),
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_NFC_ENROLLMENT_STATUS,
        get_enrollment_status,
        schema=vol.Schema({vol.Required(ATTR_PERSON_ID): str}),
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_LIST_NFC_ENROLLMENT_STATUSES,
        list_enrollment_statuses,
        schema=vol.Schema({}),
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_REVOKE_NFC_ENROLLMENT,
        revoke_enrollment,
        schema=vol.Schema({vol.Required(ATTR_PERSON_ID): str}),
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_CREATE_NFC_TEST_TAG,
        create_test_tag,
        schema=vol.Schema(
            {
                vol.Required("access_point_id"): str,
                vol.Optional("expires_in_hours", default=168): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=720)
                ),
            }
        ),
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_NFC_TEST_TAG_STATUS,
        get_test_tag_status,
        schema=vol.Schema({vol.Required("access_point_id"): str}),
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_REVOKE_NFC_TEST_TAG,
        revoke_test_tag,
        schema=vol.Schema({vol.Required("access_point_id"): str}),
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_PREPARE_NFC_TAG,
        prepare_tag,
        schema=vol.Schema(
            {
                vol.Required("access_point_id"): str,
                vol.Required("uid_hex"): str,
                vol.Optional("meta_read_key"): str,
                vol.Optional("file_read_key"): str,
            }
        ),
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_PREPARE_NFC_TAG_PROTECTION,
        prepare_tag_protection,
        schema=vol.Schema({vol.Required("access_point_id"): str, vol.Required("public_id"): str}),
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_CONFIRM_NFC_TAG_PROTECTION,
        confirm_tag_protection,
        schema=vol.Schema({vol.Required("access_point_id"): str, vol.Required("public_id"): str}),
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_UPDATE_NFC_ACCESS,
        update_access,
        schema=vol.Schema(
            {vol.Required(ATTR_PERSON_ID): str, vol.Required(ATTR_ACCESS_POINT_IDS): [str]}
        ),
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_LIST_NFC_TAGS,
        list_tags,
        schema=vol.Schema({vol.Required("access_point_id"): str}),
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_REVOKE_NFC_TAG,
        revoke_tag,
        schema=vol.Schema({vol.Required("access_point_id"): str, vol.Required("public_id"): str}),
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_REINSTATE_NFC_TAG,
        reinstate_tag,
        schema=vol.Schema({vol.Required("access_point_id"): str, vol.Required("public_id"): str}),
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_DELETE_NFC_TAG,
        delete_tag,
        schema=vol.Schema({vol.Required("access_point_id"): str, vol.Required("public_id"): str}),
        supports_response=SupportsResponse.ONLY,
    )


@callback
def async_unregister_nfc_actions(hass: HomeAssistant) -> None:
    for service in (
        SERVICE_CREATE_NFC_ENROLLMENT,
        SERVICE_GET_NFC_ENROLLMENT_STATUS,
        SERVICE_LIST_NFC_ENROLLMENT_STATUSES,
        SERVICE_PREPARE_NFC_TAG,
        SERVICE_PREPARE_NFC_TAG_PROTECTION,
        SERVICE_CONFIRM_NFC_TAG_PROTECTION,
        SERVICE_CREATE_NFC_TEST_TAG,
        SERVICE_GET_NFC_TEST_TAG_STATUS,
        SERVICE_REVOKE_NFC_TEST_TAG,
        SERVICE_REVOKE_NFC_ENROLLMENT,
        SERVICE_UPDATE_NFC_ACCESS,
        SERVICE_LIST_NFC_TAGS,
        SERVICE_REVOKE_NFC_TAG,
        SERVICE_REINSTATE_NFC_TAG,
        SERVICE_DELETE_NFC_TAG,
    ):
        hass.services.async_remove(DOMAIN, service)


__all__ = ["async_register_nfc_actions", "async_unregister_nfc_actions"]
