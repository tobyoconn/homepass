"""Persistent storage for HomePASS."""

from __future__ import annotations

import asyncio
import inspect
import logging
import math
from collections.abc import Callable
from contextvars import ContextVar
from copy import deepcopy
from datetime import UTC, datetime
from typing import TypedDict, TypeVar, cast
from uuid import NAMESPACE_URL, UUID, uuid5

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.storage import Store

from .const import (
    STORAGE_KEY,
    STORAGE_MINOR_VERSION,
    STORAGE_SCHEMA_VERSION,
    STORAGE_VERSION,
)
from .exceptions import MigrationError

type JsonValue = str | int | float | bool | None | list[JsonValue] | dict[str, JsonValue]
type StorageRecord = dict[str, JsonValue]
TransactionResultT = TypeVar("TransactionResultT")

_TRANSACTION_ACTIVE: ContextVar[bool] = ContextVar(
    "homepass_storage_transaction_active", default=False
)

_MANAGED_ACCESS_POINTS_SETTING = "managed_access_points"
_ACCESS_POINT_NAME_FALLBACKS_SETTING = "access_point_name_fallbacks"
_NOTIFICATION_PREFERENCES_RECOVERY_BACKUP_SETTING = "notification_preferences_recovery_backup"
_LOGGER = logging.getLogger(__name__)
_LEGACY_ACCESS_POINT_ID = "00000000-0000-4000-8000-000000000001"
_LEGACY_ACCESS_POINT_DISPLAY_NAME = "Lock"
_MIGRATED_ACCESS_POINT_DISPLAY_NAME = "Lock"
_ACCESS_POINT_MIGRATION_TIMESTAMP = datetime(2026, 7, 15, tzinfo=UTC)
_ACCESS_POINT_RECORD_FIELDS = {
    "id",
    "display_name",
    "enabled",
    "created_at",
    "updated_at",
}


class StorageMetadata(TypedDict):
    """HomePASS storage metadata."""

    schema_version: int


class StorageCollections(TypedDict):
    """HomePASS storage collections."""

    people: dict[str, StorageRecord]
    access_points: dict[str, StorageRecord]
    access_devices: dict[str, StorageRecord]
    access_metadata: dict[str, StorageRecord]
    credential_metadata: dict[str, StorageRecord]
    access_grants: dict[str, StorageRecord]
    schedules: dict[str, StorageRecord]
    lifecycle_operations: dict[str, StorageRecord]
    synchronization_statuses: dict[str, StorageRecord]
    synchronization_history: dict[str, StorageRecord]
    activity_events: dict[str, StorageRecord]
    properties: dict[str, StorageRecord]
    settings: dict[str, JsonValue]


class HomePassStorageData(TypedDict):
    """Complete HomePASS storage payload."""

    metadata: StorageMetadata
    data: StorageCollections


type StorageMutator[ResultT] = Callable[[HomePassStorageData], ResultT]


class HomePassStorageError(HomeAssistantError):
    """Base exception for HomePASS storage failures."""


class InvalidHomePassStorageError(HomePassStorageError):
    """Raised when stored HomePASS data is malformed."""


class UnsupportedHomePassStorageVersionError(HomePassStorageError):
    """Raised when no migration exists for a storage version."""


class InvalidHomePassStorageTransactionError(HomePassStorageError):
    """Raised when a storage transaction violates the unit-of-work contract."""


class NestedHomePassStorageTransactionError(HomePassStorageError):
    """Raised when a transaction is started from another transaction."""


def _empty_storage() -> HomePassStorageData:
    """Return an empty storage payload."""
    from .models.schedule import PERMANENT_SCHEDULE_ID, permanent_schedule

    return {
        "metadata": {"schema_version": STORAGE_SCHEMA_VERSION},
        "data": {
            "people": {},
            "access_points": {},
            "access_devices": {},
            "access_metadata": {},
            "credential_metadata": {},
            "access_grants": {},
            "schedules": {
                str(PERMANENT_SCHEDULE_ID): cast(StorageRecord, permanent_schedule().to_dict())
            },
            "lifecycle_operations": {},
            "synchronization_statuses": {},
            "synchronization_history": {},
            "activity_events": {},
            "properties": {},
            "settings": {
                _MANAGED_ACCESS_POINTS_SETTING: {},
                _ACCESS_POINT_NAME_FALLBACKS_SETTING: {},
            },
        },
    }


def _is_json_value(value: object) -> bool:
    """Return whether a value can be represented in JSON."""
    if value is None or isinstance(value, str | bool | int):
        return True
    if isinstance(value, float):
        return math.isfinite(value)
    if isinstance(value, list):
        return all(_is_json_value(item) for item in value)
    if isinstance(value, dict):
        return all(isinstance(key, str) and _is_json_value(item) for key, item in value.items())
    return False


def _schema_version(raw: object) -> int:
    """Extract the schema version from a raw payload."""
    if not isinstance(raw, dict):
        raise InvalidHomePassStorageError("HomePASS storage must be an object")

    metadata = raw.get("metadata")
    if not isinstance(metadata, dict):
        raise InvalidHomePassStorageError("HomePASS storage metadata must be an object")

    schema_version = metadata.get("schema_version")
    if isinstance(schema_version, bool) or not isinstance(schema_version, int):
        raise InvalidHomePassStorageError(
            "HomePASS storage metadata must contain an integer schema_version"
        )
    return schema_version


def _validate_root(raw: object, expected_collections: set[str]) -> dict[str, object]:
    """Validate the common storage container and collection names."""
    if not isinstance(raw, dict) or set(raw) != {"metadata", "data"}:
        raise InvalidHomePassStorageError("HomePASS storage must contain metadata and data")

    metadata = raw["metadata"]
    if not isinstance(metadata, dict) or set(metadata) != {"schema_version"}:
        raise InvalidHomePassStorageError(
            "HomePASS storage metadata must contain only schema_version"
        )

    data = raw["data"]
    if not isinstance(data, dict) or set(data) != expected_collections:
        raise InvalidHomePassStorageError("HomePASS storage data contains unexpected collections")
    return data


def _validate_record_collections(
    data: dict[str, object],
    collection_names: tuple[str, ...],
) -> None:
    """Validate JSON-compatible record collections."""
    for collection_name in collection_names:
        collection = data[collection_name]
        if not isinstance(collection, dict) or not all(
            isinstance(identifier, str) and isinstance(record, dict) and _is_json_value(record)
            for identifier, record in collection.items()
        ):
            raise InvalidHomePassStorageError(
                f"HomePASS storage {collection_name} must be an object of records"
            )


def _validate_storage(raw: object) -> HomePassStorageData:
    """Validate and copy a current HomePASS storage payload."""
    data = _validate_root(
        raw,
        {
            "people",
            "access_points",
            "access_devices",
            "access_metadata",
            "credential_metadata",
            "access_grants",
            "schedules",
            "lifecycle_operations",
            "synchronization_statuses",
            "synchronization_history",
            "activity_events",
            "properties",
            "settings",
        },
    )
    metadata = cast(dict[str, object], cast(dict[str, object], raw)["metadata"])
    if metadata["schema_version"] != STORAGE_SCHEMA_VERSION:
        raise InvalidHomePassStorageError("HomePASS storage schema_version is not current")

    _validate_record_collections(
        data,
        (
            "people",
            "access_points",
            "access_devices",
            "access_metadata",
            "credential_metadata",
            "access_grants",
            "schedules",
            "lifecycle_operations",
            "synchronization_statuses",
            "synchronization_history",
            "activity_events",
            "properties",
        ),
    )

    settings = data["settings"]
    if not isinstance(settings, dict) or not _is_json_value(settings):
        raise InvalidHomePassStorageError("HomePASS storage settings must be a JSON object")
    _validate_managed_access_points(settings)
    _validate_access_point_name_fallbacks(settings)

    return cast(HomePassStorageData, deepcopy(raw))


def _validate_managed_access_points(settings: dict[str, object]) -> dict[str, object]:
    """Validate and return stable discovery enrolment records."""
    managed = settings.get(_MANAGED_ACCESS_POINTS_SETTING)
    if not isinstance(managed, dict):
        raise InvalidHomePassStorageError("HomePASS managed Access Points must be an object")
    discovery_keys: set[str] = set()
    for access_point_id, record in managed.items():
        if not isinstance(access_point_id, str) or not isinstance(record, dict):
            raise InvalidHomePassStorageError("HomePASS managed Access Point is invalid")
        try:
            UUID(access_point_id)
        except ValueError as err:
            raise InvalidHomePassStorageError(
                "HomePASS managed Access Point identifier is invalid"
            ) from err
        if (
            set(record)
            != {
                "discovery_key",
                "managed",
                "control_entity_id",
                "status_entity_id",
                "control_profile",
                "status_inverted",
                "pulse_seconds",
                "pin_capable",
                "nfc_capable",
                "device_id",
            }
            or not (record["discovery_key"] is None or isinstance(record["discovery_key"], str))
            or not isinstance(record["managed"], bool)
            or not (
                record["control_entity_id"] is None or isinstance(record["control_entity_id"], str)
            )
            or not (
                record["status_entity_id"] is None or isinstance(record["status_entity_id"], str)
            )
            or record["control_profile"]
            not in {"lock", "garage_cover", "garage_toggle", "electric_strike"}
            or not isinstance(record["status_inverted"], bool)
            or isinstance(record["pulse_seconds"], bool)
            or not isinstance(record["pulse_seconds"], int | float)
            or not 0.1 <= record["pulse_seconds"] <= 10
            or not isinstance(record["pin_capable"], bool)
            or not isinstance(record["nfc_capable"], bool)
            or not (record["device_id"] is None or isinstance(record["device_id"], str))
        ):
            raise InvalidHomePassStorageError("HomePASS managed Access Point record is invalid")
        discovery_key = record["discovery_key"]
        if discovery_key is not None:
            if discovery_key in discovery_keys:
                raise InvalidHomePassStorageError(
                    "HomePASS managed Access Point discovery keys must be unique"
                )
            discovery_keys.add(discovery_key)

    return cast(dict[str, object], managed)


def _validate_access_point_name_fallbacks(
    settings: dict[str, object],
) -> dict[str, object]:
    """Validate durable markers for untouched migrated fallback names."""
    fallbacks = settings.get(_ACCESS_POINT_NAME_FALLBACKS_SETTING, {})
    if not isinstance(fallbacks, dict):
        raise InvalidHomePassStorageError("HomePASS Access Point name fallbacks must be an object")
    for access_point_id, pending in fallbacks.items():
        try:
            identifier = UUID(access_point_id)
        except (TypeError, ValueError) as err:
            raise InvalidHomePassStorageError(
                "HomePASS Access Point name fallback identifier is invalid"
            ) from err
        if str(identifier) != access_point_id or pending is not True:
            raise InvalidHomePassStorageError(
                "HomePASS Access Point name fallback marker is invalid"
            )
    return cast(dict[str, object], fallbacks)


def _validate_domain_snapshot(raw: object) -> HomePassStorageData:
    """Validate current storage structure and every supported domain collection."""
    snapshot = _validate_storage(raw)
    try:
        from .models import (
            AccessDevice,
            AccessGrant,
            AccessMetadata,
            AccessPoint,
            AccessPointSynchronization,
            ActivityEvent,
            LifecycleOperation,
            NotificationPreferences,
            Person,
            PropertySettings,
            Schedule,
            SynchronizationHistoryEvent,
        )
        from .models.schedule import (
            PERMANENT_SCHEDULE_ID,
            PERMANENT_SCHEDULE_NAME,
            permanent_schedule,
        )
        from .vault import CredentialMetadata

        people_names: set[str] = set()
        people: dict[UUID, Person] = {}
        for stored_id, record in snapshot["data"]["people"].items():
            person = Person.from_dict(record)
            if str(person.person_id) != stored_id:
                raise ValueError("Stored Person identifier does not match its record")
            normalized_name = person.display_name.casefold()
            if normalized_name in people_names:
                raise ValueError("Stored Person display names must be unique")
            people_names.add(normalized_name)
            people[person.person_id] = person

        access_points: dict[UUID, AccessPoint] = {}
        for stored_id, record in snapshot["data"]["access_points"].items():
            if set(record) not in (
                _ACCESS_POINT_RECORD_FIELDS,
                _ACCESS_POINT_RECORD_FIELDS | {"open_enabled", "entry_action"},
            ):
                raise ValueError("Stored Access Point contains unexpected fields")
            access_point = AccessPoint.from_dict(record)
            if str(access_point.id) != stored_id:
                raise ValueError("Stored Access Point identifier does not match its record")
            if access_point.id in access_points:
                raise ValueError("Stored Access Point identifiers must be unique")
            access_points[access_point.id] = access_point

        access_device_ids: set[UUID] = set()
        home_assistant_device_ids: set[str] = set()
        zigbee_ieee_addresses: set[str] = set()
        zigbee2mqtt_topics: set[str] = set()
        for stored_id, record in snapshot["data"]["access_devices"].items():
            access_device = AccessDevice.from_dict(record)
            if str(access_device.id) != stored_id:
                raise ValueError("Stored Access Device identifier does not match its record")
            if access_device.id in access_device_ids:
                raise ValueError("Stored Access Device identifiers must be unique")
            if access_device.home_assistant_device_id in home_assistant_device_ids:
                raise ValueError("Home Assistant device is assigned to multiple Access Devices")
            if access_device.access_point_id not in access_points:
                raise ValueError("Stored Access Device references a missing Access Point")
            if (
                access_device.zigbee_ieee_address is not None
                and access_device.zigbee_ieee_address in zigbee_ieee_addresses
            ):
                raise ValueError("Zigbee device is assigned to multiple Access Devices")
            if (
                access_device.zigbee2mqtt_state_topic is not None
                and access_device.zigbee2mqtt_state_topic in zigbee2mqtt_topics
            ):
                raise ValueError("Zigbee2MQTT topic is assigned to multiple Access Devices")
            access_device_ids.add(access_device.id)
            home_assistant_device_ids.add(access_device.home_assistant_device_id)
            if access_device.zigbee_ieee_address is not None:
                zigbee_ieee_addresses.add(access_device.zigbee_ieee_address)
            if access_device.zigbee2mqtt_state_topic is not None:
                zigbee2mqtt_topics.add(access_device.zigbee2mqtt_state_topic)

        name_fallbacks = _validate_access_point_name_fallbacks(
            cast(dict[str, object], snapshot["data"]["settings"])
        )
        for access_point_id in name_fallbacks:
            fallback_access_point = access_points.get(UUID(access_point_id))
            if fallback_access_point is None or not _is_untouched_access_point_name_fallback(
                fallback_access_point
            ):
                raise ValueError("Stored Access Point name fallback marker is invalid")

        grant_ids: set[object] = set()
        grants: list[AccessGrant] = []
        for stored_key, record in snapshot["data"]["access_grants"].items():
            grant = AccessGrant.from_dict(record)
            expected_key = f"{grant.person_id}:{grant.access_point_id}"
            if stored_key != expected_key:
                raise ValueError("Stored Access Grant identifier does not match its record")
            if grant.access_grant_id in grant_ids:
                raise ValueError("Stored Access Grant identifiers must be unique")
            grant_ids.add(grant.access_grant_id)
            grants.append(grant)

        access_metadata_records: list[AccessMetadata] = []
        for stored_key, record in snapshot["data"]["access_metadata"].items():
            metadata = AccessMetadata.from_dict(record)
            expected_key = f"{metadata.person_id}:{metadata.access_point_id}"
            if stored_key != expected_key:
                raise ValueError("Stored access metadata identifier does not match its record")
            access_metadata_records.append(metadata)

        credential_people: set[UUID] = set()
        credential_ids: set[str] = set()
        credentials: list[CredentialMetadata] = []
        for stored_id, record in snapshot["data"]["credential_metadata"].items():
            credential = CredentialMetadata.from_dict(record)
            if str(credential.person_id) != stored_id:
                raise ValueError("Stored Credential Metadata identifier does not match its record")
            if credential.person_id not in people:
                raise ValueError("Stored Credential Metadata references a missing Person")
            if credential.person_id in credential_people:
                raise ValueError("Stored Person has multiple Credential Metadata records")
            credential_id = str(credential.credential_id)
            if credential_id in credential_ids:
                raise ValueError("Stored credential is assigned to multiple People")
            credential_people.add(credential.person_id)
            credential_ids.add(credential_id)
            credentials.append(credential)

        for credential in credentials:
            claimed_id = credential.credential_id.value
            if any(
                grant.person_id == credential.person_id and grant.credential_id != claimed_id
                for grant in grants
            ):
                raise ValueError(
                    "Stored Credential Metadata conflicts with its Person's Access Grants"
                )
            if any(
                grant.person_id != credential.person_id and grant.credential_id == claimed_id
                for grant in grants
            ):
                raise ValueError("Stored credential is referenced by another Person's Access Grant")
            if any(
                metadata.person_id == credential.person_id
                and (
                    metadata.vault_credential_id is None
                    or metadata.vault_credential_id.value != claimed_id
                )
                for metadata in access_metadata_records
            ):
                raise ValueError(
                    "Stored Credential Metadata conflicts with its Person's access metadata"
                )
            if any(
                metadata.person_id != credential.person_id
                and metadata.vault_credential_id is not None
                and metadata.vault_credential_id.value == claimed_id
                for metadata in access_metadata_records
            ):
                raise ValueError("Stored credential is referenced by another Person's metadata")

        schedule_names: set[str] = set()
        schedule_ids: set[UUID] = set()
        for stored_id, record in snapshot["data"]["schedules"].items():
            schedule = Schedule.from_dict(record)
            if str(schedule.schedule_id) != stored_id:
                raise ValueError("Stored Schedule identifier does not match its record")
            if schedule.schedule_id == PERMANENT_SCHEDULE_ID:
                if schedule != permanent_schedule():
                    raise ValueError("Stored Permanent Schedule must be canonical")
            elif schedule.name.casefold() == PERMANENT_SCHEDULE_NAME.casefold():
                raise ValueError("Stored user Schedule uses the reserved Permanent name")
            normalized_name = schedule.name.casefold()
            if normalized_name in schedule_names:
                raise ValueError("Stored Schedule names must be unique")
            schedule_names.add(normalized_name)
            schedule_ids.add(schedule.schedule_id)

        if PERMANENT_SCHEDULE_ID not in schedule_ids:
            raise ValueError("Stored Permanent Schedule is missing")
        for person in people.values():
            if person.schedule_id not in schedule_ids:
                raise ValueError("Stored Person references a missing Schedule")
        for grant in grants:
            if grant.person_id not in people:
                raise ValueError("Stored Access Grant references a missing Person")
            if grant.schedule_id not in schedule_ids:
                raise ValueError("Stored Access Grant references a missing Schedule")
            if grant.access_point_id not in access_points:
                raise ValueError("Stored Access Grant references a missing Access Point")

        for record in snapshot["data"]["access_metadata"].values():
            metadata = AccessMetadata.from_dict(record)
            if metadata.access_point_id not in access_points:
                raise ValueError("Stored access metadata references a missing Access Point")

        managed = _validate_managed_access_points(
            cast(dict[str, object], snapshot["data"]["settings"])
        )
        if any(UUID(access_point_id) not in access_points for access_point_id in managed):
            raise ValueError("Stored enrolment references a missing Access Point")

        synchronization_statuses: set[UUID] = set()
        for stored_id, record in snapshot["data"]["synchronization_statuses"].items():
            synchronization = AccessPointSynchronization.from_dict(record)
            if str(synchronization.access_point_id) != stored_id:
                raise ValueError(
                    "Stored synchronization status identifier does not match its record"
                )
            synchronization_statuses.add(synchronization.access_point_id)
        managed_ids = {
            UUID(access_point_id)
            for access_point_id, enrollment in managed.items()
            if cast(dict[str, object], enrollment)["managed"] is True
        }
        if synchronization_statuses != managed_ids:
            raise ValueError("Stored synchronization statuses must match managed Access Points")

        for stored_id, record in snapshot["data"]["synchronization_history"].items():
            event = SynchronizationHistoryEvent.from_dict(record)
            if str(event.event_id) != stored_id:
                raise ValueError("Stored synchronization history identifier does not match")

        for stored_id, record in snapshot["data"]["activity_events"].items():
            activity_event = ActivityEvent.from_dict(record)
            if str(activity_event.event_id) != stored_id:
                raise ValueError("Stored Activity Event identifier does not match")

        for stored_id, record in snapshot["data"]["lifecycle_operations"].items():
            operation = LifecycleOperation.from_dict(record)
            if str(operation.operation_id) != stored_id:
                raise ValueError("Stored lifecycle operation identifier does not match its record")
            if any(
                UUID(access_point_id) not in access_points
                for access_point_id in _stored_access_point_references(operation.payload)
            ):
                raise ValueError("Stored lifecycle operation references a missing Access Point")
        raw_notification_preferences = snapshot["data"]["settings"].get("notification_preferences")
        if raw_notification_preferences is not None:
            try:
                notification_preferences = NotificationPreferences.migrate_dict(
                    raw_notification_preferences
                )
            except (TypeError, ValueError):
                settings = snapshot["data"]["settings"]
                settings.setdefault(
                    _NOTIFICATION_PREFERENCES_RECOVERY_BACKUP_SETTING,
                    deepcopy(raw_notification_preferences),
                )
                notification_preferences = NotificationPreferences.defaults()
                _LOGGER.warning(
                    "Recovered invalid HomePASS notification preferences; "
                    "access-control records were not changed"
                )
            snapshot["data"]["settings"]["notification_preferences"] = cast(
                JsonValue,
                notification_preferences.to_dict(),
            )
        raw_property_settings = snapshot["data"]["settings"].get("property_settings")
        if raw_property_settings is not None:
            PropertySettings.from_dict(raw_property_settings)
        if any(
            UUID(access_point_id) not in access_points
            for access_point_id in _stored_access_point_references(snapshot["data"]["properties"])
        ):
            raise ValueError("Stored property data references a missing Access Point")
    except InvalidHomePassStorageError:
        raise
    except Exception as err:
        raise InvalidHomePassStorageError(
            "HomePASS storage contains invalid domain records"
        ) from err
    return snapshot


def _migrate_access_point_policy_schema(
    raw: dict[str, object],
) -> HomePassStorageData:
    """Materialize stable policy records for every retained Access Point reference."""
    from .models import AccessPoint, LifecycleOperation

    migrated = deepcopy(raw)
    metadata = cast(dict[str, object], migrated["metadata"])
    data = cast(dict[str, object], migrated["data"])
    settings = cast(dict[str, object], data["settings"])
    managed = _validate_managed_access_points(settings)
    referenced_ids = set(managed)

    try:
        for collection_name in ("access_grants", "access_metadata"):
            collection = cast(dict[str, object], data[collection_name])
            for record in collection.values():
                if not isinstance(record, dict):
                    raise ValueError(f"{collection_name} record must be an object")
                access_point_id = record.get("access_point_id")
                if not isinstance(access_point_id, str):
                    raise ValueError(f"{collection_name} record has no Access Point identifier")
                UUID(access_point_id)
                referenced_ids.add(access_point_id)

        lifecycle_records = cast(dict[str, object], data["lifecycle_operations"])
        for record in lifecycle_records.values():
            if not isinstance(record, dict):
                raise ValueError("lifecycle operation record must be an object")
            referenced_ids.update(
                _stored_access_point_references(LifecycleOperation.from_dict(record).payload)
            )
        referenced_ids.update(_stored_access_point_references(data["properties"]))

        records: dict[str, object] = {}
        for access_point_id in sorted(referenced_ids):
            identifier = UUID(access_point_id)
            display_name = (
                _LEGACY_ACCESS_POINT_DISPLAY_NAME
                if access_point_id == _LEGACY_ACCESS_POINT_ID
                else _MIGRATED_ACCESS_POINT_DISPLAY_NAME
            )
            records[access_point_id] = AccessPoint(
                id=identifier,
                display_name=display_name,
                enabled=True,
                created_at=_ACCESS_POINT_MIGRATION_TIMESTAMP,
                updated_at=_ACCESS_POINT_MIGRATION_TIMESTAMP,
            ).to_dict()
    except (KeyError, TypeError, ValueError) as err:
        raise MigrationError(f"Unable to migrate HomePASS Access Points: {err}") from err

    data["access_points"] = records
    settings[_ACCESS_POINT_NAME_FALLBACKS_SETTING] = {
        access_point_id: True for access_point_id in sorted(referenced_ids)
    }
    metadata["schema_version"] = 10
    return _migrate_schema_v10(migrated)


def _stored_access_point_references(value: object) -> set[str]:
    """Collect UUID values explicitly labeled as Access Point references."""
    references: set[str] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            if key == "access_point_id":
                if not isinstance(item, str):
                    raise ValueError("Access Point reference must be a UUID string")
                UUID(item)
                references.add(item)
            else:
                references.update(_stored_access_point_references(item))
    elif isinstance(value, list):
        for item in value:
            references.update(_stored_access_point_references(item))
    return references


def _is_untouched_access_point_name_fallback(access_point: object) -> bool:
    """Return whether a policy still has the exact synthetic migration values."""
    from .models import AccessPoint

    return (
        isinstance(access_point, AccessPoint)
        and access_point.display_name == _MIGRATED_ACCESS_POINT_DISPLAY_NAME
        and access_point.created_at == _ACCESS_POINT_MIGRATION_TIMESTAMP
        and access_point.updated_at == _ACCESS_POINT_MIGRATION_TIMESTAMP
    )


def _migrate_person_schedule_schema(raw: dict[str, object]) -> HomePassStorageData:
    """Add required Person and Access Grant Schedule references atomically."""
    from .models import Schedule
    from .models.schedule import PERMANENT_SCHEDULE_ID, permanent_schedule

    migrated = deepcopy(raw)
    metadata = cast(dict[str, object], migrated["metadata"])
    data = cast(dict[str, object], migrated["data"])
    people = cast(dict[str, object], data["people"])
    grants = cast(dict[str, object], data["access_grants"])
    schedules = cast(dict[str, object], data["schedules"])
    data.setdefault("lifecycle_operations", {})
    settings = cast(dict[str, object], data["settings"])
    settings.setdefault(
        _MANAGED_ACCESS_POINTS_SETTING,
        {_LEGACY_ACCESS_POINT_ID: {"discovery_key": None, "managed": True}},
    )

    permanent_id = str(PERMANENT_SCHEDULE_ID)
    schedules[permanent_id] = permanent_schedule().to_dict()
    known_schedule_ids: set[str] = set()
    try:
        for stored_id, record in schedules.items():
            if not isinstance(record, dict):
                raise ValueError("Schedule record must be an object")
            schedule = Schedule.from_dict(record)
            if str(schedule.schedule_id) != stored_id:
                raise ValueError("Stored Schedule identifier does not match its record")
            known_schedule_ids.add(stored_id)

        person_grants: dict[str, list[str]] = {person_id: [] for person_id in people}
        for record in grants.values():
            if not isinstance(record, dict):
                raise ValueError("Access Grant record must be an object")
            person_id = record.get("person_id")
            if not isinstance(person_id, str) or person_id not in people:
                raise ValueError("Access Grant references a missing Person")
            schedule_id = record.get("schedule_id")
            if schedule_id is None:
                schedule_id = permanent_id
                record["schedule_id"] = schedule_id
            if not isinstance(schedule_id, str) or schedule_id not in known_schedule_ids:
                raise ValueError("Access Grant references a missing Schedule")
            person_grants[person_id].append(schedule_id)

        for person_id, record in people.items():
            if not isinstance(record, dict):
                raise ValueError("Person record must be an object")
            if record.get("person_id") != person_id:
                raise ValueError("Stored Person identifier does not match its record")
            distinct_schedules = set(person_grants[person_id])
            record["schedule_id"] = (
                next(iter(distinct_schedules)) if len(distinct_schedules) == 1 else permanent_id
            )
    except (TypeError, ValueError) as err:
        raise MigrationError(f"Unable to migrate HomePASS person schedules: {err}") from err

    metadata["schema_version"] = STORAGE_SCHEMA_VERSION
    try:
        return _migrate_access_point_policy_schema(migrated)
    except InvalidHomePassStorageError as err:
        raise MigrationError("Unable to validate migrated HomePASS person schedules") from err


def _migrate_schema_v1(raw: object) -> HomePassStorageData:
    """Add the empty non-secret access metadata collection to schema 1."""
    data = _validate_root(raw, {"people", "properties", "settings"})
    _validate_record_collections(data, ("people", "properties"))
    settings = data["settings"]
    if not isinstance(settings, dict) or not _is_json_value(settings):
        raise InvalidHomePassStorageError("HomePASS storage settings must be a JSON object")

    migrated = deepcopy(cast(dict[str, object], raw))
    migrated_metadata = cast(dict[str, object], migrated["metadata"])
    migrated_data = cast(dict[str, object], migrated["data"])
    migrated_metadata["schema_version"] = STORAGE_SCHEMA_VERSION
    migrated_data["access_metadata"] = {}
    migrated_data["access_grants"] = {}
    migrated_data["schedules"] = {}
    return _migrate_person_schedule_schema(migrated)


def _migrate_schema_v2(raw: object) -> HomePassStorageData:
    """Create Access Grants for relationships already owned by HomePASS."""
    data = _validate_root(raw, {"people", "access_metadata", "properties", "settings"})
    _validate_record_collections(data, ("people", "access_metadata", "properties"))
    settings = data["settings"]
    if not isinstance(settings, dict) or not _is_json_value(settings):
        raise InvalidHomePassStorageError("HomePASS storage settings must be a JSON object")

    migrated = deepcopy(cast(dict[str, object], raw))
    migrated_metadata = cast(dict[str, object], migrated["metadata"])
    migrated_data = cast(dict[str, object], migrated["data"])
    raw_metadata = cast(dict[str, object], migrated_data["access_metadata"])
    grants: dict[str, object] = {}
    for relationship_key, record_value in raw_metadata.items():
        if not isinstance(record_value, dict):
            continue
        credential_id = record_value.get("vault_credential_id")
        if not isinstance(credential_id, str):
            continue
        person_id = record_value.get("person_id")
        access_point_id = record_value.get("access_point_id")
        created_at = record_value.get("created_at")
        updated_at = record_value.get("updated_at")
        if not all(
            isinstance(value, str) for value in (person_id, access_point_id, created_at, updated_at)
        ):
            raise InvalidHomePassStorageError("Access metadata cannot migrate to Access Grant")
        grants[relationship_key] = {
            "access_grant_id": str(uuid5(NAMESPACE_URL, f"homepass:{relationship_key}")),
            "person_id": person_id,
            "credential_id": credential_id,
            "access_point_id": access_point_id,
            "schedule_id": None,
            "enabled": True,
            "synchronization_status": "working",
            "created_at": created_at,
            "updated_at": updated_at,
        }
    migrated_metadata["schema_version"] = STORAGE_SCHEMA_VERSION
    migrated_data["access_grants"] = grants
    migrated_data["schedules"] = {}
    return _migrate_person_schedule_schema(migrated)


def _migrate_schema_v3(raw: object) -> HomePassStorageData:
    """Add durable synchronization state to existing Access Grants."""
    data = _validate_root(
        raw,
        {"people", "access_metadata", "access_grants", "properties", "settings"},
    )
    _validate_record_collections(data, ("people", "access_metadata", "access_grants", "properties"))
    settings = data["settings"]
    if not isinstance(settings, dict) or not _is_json_value(settings):
        raise InvalidHomePassStorageError("HomePASS storage settings must be a JSON object")

    migrated = deepcopy(cast(dict[str, object], raw))
    migrated_metadata = cast(dict[str, object], migrated["metadata"])
    migrated_data = cast(dict[str, object], migrated["data"])
    grants = cast(dict[str, object], migrated_data["access_grants"])
    for record_value in grants.values():
        if isinstance(record_value, dict):
            record_value.setdefault("synchronization_status", "working")
    migrated_data["schedules"] = {}
    migrated_metadata["schema_version"] = STORAGE_SCHEMA_VERSION
    return _migrate_person_schedule_schema(migrated)


def _migrate_schema_v4(raw: object) -> HomePassStorageData:
    """Add the empty Schedule collection to schema 4."""
    data = _validate_root(
        raw,
        {"people", "access_metadata", "access_grants", "properties", "settings"},
    )
    _validate_record_collections(data, ("people", "access_metadata", "access_grants", "properties"))
    settings = data["settings"]
    if not isinstance(settings, dict) or not _is_json_value(settings):
        raise InvalidHomePassStorageError("HomePASS storage settings must be a JSON object")

    migrated = deepcopy(cast(dict[str, object], raw))
    migrated_metadata = cast(dict[str, object], migrated["metadata"])
    migrated_data = cast(dict[str, object], migrated["data"])
    migrated_metadata["schema_version"] = STORAGE_SCHEMA_VERSION
    migrated_data["schedules"] = {}
    return _migrate_person_schedule_schema(migrated)


def _migrate_schema_v5(raw: object) -> HomePassStorageData:
    """Add required Person-owned Schedule references to schema 5."""
    data = _validate_root(
        raw,
        {
            "people",
            "access_metadata",
            "access_grants",
            "schedules",
            "properties",
            "settings",
        },
    )
    _validate_record_collections(
        data, ("people", "access_metadata", "access_grants", "schedules", "properties")
    )
    settings = data["settings"]
    if not isinstance(settings, dict) or not _is_json_value(settings):
        raise InvalidHomePassStorageError("HomePASS storage settings must be a JSON object")
    return _migrate_person_schedule_schema(deepcopy(cast(dict[str, object], raw)))


def _migrate_schema_v6(raw: object) -> HomePassStorageData:
    """Add the durable lifecycle operation journal to schema 6."""
    data = _validate_root(
        raw,
        {
            "people",
            "access_metadata",
            "access_grants",
            "schedules",
            "properties",
            "settings",
        },
    )
    _validate_record_collections(
        data, ("people", "access_metadata", "access_grants", "schedules", "properties")
    )
    settings = data["settings"]
    if not isinstance(settings, dict) or not _is_json_value(settings):
        raise InvalidHomePassStorageError("HomePASS storage settings must be a JSON object")
    migrated = deepcopy(cast(dict[str, object], raw))
    migrated_metadata = cast(dict[str, object], migrated["metadata"])
    migrated_data = cast(dict[str, object], migrated["data"])
    migrated_metadata["schema_version"] = STORAGE_SCHEMA_VERSION
    migrated_data["lifecycle_operations"] = {}
    settings = cast(dict[str, object], migrated_data["settings"])
    settings[_MANAGED_ACCESS_POINTS_SETTING] = {
        _LEGACY_ACCESS_POINT_ID: {"discovery_key": None, "managed": True}
    }
    return _migrate_access_point_policy_schema(migrated)


def _migrate_schema_v7(raw: object) -> HomePassStorageData:
    """Add the authoritative Vault credential revision to Access Metadata."""
    data = _validate_root(
        raw,
        {
            "people",
            "access_metadata",
            "access_grants",
            "schedules",
            "lifecycle_operations",
            "properties",
            "settings",
        },
    )
    _validate_record_collections(
        data,
        (
            "people",
            "access_metadata",
            "access_grants",
            "schedules",
            "lifecycle_operations",
            "properties",
        ),
    )
    migrated = deepcopy(cast(dict[str, object], raw))
    migrated_metadata = cast(dict[str, object], migrated["metadata"])
    migrated_data = cast(dict[str, object], migrated["data"])
    access_metadata = cast(dict[str, object], migrated_data["access_metadata"])
    for record in access_metadata.values():
        if not isinstance(record, dict):
            raise MigrationError("Unable to migrate credential revisions")
        record.setdefault("credential_revision", 1)
    settings = cast(dict[str, object], migrated_data["settings"])
    settings[_MANAGED_ACCESS_POINTS_SETTING] = {
        _LEGACY_ACCESS_POINT_ID: {"discovery_key": None, "managed": True}
    }
    migrated_metadata["schema_version"] = STORAGE_SCHEMA_VERSION
    return _migrate_access_point_policy_schema(migrated)


def _migrate_schema_v8(raw: object) -> HomePassStorageData:
    """Preserve the historically managed Garage lock as the sole enrolment."""
    migrated = deepcopy(cast(dict[str, object], raw))
    data = _validate_root(
        migrated,
        {
            "people",
            "access_metadata",
            "access_grants",
            "schedules",
            "lifecycle_operations",
            "properties",
            "settings",
        },
    )
    settings = cast(dict[str, object], data["settings"])
    settings[_MANAGED_ACCESS_POINTS_SETTING] = {
        _LEGACY_ACCESS_POINT_ID: {"discovery_key": None, "managed": True}
    }
    metadata = cast(dict[str, object], migrated["metadata"])
    metadata["schema_version"] = STORAGE_SCHEMA_VERSION
    return _migrate_access_point_policy_schema(migrated)


def _migrate_schema_v9(raw: object) -> HomePassStorageData:
    """Add durable Access Point policy definitions to schema 9."""
    data = _validate_root(
        raw,
        {
            "people",
            "access_metadata",
            "access_grants",
            "schedules",
            "lifecycle_operations",
            "properties",
            "settings",
        },
    )
    _validate_record_collections(
        data,
        (
            "people",
            "access_metadata",
            "access_grants",
            "schedules",
            "lifecycle_operations",
            "properties",
        ),
    )
    settings = data["settings"]
    if not isinstance(settings, dict) or not _is_json_value(settings):
        raise InvalidHomePassStorageError("HomePASS storage settings must be a JSON object")
    _validate_managed_access_points(settings)
    return _migrate_access_point_policy_schema(cast(dict[str, object], raw))


def _migrate_schema_v10(raw: object) -> HomePassStorageData:
    """Add canonical managed Access Point synchronization status to schema 10."""
    from .models import (
        AccessGrant,
        AccessMetadata,
        AccessPoint,
        AccessPointSynchronization,
        LifecycleOperation,
        LifecycleOperationStatus,
        SynchronizationStatus,
        aggregate_synchronization_status,
    )

    data = _validate_root(
        raw,
        {
            "people",
            "access_points",
            "access_metadata",
            "access_grants",
            "schedules",
            "lifecycle_operations",
            "properties",
            "settings",
        },
    )
    _validate_record_collections(
        data,
        (
            "people",
            "access_points",
            "access_metadata",
            "access_grants",
            "schedules",
            "lifecycle_operations",
            "properties",
        ),
    )
    settings = data["settings"]
    if not isinstance(settings, dict) or not _is_json_value(settings):
        raise InvalidHomePassStorageError("HomePASS storage settings must be a JSON object")
    managed = _validate_managed_access_points(settings)
    migrated = deepcopy(cast(dict[str, object], raw))
    migrated_metadata = cast(dict[str, object], migrated["metadata"])
    migrated_data = cast(dict[str, object], migrated["data"])
    legacy_statuses = {
        "healthy": SynchronizationStatus.SYNCHRONIZED,
        "working": SynchronizationStatus.SYNCHRONIZED,
        "synchronizing": SynchronizationStatus.SYNCHRONIZING,
        "pending_verification": SynchronizationStatus.PENDING,
        "out_of_sync": SynchronizationStatus.RETRY_REQUIRED,
        "needs_attention": SynchronizationStatus.MANUAL_ATTENTION_REQUIRED,
        "error": SynchronizationStatus.MANUAL_ATTENTION_REQUIRED,
    }
    try:
        for collection_name in ("access_metadata", "access_grants"):
            collection = cast(dict[str, object], migrated_data[collection_name])
            for raw_record in collection.values():
                if not isinstance(raw_record, dict):
                    raise ValueError("Synchronization evidence record must be an object")
                raw_status = raw_record.get("synchronization_status")
                if not isinstance(raw_status, str):
                    raise ValueError("Synchronization evidence status must be a string")
                status = legacy_statuses.get(raw_status)
                if status is None:
                    status = SynchronizationStatus(raw_status)
                raw_record["synchronization_status"] = status.value

        access_points = {
            access_point_id: AccessPoint.from_dict(record)
            for access_point_id, record in cast(
                dict[str, StorageRecord], migrated_data["access_points"]
            ).items()
        }
        metadata_records = tuple(
            AccessMetadata.from_dict(record)
            for record in cast(dict[str, StorageRecord], migrated_data["access_metadata"]).values()
        )
        grant_records = tuple(
            AccessGrant.from_dict(record)
            for record in cast(dict[str, StorageRecord], migrated_data["access_grants"]).values()
        )
        lifecycle_records = tuple(
            LifecycleOperation.from_dict(record)
            for record in cast(
                dict[str, StorageRecord], migrated_data["lifecycle_operations"]
            ).values()
        )
        lifecycle_evidence = {
            LifecycleOperationStatus.PENDING: SynchronizationStatus.PENDING,
            LifecycleOperationStatus.RUNNING: SynchronizationStatus.SYNCHRONIZING,
            LifecycleOperationStatus.WAITING_RETRY: SynchronizationStatus.RETRY_REQUIRED,
            LifecycleOperationStatus.FAILED: SynchronizationStatus.MANUAL_ATTENTION_REQUIRED,
            LifecycleOperationStatus.COMPLETED: SynchronizationStatus.SYNCHRONIZED,
        }
        records: dict[str, StorageRecord] = {}
        for access_point_id, enrollment in sorted(managed.items()):
            if cast(dict[str, object], enrollment)["managed"] is not True:
                continue
            access_point = access_points[access_point_id]
            identifier = UUID(access_point_id)
            evidence = [
                metadata.synchronization_status
                for metadata in metadata_records
                if metadata.access_point_id == identifier
            ]
            evidence.extend(
                grant.synchronization_status
                for grant in grant_records
                if grant.access_point_id == identifier
            )
            evaluated_at = access_point.updated_at
            for metadata in metadata_records:
                if metadata.access_point_id == identifier:
                    evaluated_at = max(evaluated_at, metadata.updated_at)
            for grant in grant_records:
                if grant.access_point_id == identifier:
                    evaluated_at = max(evaluated_at, grant.updated_at)
            for operation in lifecycle_records:
                if access_point_id not in _stored_access_point_references(operation.payload):
                    continue
                evaluated_at = max(evaluated_at, operation.updated_at)
                status = lifecycle_evidence.get(operation.status)
                if status is not None:
                    evidence.append(status)
            synchronization = AccessPointSynchronization(
                identifier,
                aggregate_synchronization_status(evidence),
                evaluated_at,
            )
            records[access_point_id] = cast(StorageRecord, synchronization.to_dict())
    except (KeyError, TypeError, ValueError) as err:
        raise MigrationError("Unable to migrate HomePASS synchronization status") from err

    migrated_data["synchronization_statuses"] = records
    migrated_data["synchronization_history"] = {}
    migrated_metadata["schema_version"] = 12
    return _migrate_schema_v12(migrated)


def _migrate_schema_v11(raw: object) -> HomePassStorageData:
    """Add bounded synchronization history without fabricating past events."""
    data = _validate_root(
        raw,
        {
            "people",
            "access_points",
            "access_metadata",
            "access_grants",
            "schedules",
            "lifecycle_operations",
            "synchronization_statuses",
            "properties",
            "settings",
        },
    )
    _validate_record_collections(
        data,
        (
            "people",
            "access_points",
            "access_metadata",
            "access_grants",
            "schedules",
            "lifecycle_operations",
            "synchronization_statuses",
            "properties",
        ),
    )
    migrated = deepcopy(cast(dict[str, object], raw))
    migrated_data = cast(dict[str, object], migrated["data"])
    migrated_data["synchronization_history"] = {}
    cast(dict[str, object], migrated["metadata"])["schema_version"] = 12
    return _migrate_schema_v12(migrated)


def _migrate_schema_v12(raw: object) -> HomePassStorageData:
    """Add empty Activity storage without fabricating historical events."""
    data = _validate_root(
        raw,
        {
            "people",
            "access_points",
            "access_metadata",
            "access_grants",
            "schedules",
            "lifecycle_operations",
            "synchronization_statuses",
            "synchronization_history",
            "properties",
            "settings",
        },
    )
    _validate_record_collections(
        data,
        (
            "people",
            "access_points",
            "access_metadata",
            "access_grants",
            "schedules",
            "lifecycle_operations",
            "synchronization_statuses",
            "synchronization_history",
            "properties",
        ),
    )
    migrated = deepcopy(cast(dict[str, object], raw))
    migrated_data = cast(dict[str, object], migrated["data"])
    migrated_data["activity_events"] = {}
    cast(dict[str, object], migrated["metadata"])["schema_version"] = 13
    return _migrate_schema_v13(migrated)


def _migrate_schema_v13(raw: object) -> HomePassStorageData:
    """Add User descriptions and person-scoped non-secret credential metadata."""
    from .models import AccessGrant, AccessMetadata
    from .vault import AccessMethod, CredentialMetadata, VaultCredentialId

    data = _validate_root(
        raw,
        {
            "people",
            "access_points",
            "access_metadata",
            "access_grants",
            "schedules",
            "lifecycle_operations",
            "synchronization_statuses",
            "synchronization_history",
            "activity_events",
            "properties",
            "settings",
        },
    )
    _validate_record_collections(
        data,
        (
            "people",
            "access_points",
            "access_metadata",
            "access_grants",
            "schedules",
            "lifecycle_operations",
            "synchronization_statuses",
            "synchronization_history",
            "activity_events",
            "properties",
        ),
    )
    migrated = deepcopy(cast(dict[str, object], raw))
    migrated_data = cast(dict[str, object], migrated["data"])
    people = cast(dict[str, object], migrated_data["people"])
    for record in people.values():
        if not isinstance(record, dict):
            raise MigrationError("Unable to migrate HomePASS User descriptions")
        record.setdefault("description", None)

    candidates: dict[str, list[AccessMetadata]] = {}
    grants_by_person: dict[str, dict[UUID, AccessGrant]] = {}
    incomplete_metadata_people: set[str] = set()
    credential_owners: dict[VaultCredentialId, set[str]] = {}
    person_credential_references: dict[str, set[VaultCredentialId]] = {}
    grant_records = cast(dict[str, object], migrated_data["access_grants"])
    metadata_records = cast(dict[str, object], migrated_data["access_metadata"])
    try:
        for _stored_key, record in grant_records.items():
            if not isinstance(record, dict):
                raise ValueError("Access Grant record must be an object")
            grant = AccessGrant.from_dict(record)
            person_id = str(grant.person_id)
            credential_id = VaultCredentialId(grant.credential_id)
            grants_by_person.setdefault(person_id, {})[grant.access_point_id] = grant
            credential_owners.setdefault(credential_id, set()).add(person_id)
            person_credential_references.setdefault(person_id, set()).add(credential_id)
        for _stored_key, record in metadata_records.items():
            if not isinstance(record, dict):
                raise ValueError("Access Metadata record must be an object")
            metadata = AccessMetadata.from_dict(record)
            person_id = str(metadata.person_id)
            if person_id not in people:
                # Schema 13 permitted retained synchronization metadata whose
                # Person had already been removed. Preserve it, but never create
                # a Person-level authority for a Person who no longer exists.
                if metadata.vault_credential_id is not None:
                    credential_owners.setdefault(metadata.vault_credential_id, set()).add(person_id)
                continue
            if metadata.vault_credential_id is None:
                incomplete_metadata_people.add(person_id)
                continue
            candidates.setdefault(person_id, []).append(metadata)
            credential_owners.setdefault(metadata.vault_credential_id, set()).add(person_id)
            person_credential_references.setdefault(person_id, set()).add(
                metadata.vault_credential_id
            )
        consistent_candidates: dict[str, tuple[VaultCredentialId, list[AccessMetadata]]] = {}
        for person_id, records in sorted(candidates.items()):
            if person_id in incomplete_metadata_people:
                # A missing legacy reference is ambiguous. Leave every
                # relationship intact and require explicit repair before a
                # Person-level credential may be claimed.
                continue
            metadata_by_access_point = {record.access_point_id: record for record in records}
            person_grants = grants_by_person.get(person_id, {})
            pairs_agree = set(metadata_by_access_point) == set(person_grants)
            if pairs_agree:
                for access_point_id, grant in person_grants.items():
                    metadata_credential_id = metadata_by_access_point[
                        access_point_id
                    ].vault_credential_id
                    if (
                        metadata_credential_id is None
                        or grant.credential_id != metadata_credential_id.value
                    ):
                        pairs_agree = False
                        break
            if not pairs_agree:
                # One-sided or pairwise-conflicting legacy relationships cannot
                # establish a Person-level authority safely.
                continue
            credential_ids = person_credential_references[person_id]
            if len(credential_ids) != 1:
                # Conflicting legacy relationships cannot truthfully establish a
                # Person-scoped credential. Access-point-scoped Reveal remains valid.
                continue
            credential_id = credential_ids.pop()
            assert credential_id is not None
            consistent_candidates[person_id] = (credential_id, records)

        credential_records: dict[str, object] = {}
        for person_id, (credential_id, records) in sorted(consistent_candidates.items()):
            if credential_owners[credential_id] != {person_id}:
                # A legacy credential shared across People cannot become either
                # Person's authority. Preserve every legacy relationship and leave
                # person-scoped Reveal unavailable instead of blocking migration.
                continue
            credential_records[person_id] = CredentialMetadata(
                credential_id=credential_id,
                person_id=records[0].person_id,
                access_method=AccessMethod.PIN,
                enabled=True,
                created_at=min(record.created_at for record in records),
                updated_at=max(record.updated_at for record in records),
            ).to_dict()
    except (TypeError, ValueError) as err:
        raise MigrationError("Unable to migrate HomePASS Credential Metadata") from err

    migrated_data["credential_metadata"] = credential_records
    cast(dict[str, object], migrated["metadata"])["schema_version"] = 14
    return _migrate_schema_v14(migrated)


def _migrate_schema_v14(raw: object) -> HomePassStorageData:
    """Remove only deterministic legacy credential-slot ownership orphans."""
    from .repositories.access_metadata import AccessMetadataRepository

    data = _validate_root(
        raw,
        {
            "people",
            "access_points",
            "access_metadata",
            "credential_metadata",
            "access_grants",
            "schedules",
            "lifecycle_operations",
            "synchronization_statuses",
            "synchronization_history",
            "activity_events",
            "properties",
            "settings",
        },
    )
    _validate_record_collections(
        data,
        (
            "people",
            "access_points",
            "access_metadata",
            "credential_metadata",
            "access_grants",
            "schedules",
            "lifecycle_operations",
            "synchronization_statuses",
            "synchronization_history",
            "activity_events",
            "properties",
        ),
    )
    migrated = deepcopy(cast(dict[str, object], raw))
    AccessMetadataRepository.repair_deterministic_orphans_in_snapshot(
        cast(HomePassStorageData, migrated)
    )
    cast(dict[str, object], migrated["metadata"])["schema_version"] = 15
    return _migrate_schema_v15(migrated)


def _migrate_schema_v15(raw: object) -> HomePassStorageData:
    """Add capability-based Home Assistant device bindings to managed doors."""
    _validate_root(
        raw,
        {
            "people",
            "access_points",
            "access_metadata",
            "credential_metadata",
            "access_grants",
            "schedules",
            "lifecycle_operations",
            "synchronization_statuses",
            "synchronization_history",
            "activity_events",
            "properties",
            "settings",
        },
    )
    migrated = deepcopy(cast(dict[str, object], raw))
    settings = cast(dict[str, object], cast(dict[str, object], migrated["data"])["settings"])
    records = cast(dict[str, object], settings[_MANAGED_ACCESS_POINTS_SETTING])
    for record in records.values():
        if not isinstance(record, dict):
            raise MigrationError("Unable to migrate managed HomePASS doors")
        record.update(
            {
                "control_entity_id": None,
                "status_entity_id": None,
                "control_profile": "lock",
                "status_inverted": False,
                "pulse_seconds": 1.0,
                "pin_capable": True,
                "nfc_capable": False,
                "device_id": None,
            }
        )
    cast(dict[str, object], migrated["metadata"])["schema_version"] = 16
    return _migrate_schema_v16(migrated)


def _migrate_schema_v16(raw: object) -> HomePassStorageData:
    """Enable NFC capability for every managed door with a command binding."""
    _validate_root(
        raw,
        {
            "people",
            "access_points",
            "access_metadata",
            "credential_metadata",
            "access_grants",
            "schedules",
            "lifecycle_operations",
            "synchronization_statuses",
            "synchronization_history",
            "activity_events",
            "properties",
            "settings",
        },
    )
    migrated = deepcopy(cast(dict[str, object], raw))
    settings = cast(dict[str, object], cast(dict[str, object], migrated["data"])["settings"])
    records = cast(dict[str, object], settings[_MANAGED_ACCESS_POINTS_SETTING])
    for record in records.values():
        if not isinstance(record, dict):
            raise MigrationError("Unable to migrate HomePASS NFC door capabilities")
        record["nfc_capable"] = record.get("managed") is True and (
            record.get("control_profile") != "garage_toggle"
            or record.get("status_entity_id") is not None
        )
    cast(dict[str, object], migrated["metadata"])["schema_version"] = 17
    return _migrate_schema_v17(migrated)


def _migrate_schema_v17(raw: object) -> HomePassStorageData:
    """Add HomePASS-managed accessory devices without changing existing Doors."""
    _validate_root(
        raw,
        {
            "people",
            "access_points",
            "access_metadata",
            "credential_metadata",
            "access_grants",
            "schedules",
            "lifecycle_operations",
            "synchronization_statuses",
            "synchronization_history",
            "activity_events",
            "properties",
            "settings",
        },
    )
    migrated = deepcopy(cast(dict[str, object], raw))
    data = cast(dict[str, object], migrated["data"])
    data["access_devices"] = {}
    cast(dict[str, object], migrated["metadata"])["schema_version"] = 18
    return _migrate_schema_v18(migrated)


def _migrate_schema_v18(raw: object) -> HomePassStorageData:
    """Add optional Zigbee2MQTT identity fields while preserving every ZHA record."""
    _validate_root(
        raw,
        {
            "people",
            "access_points",
            "access_devices",
            "access_metadata",
            "credential_metadata",
            "access_grants",
            "schedules",
            "lifecycle_operations",
            "synchronization_statuses",
            "synchronization_history",
            "activity_events",
            "properties",
            "settings",
        },
    )
    migrated = deepcopy(cast(dict[str, object], raw))
    records = cast(dict[str, object], cast(dict[str, object], migrated["data"])["access_devices"])
    for record in records.values():
        if not isinstance(record, dict):
            raise MigrationError("Unable to migrate HomePASS access-device transports")
        record.update(
            {
                "zigbee_ieee_address": None,
                "zigbee2mqtt_base_topic": None,
                "zigbee2mqtt_friendly_name": None,
            }
        )
    cast(dict[str, object], migrated["metadata"])["schema_version"] = STORAGE_SCHEMA_VERSION
    try:
        return _validate_domain_snapshot(migrated)
    except InvalidHomePassStorageError as err:
        raise MigrationError("Unable to migrate HomePASS access-device transports") from err


async def async_migrate_storage(raw: object) -> HomePassStorageData:
    """Migrate a storage payload to the current schema."""
    schema_version = _schema_version(raw)
    if schema_version == 1:
        return _migrate_schema_v1(raw)
    if schema_version == 2:
        return _migrate_schema_v2(raw)
    if schema_version == 3:
        return _migrate_schema_v3(raw)
    if schema_version == 4:
        return _migrate_schema_v4(raw)
    if schema_version == 5:
        return _migrate_schema_v5(raw)
    if schema_version == 6:
        return _migrate_schema_v6(raw)
    if schema_version == 7:
        return _migrate_schema_v7(raw)
    if schema_version == 8:
        return _migrate_schema_v8(raw)
    if schema_version == 9:
        return _migrate_schema_v9(raw)
    if schema_version == 10:
        return _migrate_schema_v10(raw)
    if schema_version == 11:
        return _migrate_schema_v11(raw)
    if schema_version == 12:
        return _migrate_schema_v12(raw)
    if schema_version == 13:
        return _migrate_schema_v13(raw)
    if schema_version == 14:
        return _migrate_schema_v14(raw)
    if schema_version == 15:
        return _migrate_schema_v15(raw)
    if schema_version == 16:
        return _migrate_schema_v16(raw)
    if schema_version == 17:
        return _migrate_schema_v17(raw)
    if schema_version == 18:
        return _migrate_schema_v18(raw)
    if schema_version != STORAGE_SCHEMA_VERSION:
        raise UnsupportedHomePassStorageVersionError(
            f"Unsupported HomePASS storage schema version: {schema_version}"
        )

    return _validate_domain_snapshot(raw)


class _HomePassStore(Store[HomePassStorageData]):
    """Home Assistant store with a HomePASS migration boundary."""

    async def _async_migrate_func(
        self,
        old_major_version: int,
        old_minor_version: int,
        old_data: HomePassStorageData,
    ) -> HomePassStorageData:
        """Migrate the Home Assistant storage wrapper."""
        if old_major_version != STORAGE_VERSION or old_minor_version != STORAGE_MINOR_VERSION:
            raise UnsupportedHomePassStorageVersionError(
                f"Unsupported HomePASS Store version: {old_major_version}.{old_minor_version}"
            )
        return await async_migrate_storage(old_data)


class HomePassStorageManager:
    """Manage lazy, versioned HomePASS persistence."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the storage manager without reading from disk."""
        self._store = _HomePassStore(
            hass,
            STORAGE_VERSION,
            STORAGE_KEY,
            atomic_writes=True,
            minor_version=STORAGE_MINOR_VERSION,
        )
        self._data: HomePassStorageData | None = None
        self._lock = asyncio.Lock()

    @property
    def loaded(self) -> bool:
        """Return whether storage has been loaded."""
        return self._data is not None

    async def async_load(self) -> HomePassStorageData:
        """Load storage on first access and return an isolated copy."""
        async with self._lock:
            data = await self._async_ensure_loaded()
            return deepcopy(data)

    async def async_save(self, data: HomePassStorageData) -> None:
        """Validate and atomically persist a complete storage payload."""
        validated = _validate_domain_snapshot(await async_migrate_storage(data))

        async with self._lock:
            await self._async_ensure_loaded()
            await self._store.async_save(validated)
            self._data = deepcopy(validated)

    async def async_transaction(
        self,
        mutator: StorageMutator[TransactionResultT],
    ) -> TransactionResultT:
        """Mutate one isolated snapshot and publish it after one successful write."""
        if _TRANSACTION_ACTIVE.get():
            raise NestedHomePassStorageTransactionError(
                "Nested HomePASS storage transactions are not supported"
            )
        if not callable(mutator):
            raise TypeError("HomePASS storage transaction mutator must be callable")

        transaction_token = _TRANSACTION_ACTIVE.set(True)
        try:
            async with self._lock:
                current = await self._async_ensure_loaded()
                working = deepcopy(current)
                result = mutator(working)
                if inspect.isawaitable(result):
                    if inspect.iscoroutine(result):
                        result.close()
                    raise InvalidHomePassStorageTransactionError(
                        "HomePASS storage transaction mutator must be synchronous"
                    )
                validated = _validate_domain_snapshot(working)
                await self._store.async_save(validated)
                self._data = deepcopy(validated)
                return result
        finally:
            _TRANSACTION_ACTIVE.reset(transaction_token)

    async def _async_ensure_loaded(self) -> HomePassStorageData:
        """Load and validate storage while the manager lock is held."""
        if self._data is None:
            stored = await self._store.async_load()
            self._data = _empty_storage() if stored is None else await async_migrate_storage(stored)
        return self._data
