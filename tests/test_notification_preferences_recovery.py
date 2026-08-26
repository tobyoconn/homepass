"""Regression tests for preservation-first notification preference recovery."""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
import logging
from uuid import UUID

import pytest

from custom_components.homepass.const import STORAGE_SCHEMA_VERSION
from custom_components.homepass.models import (
    PERMANENT_SCHEDULE_ID,
    AccessGrant,
    AccessPoint,
    NotificationPreferences,
    Person,
    permanent_schedule,
)
from custom_components.homepass.storage import async_migrate_storage

PERSON_ID = UUID("00000000-0000-4000-8000-000000000301")
ACCESS_POINT_ID = UUID("00000000-0000-4000-8000-000000000101")
CREDENTIAL_ID = UUID("00000000-0000-4000-8000-000000000401")
GRANT_ID = UUID("00000000-0000-4000-8000-000000000501")
NOW = datetime(2026, 8, 27, 12, 0, tzinfo=UTC)
RECOVERY_BACKUP_SETTING = "notification_preferences_recovery_backup"


def _storage_with_access_records() -> dict[str, object]:
    """Return a valid current snapshot containing synthetic access records."""
    person = Person(
        "Example Resident",
        person_id=PERSON_ID,
        created_at=NOW,
        updated_at=NOW,
    )
    access_point = AccessPoint(
        "Example Door",
        id=ACCESS_POINT_ID,
        created_at=NOW,
        updated_at=NOW,
    )
    grant = AccessGrant(
        person_id=PERSON_ID,
        credential_id=CREDENTIAL_ID,
        access_point_id=ACCESS_POINT_ID,
        access_grant_id=GRANT_ID,
        created_at=NOW,
        updated_at=NOW,
    )
    return {
        "metadata": {"schema_version": STORAGE_SCHEMA_VERSION},
        "data": {
            "people": {str(PERSON_ID): person.to_dict()},
            "access_points": {str(ACCESS_POINT_ID): access_point.to_dict()},
            "access_devices": {},
            "access_metadata": {},
            "credential_metadata": {},
            "access_grants": {
                f"{PERSON_ID}:{ACCESS_POINT_ID}": grant.to_dict(),
            },
            "schedules": {
                str(PERMANENT_SCHEDULE_ID): permanent_schedule().to_dict(),
            },
            "lifecycle_operations": {},
            "synchronization_statuses": {},
            "synchronization_history": {},
            "activity_events": {},
            "properties": {"example": {"display_name": "Example Home"}},
            "settings": {
                "managed_access_points": {},
                "access_point_name_fallbacks": {},
                "unrelated_setting": {"preserve": True},
            },
        },
    }


@pytest.mark.asyncio
async def test_invalid_notification_preferences_recover_without_access_changes(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A malformed preference record must never block or alter access data."""
    snapshot = _storage_with_access_records()
    data = snapshot["data"]
    assert isinstance(data, dict)
    settings = data["settings"]
    assert isinstance(settings, dict)
    invalid_preferences = {
        "version": 2,
        "enabled": True,
        "selected_device_ids": ["mobile_app:must-not-be-logged", None],
        "events": {},
    }
    settings["notification_preferences"] = invalid_preferences
    original_data = deepcopy(data)

    with pytest.raises(ValueError, match="invalid collections"):
        NotificationPreferences.migrate_dict(invalid_preferences)

    with caplog.at_level(logging.WARNING):
        migrated = await async_migrate_storage(snapshot)

    migrated_data = migrated["data"]
    for collection_name, records in original_data.items():
        if collection_name != "settings":
            assert migrated_data[collection_name] == records
    migrated_settings = migrated_data["settings"]
    assert migrated_settings["unrelated_setting"] == {"preserve": True}
    assert migrated_settings[RECOVERY_BACKUP_SETTING] == invalid_preferences
    assert migrated_settings["notification_preferences"] == (
        NotificationPreferences.defaults().to_dict()
    )
    assert "must-not-be-logged" not in caplog.text
    assert "access-control records were not changed" in caplog.text


@pytest.mark.asyncio
async def test_valid_notification_preferences_are_preserved() -> None:
    """Valid preferences continue through the migration unchanged."""
    snapshot = _storage_with_access_records()
    data = snapshot["data"]
    assert isinstance(data, dict)
    settings = data["settings"]
    assert isinstance(settings, dict)
    preferences = NotificationPreferences.defaults(("mobile_app:example_phone",)).to_dict()
    settings["notification_preferences"] = preferences

    migrated = await async_migrate_storage(snapshot)

    migrated_settings = migrated["data"]["settings"]
    assert migrated_settings["notification_preferences"] == preferences
    assert RECOVERY_BACKUP_SETTING not in migrated_settings


@pytest.mark.asyncio
async def test_first_recovery_backup_is_not_overwritten() -> None:
    """Repeated recovery retains the first diagnostic record."""
    snapshot = _storage_with_access_records()
    data = snapshot["data"]
    assert isinstance(data, dict)
    settings = data["settings"]
    assert isinstance(settings, dict)
    first_invalid_record = {"selected_device_ids": None}
    settings[RECOVERY_BACKUP_SETTING] = first_invalid_record
    settings["notification_preferences"] = {"events": []}

    migrated = await async_migrate_storage(snapshot)

    assert migrated["data"]["settings"][RECOVERY_BACKUP_SETTING] == first_invalid_record
