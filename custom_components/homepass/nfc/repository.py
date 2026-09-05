"""Isolated persistence for NFC tags, passkeys, invitations, and access audits."""

from __future__ import annotations

import asyncio
from copy import deepcopy
from datetime import datetime
from hashlib import sha256
from typing import Any, cast
from uuid import UUID

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .models import (
    EnrollmentInvite,
    NfcAccessGrant,
    NfcTag,
    NfcTestTag,
    PasskeyCredential,
    utcnow,
)

_STORAGE_KEY = "homepass.nfc_access"
_STORAGE_VERSION = 1
_MAX_AUDIT_RECORDS = 500


class NfcRepositoryError(ValueError):
    """Raised when NFC state fails a security invariant."""


def hash_token(token: str) -> str:
    return sha256(token.encode()).hexdigest()


def _empty() -> dict[str, Any]:
    return {
        "tags": {},
        "test_tags": {},
        "credentials": {},
        "invites": {},
        "access_grants": {},
        "audit": [],
    }


class NfcAccessRepository:
    """Serialize NFC mutations without changing HomePASS's policy schema."""

    def __init__(self, hass: HomeAssistant) -> None:
        self._store: Store[dict[str, Any]] = Store(hass, _STORAGE_VERSION, _STORAGE_KEY)
        self._lock = asyncio.Lock()
        self._data: dict[str, Any] | None = None

    async def initialize(self) -> None:
        async with self._lock:
            loaded = await self._store.async_load()
            self._data = _empty() if loaded is None else self._validate(loaded)

    def _require_data(self) -> dict[str, Any]:
        if self._data is None:
            raise NfcRepositoryError("NFC repository is not initialized")
        return self._data

    async def get_tag(self, public_id: str) -> NfcTag:
        async with self._lock:
            raw = self._require_data()["tags"].get(public_id)
            if not isinstance(raw, dict):
                raise NfcRepositoryError("NFC tag was not found")
            return NfcTag.from_dict(raw)

    async def upsert_tag(self, tag: NfcTag) -> None:
        async with self._lock:
            data = deepcopy(self._require_data())
            data["tags"][tag.public_id] = tag.to_dict()
            await self._store.async_save(data)
            self._data = data

    async def replace_test_tag(self, tag: NfcTestTag) -> None:
        """Replace any previous test tag for one Door with a new hashed token."""
        async with self._lock:
            data = deepcopy(self._require_data())
            for key, raw in tuple(data["test_tags"].items()):
                if not isinstance(raw, dict):
                    raise NfcRepositoryError("NFC test tag is invalid")
                existing = NfcTestTag.from_dict(raw)
                if existing.access_point_id == tag.access_point_id:
                    data["test_tags"].pop(key)
            data["test_tags"][tag.token_hash] = tag.to_dict()
            await self._store.async_save(data)
            self._data = data

    async def get_active_test_tag(self, raw_token: str) -> NfcTestTag:
        """Resolve a non-expired test tag without persisting its bearer token."""
        async with self._lock:
            raw = self._require_data()["test_tags"].get(hash_token(raw_token))
            if not isinstance(raw, dict):
                raise NfcRepositoryError("NFC test tag was not found")
            tag = NfcTestTag.from_dict(raw)
            if not tag.active:
                raise NfcRepositoryError("NFC test tag is disabled or expired")
            return tag

    async def active_test_tag_for_access_point(self, access_point_id: UUID) -> NfcTestTag | None:
        """Return one active test tag for a Door without exposing its URL token."""
        async with self._lock:
            for raw in self._require_data()["test_tags"].values():
                if not isinstance(raw, dict):
                    raise NfcRepositoryError("NFC test tag is invalid")
                tag = NfcTestTag.from_dict(raw)
                if tag.access_point_id == access_point_id and tag.active:
                    return tag
            return None

    async def test_tag_hash_is_active(self, token_hash: str, access_point_id: UUID) -> bool:
        """Recheck a test tag at unlock time so revocation takes effect immediately."""
        async with self._lock:
            raw = self._require_data()["test_tags"].get(token_hash)
            if not isinstance(raw, dict):
                return False
            tag = NfcTestTag.from_dict(raw)
            return tag.access_point_id == access_point_id and tag.active

    async def revoke_test_tags_for_access_point(self, access_point_id: UUID) -> int:
        """Remove every static test-tag token mapped to one Door."""
        async with self._lock:
            data = deepcopy(self._require_data())
            changed = 0
            for key, raw in tuple(data["test_tags"].items()):
                if not isinstance(raw, dict):
                    raise NfcRepositoryError("NFC test tag is invalid")
                tag = NfcTestTag.from_dict(raw)
                if tag.access_point_id == access_point_id:
                    data["test_tags"].pop(key)
                    changed += 1
            if changed:
                await self._store.async_save(data)
                self._data = data
            return changed

    async def enabled_tag_counts_by_access_point(self) -> dict[UUID, int]:
        """Return non-secret enabled-tag counts keyed by Door UUID."""
        async with self._lock:
            counts: dict[UUID, int] = {}
            for raw in self._require_data()["tags"].values():
                if not isinstance(raw, dict):
                    continue
                tag = NfcTag.from_dict(raw)
                if tag.enabled:
                    counts[tag.access_point_id] = counts.get(tag.access_point_id, 0) + 1
            return counts

    async def list_tags_for_access_point(self, access_point_id: UUID) -> tuple[NfcTag, ...]:
        """Return registered tags for one Door without exposing their AES keys."""
        async with self._lock:
            tags = (
                NfcTag.from_dict(raw)
                for raw in self._require_data()["tags"].values()
                if isinstance(raw, dict)
            )
            return tuple(
                sorted(
                    (tag for tag in tags if tag.access_point_id == access_point_id),
                    key=lambda tag: (not tag.enabled, tag.created_at, tag.uid_hex),
                )
            )

    async def revoke_tag(self, public_id: str, access_point_id: UUID) -> NfcTag:
        """Disable one physical tag while retaining its non-secret audit record."""
        return await self._set_tag_enabled(public_id, access_point_id, False)

    async def reinstate_tag(self, public_id: str, access_point_id: UUID) -> NfcTag:
        """Re-enable one previously disabled physical tag."""
        return await self._set_tag_enabled(public_id, access_point_id, True)

    async def _set_tag_enabled(
        self, public_id: str, access_point_id: UUID, enabled: bool
    ) -> NfcTag:
        """Set one physical tag's reversible enabled state."""
        async with self._lock:
            data = deepcopy(self._require_data())
            raw = data["tags"].get(public_id)
            if not isinstance(raw, dict):
                raise NfcRepositoryError("NFC tag was not found")
            tag = NfcTag.from_dict(raw)
            if tag.access_point_id != access_point_id:
                raise NfcRepositoryError("NFC tag is not registered to this Door")
            updated = NfcTag(
                tag.public_id,
                tag.uid_hex,
                tag.access_point_id,
                tag.meta_key_credential_id,
                tag.file_key_credential_id,
                enabled,
                tag.last_counter,
                tag.created_at,
                tag.admin_key_credential_id,
                tag.write_protected,
            )
            data["tags"][public_id] = updated.to_dict()
            await self._store.async_save(data)
            self._data = data
            return updated

    async def delete_tag(self, public_id: str, access_point_id: UUID) -> NfcTag:
        """Permanently remove one physical tag registration from HomePASS."""
        async with self._lock:
            data = deepcopy(self._require_data())
            raw = data["tags"].get(public_id)
            if not isinstance(raw, dict):
                raise NfcRepositoryError("NFC tag was not found")
            tag = NfcTag.from_dict(raw)
            if tag.access_point_id != access_point_id:
                raise NfcRepositoryError("NFC tag is not registered to this Door")
            data["tags"].pop(public_id)
            await self._store.async_save(data)
            self._data = data
            return tag

    async def claim_counter(self, public_id: str, counter: int) -> NfcTag:
        """Atomically reject replayed tag reads and remember the newest counter."""
        async with self._lock:
            data = deepcopy(self._require_data())
            raw = data["tags"].get(public_id)
            if not isinstance(raw, dict):
                raise NfcRepositoryError("NFC tag was not found")
            tag = NfcTag.from_dict(raw)
            if not tag.enabled:
                raise NfcRepositoryError("NFC tag is disabled")
            if tag.last_counter is not None and counter <= tag.last_counter:
                raise NfcRepositoryError("NFC tap was already used")
            updated = NfcTag(
                tag.public_id,
                tag.uid_hex,
                tag.access_point_id,
                tag.meta_key_credential_id,
                tag.file_key_credential_id,
                tag.enabled,
                counter,
                tag.created_at,
                tag.admin_key_credential_id,
                tag.write_protected,
            )
            data["tags"][public_id] = updated.to_dict()
            await self._store.async_save(data)
            self._data = data
            return updated

    async def set_tag_admin_key(
        self, public_id: str, access_point_id: UUID, credential_id: str
    ) -> NfcTag:
        """Attach a recoverable rewrite-administrator key to one physical tag."""
        async with self._lock:
            data = deepcopy(self._require_data())
            raw = data["tags"].get(public_id)
            if not isinstance(raw, dict):
                raise NfcRepositoryError("NFC tag was not found")
            tag = NfcTag.from_dict(raw)
            if tag.access_point_id != access_point_id:
                raise NfcRepositoryError("NFC tag is not registered to this Door")
            updated = NfcTag(
                tag.public_id,
                tag.uid_hex,
                tag.access_point_id,
                tag.meta_key_credential_id,
                tag.file_key_credential_id,
                tag.enabled,
                tag.last_counter,
                tag.created_at,
                credential_id,
                tag.write_protected,
            )
            data["tags"][public_id] = updated.to_dict()
            await self._store.async_save(data)
            self._data = data
            return updated

    async def confirm_tag_write_protected(self, public_id: str, access_point_id: UUID) -> NfcTag:
        """Record an administrator-confirmed successful protected encoding."""
        async with self._lock:
            data = deepcopy(self._require_data())
            raw = data["tags"].get(public_id)
            if not isinstance(raw, dict):
                raise NfcRepositoryError("NFC tag was not found")
            tag = NfcTag.from_dict(raw)
            if tag.access_point_id != access_point_id:
                raise NfcRepositoryError("NFC tag is not registered to this Door")
            if tag.admin_key_credential_id is None:
                raise NfcRepositoryError("NFC tag has no administrator key")
            updated = NfcTag(
                tag.public_id,
                tag.uid_hex,
                tag.access_point_id,
                tag.meta_key_credential_id,
                tag.file_key_credential_id,
                tag.enabled,
                None,
                tag.created_at,
                tag.admin_key_credential_id,
                True,
            )
            data["tags"][public_id] = updated.to_dict()
            await self._store.async_save(data)
            self._data = data
            return updated

    async def create_invite(self, invite: EnrollmentInvite) -> None:
        async with self._lock:
            data = deepcopy(self._require_data())
            data["invites"][invite.token_hash] = invite.to_dict()
            await self._store.async_save(data)
            self._data = data

    async def get_active_invite(self, raw_token: str) -> EnrollmentInvite:
        async with self._lock:
            raw = self._require_data()["invites"].get(hash_token(raw_token))
            if not isinstance(raw, dict):
                raise NfcRepositoryError("Enrollment invitation is invalid")
            invite = EnrollmentInvite.from_dict(raw)
            if not invite.active:
                raise NfcRepositoryError("Enrollment invitation is expired or already used")
            return invite

    async def complete_enrollment(self, raw_token: str, credential: PasskeyCredential) -> None:
        """Consume an invite and add its passkey in one durable mutation."""
        async with self._lock:
            data = deepcopy(self._require_data())
            token_hash = hash_token(raw_token)
            raw = data["invites"].get(token_hash)
            if not isinstance(raw, dict):
                raise NfcRepositoryError("Enrollment invitation is invalid")
            invite = EnrollmentInvite.from_dict(raw)
            if not invite.active or invite.person_id != credential.person_id:
                raise NfcRepositoryError("Enrollment invitation cannot be used")
            if credential.credential_id in data["credentials"]:
                raise NfcRepositoryError("Passkey is already enrolled")
            data["credentials"][credential.credential_id] = credential.to_dict()
            data["invites"][token_hash] = EnrollmentInvite(
                invite.token_hash,
                invite.person_id,
                invite.person_name,
                invite.expires_at,
                utcnow(),
                invite.created_at,
            ).to_dict()
            await self._store.async_save(data)
            self._data = data

    async def list_credentials_for_person(self, person_id: UUID) -> tuple[PasskeyCredential, ...]:
        async with self._lock:
            items = (
                PasskeyCredential.from_dict(raw)
                for raw in self._require_data()["credentials"].values()
                if isinstance(raw, dict)
            )
            return tuple(
                sorted(
                    (item for item in items if item.person_id == person_id and item.enabled),
                    key=lambda item: item.credential_id,
                )
            )

    async def get_credential(self, credential_id: str) -> PasskeyCredential:
        async with self._lock:
            raw = self._require_data()["credentials"].get(credential_id)
            if not isinstance(raw, dict):
                raise NfcRepositoryError("Passkey is not enrolled")
            credential = PasskeyCredential.from_dict(raw)
            if not credential.enabled:
                raise NfcRepositoryError("Passkey is disabled")
            return credential

    async def replace_access_grants_for_person(
        self,
        person_id: UUID,
        access_point_ids: frozenset[UUID],
    ) -> tuple[NfcAccessGrant, ...]:
        """Atomically replace one Person's explicit NFC Door assignments."""
        if not isinstance(person_id, UUID) or any(
            not isinstance(access_point_id, UUID) for access_point_id in access_point_ids
        ):
            raise TypeError("NFC access assignments require UUID identifiers")
        async with self._lock:
            data = deepcopy(self._require_data())
            records = data["access_grants"]
            now = utcnow()
            existing: dict[UUID, NfcAccessGrant] = {}
            for key, raw in tuple(records.items()):
                if not isinstance(raw, dict):
                    raise NfcRepositoryError("NFC access grant is invalid")
                grant = NfcAccessGrant.from_dict(raw)
                if key != self._grant_key(grant.person_id, grant.access_point_id):
                    raise NfcRepositoryError("NFC access grant key is invalid")
                if grant.person_id == person_id:
                    existing[grant.access_point_id] = grant
                    records.pop(key)
            updated_items: list[NfcAccessGrant] = []
            for access_point_id in sorted(access_point_ids, key=str):
                previous = existing.get(access_point_id)
                updated_items.append(
                    NfcAccessGrant(
                        person_id,
                        access_point_id,
                        now if previous is None else previous.created_at,
                        now,
                    )
                )
            updated = tuple(updated_items)
            for grant in updated:
                records[self._grant_key(person_id, grant.access_point_id)] = grant.to_dict()
            await self._store.async_save(data)
            self._data = data
            return updated

    async def has_access_grant(self, person_id: UUID, access_point_id: UUID) -> bool:
        """Return whether NFC access was explicitly assigned for this relationship."""
        async with self._lock:
            raw = self._require_data()["access_grants"].get(
                self._grant_key(person_id, access_point_id)
            )
            if raw is None:
                return False
            if not isinstance(raw, dict):
                raise NfcRepositoryError("NFC access grant is invalid")
            grant = NfcAccessGrant.from_dict(raw)
            return grant.person_id == person_id and grant.access_point_id == access_point_id

    async def list_access_grants_for_person(self, person_id: UUID) -> tuple[NfcAccessGrant, ...]:
        """Return explicit NFC assignments for one Person."""
        async with self._lock:
            grants = tuple(
                NfcAccessGrant.from_dict(raw)
                for raw in self._require_data()["access_grants"].values()
                if isinstance(raw, dict)
            )
            return tuple(
                sorted(
                    (grant for grant in grants if grant.person_id == person_id),
                    key=lambda grant: str(grant.access_point_id),
                )
            )

    async def disable_credentials_for_person(self, person_id: UUID) -> int:
        """Disable passkeys and revoke NFC grants before Person deletion."""
        async with self._lock:
            data = deepcopy(self._require_data())
            changed = 0
            for key, raw in tuple(data["credentials"].items()):
                if not isinstance(raw, dict):
                    continue
                item = PasskeyCredential.from_dict(raw)
                if item.person_id == person_id and item.enabled:
                    data["credentials"][key] = PasskeyCredential(
                        item.credential_id,
                        item.person_id,
                        item.public_key,
                        item.sign_count,
                        item.device_type,
                        item.backed_up,
                        False,
                        item.created_at,
                    ).to_dict()
                    changed += 1
            for key, raw in tuple(data["invites"].items()):
                if not isinstance(raw, dict):
                    continue
                invite = EnrollmentInvite.from_dict(raw)
                if invite.person_id == person_id:
                    data["invites"].pop(key)
                    changed += 1
            for key, raw in tuple(data["access_grants"].items()):
                if not isinstance(raw, dict):
                    continue
                grant = NfcAccessGrant.from_dict(raw)
                if grant.person_id == person_id:
                    data["access_grants"].pop(key)
                    changed += 1
            if changed:
                await self._store.async_save(data)
                self._data = data
            return changed

    async def disable_tags_for_access_point(self, access_point_id: UUID) -> int:
        """Disable tags and revoke NFC grants before Door deletion."""
        async with self._lock:
            data = deepcopy(self._require_data())
            changed = 0
            for key, raw in tuple(data["tags"].items()):
                if not isinstance(raw, dict):
                    continue
                item = NfcTag.from_dict(raw)
                if item.access_point_id == access_point_id and item.enabled:
                    data["tags"][key] = NfcTag(
                        item.public_id,
                        item.uid_hex,
                        item.access_point_id,
                        item.meta_key_credential_id,
                        item.file_key_credential_id,
                        False,
                        item.last_counter,
                        item.created_at,
                        item.admin_key_credential_id,
                        item.write_protected,
                    ).to_dict()
                    changed += 1
            for key, raw in tuple(data["test_tags"].items()):
                if not isinstance(raw, dict):
                    continue
                item = NfcTestTag.from_dict(raw)
                if item.access_point_id == access_point_id:
                    data["test_tags"].pop(key)
                    changed += 1
            for key, raw in tuple(data["access_grants"].items()):
                if not isinstance(raw, dict):
                    continue
                grant = NfcAccessGrant.from_dict(raw)
                if grant.access_point_id == access_point_id:
                    data["access_grants"].pop(key)
                    changed += 1
            if changed:
                await self._store.async_save(data)
                self._data = data
            return changed

    async def update_sign_count(self, credential_id: str, sign_count: int) -> None:
        async with self._lock:
            data = deepcopy(self._require_data())
            raw = data["credentials"].get(credential_id)
            if not isinstance(raw, dict):
                raise NfcRepositoryError("Passkey is not enrolled")
            item = PasskeyCredential.from_dict(raw)
            if sign_count < item.sign_count:
                raise NfcRepositoryError("Passkey signature counter moved backwards")
            data["credentials"][credential_id] = PasskeyCredential(
                item.credential_id,
                item.person_id,
                item.public_key,
                sign_count,
                item.device_type,
                item.backed_up,
                item.enabled,
                item.created_at,
            ).to_dict()
            await self._store.async_save(data)
            self._data = data

    async def append_audit(
        self,
        *,
        occurred_at: datetime,
        outcome: str,
        access_point_id: str,
        person_id: str | None,
        reason: str,
        counter: int | None,
        test_mode: bool = False,
    ) -> None:
        async with self._lock:
            data = deepcopy(self._require_data())
            audit = cast(list[dict[str, Any]], data["audit"])
            audit.append(
                {
                    "occurred_at": occurred_at.isoformat(),
                    "outcome": outcome,
                    "access_point_id": access_point_id,
                    "person_id": person_id,
                    "reason": reason,
                    "counter": counter,
                    "test_mode": test_mode,
                }
            )
            del audit[:-_MAX_AUDIT_RECORDS]
            await self._store.async_save(data)
            self._data = data

    @staticmethod
    def _validate(raw: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(raw, dict):
            raise NfcRepositoryError("NFC storage has an invalid schema")
        migrated = deepcopy(raw)
        if set(migrated) == {"tags", "credentials", "invites", "audit"}:
            migrated["access_grants"] = {}
        if "test_tags" not in migrated:
            migrated["test_tags"] = {}
        if set(migrated) != {
            "tags",
            "test_tags",
            "credentials",
            "invites",
            "access_grants",
            "audit",
        }:
            raise NfcRepositoryError("NFC storage has an invalid schema")
        if not all(
            isinstance(migrated[key], dict)
            for key in ("tags", "test_tags", "credentials", "invites", "access_grants")
        ):
            raise NfcRepositoryError("NFC storage collections are invalid")
        if not isinstance(migrated["audit"], list):
            raise NfcRepositoryError("NFC audit storage is invalid")
        for key, record in migrated["access_grants"].items():
            if not isinstance(record, dict):
                raise NfcRepositoryError("NFC access grant is invalid")
            grant = NfcAccessGrant.from_dict(record)
            if key != NfcAccessRepository._grant_key(grant.person_id, grant.access_point_id):
                raise NfcRepositoryError("NFC access grant key is invalid")
        for key, record in migrated["test_tags"].items():
            if not isinstance(record, dict):
                raise NfcRepositoryError("NFC test tag is invalid")
            tag = NfcTestTag.from_dict(record)
            if key != tag.token_hash:
                raise NfcRepositoryError("NFC test-tag token key is invalid")
        return migrated

    @staticmethod
    def _grant_key(person_id: UUID, access_point_id: UUID) -> str:
        return f"{person_id}:{access_point_id}"


__all__ = ["NfcAccessRepository", "NfcRepositoryError", "hash_token"]
