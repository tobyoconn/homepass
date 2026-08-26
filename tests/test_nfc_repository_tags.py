"""Per-Door NFC tag administration tests."""

import asyncio
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from custom_components.homepass.nfc.models import NfcTag
from custom_components.homepass.nfc.repository import NfcAccessRepository


class _Store:
    def __init__(self, data):
        self.data = data

    async def async_save(self, data):
        self.data = data


class _FailingStore:
    async def async_save(self, data):
        raise OSError("storage unavailable")


@pytest.mark.asyncio
async def test_list_disable_reinstate_and_delete_one_tag_without_affecting_another() -> None:
    door_id = uuid4()
    other_door_id = uuid4()
    first = NfcTag(
        "abcdefghijklmnop", "04010203040501", door_id,
        str(uuid4()), str(uuid4()), True, 10, datetime.now(UTC),
    )
    second = NfcTag(
        "qrstuvwxyzABCDEF", "04010203040502", other_door_id,
        str(uuid4()), str(uuid4()), True, None, datetime.now(UTC),
    )
    repository = object.__new__(NfcAccessRepository)
    repository._lock = asyncio.Lock()
    repository._data = {
        "tags": {first.public_id: first.to_dict(), second.public_id: second.to_dict()},
        "test_tags": {}, "credentials": {}, "invites": {},
        "access_grants": {}, "audit": [],
    }
    repository._store = _Store(repository._data)

    assert await repository.list_tags_for_access_point(door_id) == (first,)

    revoked = await repository.revoke_tag(first.public_id, door_id)

    assert revoked.enabled is False
    assert (await repository.get_tag(first.public_id)).enabled is False
    assert (await repository.get_tag(second.public_id)).enabled is True

    reinstated = await repository.reinstate_tag(first.public_id, door_id)

    assert reinstated.enabled is True
    assert (await repository.get_tag(first.public_id)).enabled is True

    deleted = await repository.delete_tag(first.public_id, door_id)

    assert deleted.public_id == first.public_id
    with pytest.raises(ValueError, match="not found"):
        await repository.get_tag(first.public_id)
    assert (await repository.get_tag(second.public_id)).enabled is True


@pytest.mark.asyncio
async def test_existing_tag_can_record_recoverable_write_protection() -> None:
    door_id = uuid4()
    tag = NfcTag(
        "abcdefghijklmnop", "04010203040503", door_id,
        str(uuid4()), str(uuid4()), True, 20, datetime.now(UTC),
    )
    repository = object.__new__(NfcAccessRepository)
    repository._lock = asyncio.Lock()
    repository._data = {
        "tags": {tag.public_id: tag.to_dict()}, "test_tags": {},
        "credentials": {}, "invites": {}, "access_grants": {}, "audit": [],
    }
    repository._store = _Store(repository._data)
    admin_id = str(uuid4())

    prepared = await repository.set_tag_admin_key(tag.public_id, door_id, admin_id)
    assert prepared.admin_key_credential_id == admin_id
    assert prepared.write_protected is False

    protected = await repository.confirm_tag_write_protected(tag.public_id, door_id)
    assert protected.admin_key_credential_id == admin_id
    assert protected.write_protected is True
    assert protected.last_counter is None


@pytest.mark.asyncio
async def test_failed_save_does_not_change_live_tag_state() -> None:
    """A storage failure must not leave an in-memory tag change partially applied."""
    door_id = uuid4()
    tag = NfcTag(
        "abcdefghijklmnop", "04010203040503", door_id,
        str(uuid4()), str(uuid4()), True, 20, datetime.now(UTC),
    )
    original = tag.to_dict()
    repository = object.__new__(NfcAccessRepository)
    repository._lock = asyncio.Lock()
    repository._data = {
        "tags": {tag.public_id: original}, "test_tags": {},
        "credentials": {}, "invites": {}, "access_grants": {}, "audit": [],
    }
    repository._store = _FailingStore()

    replacement = NfcTag(
        tag.public_id, tag.uid_hex, tag.access_point_id,
        tag.meta_key_credential_id, tag.file_key_credential_id,
        False, tag.last_counter, tag.created_at,
    )
    with pytest.raises(OSError, match="storage unavailable"):
        await repository.upsert_tag(replacement)

    assert repository._data["tags"][tag.public_id] == original
    assert (await repository.get_tag(tag.public_id)).enabled is True
