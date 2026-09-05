"""Guided Nuki-app fingerprint enrollment and fail-closed event attribution."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING, TypedDict, cast
from uuid import UUID

from ..models import (
    AccessDriver,
    AccessGrant,
    AccessMetadata,
    AccessPoint,
    ActivityAccessMethod,
    ActivityActorType,
    ActivityEventType,
    ActivityNavigationKind,
    ActivityNavigationReference,
    ActivityOutcome,
    ActivitySource,
    Person,
    SynchronizationStatus,
)
from ..providers import ProviderAuditEvent
from .activity import ActivityEventProposal, ActivityService

if TYPE_CHECKING:
    from ..storage import HomePassStorageData, HomePassStorageManager
    from .activity_attribution import ActivityKeypadAttributionService

_SETTING = "nuki_fingerprint_enrollments"
_SUCCESS_ACTIONS = frozenset({"unlock", "unlatch", "lock_n_go_unlatch"})


class NukiFingerprintEnrollmentStatus(StrEnum):
    """Truthful state of the part of enrollment HomePASS can observe."""

    AWAITING_NUKI_APP = "awaiting_nuki_app"
    ENROLLED_UNVERIFIED = "enrolled_unverified"
    CONFIRMED = "confirmed"
    FAILED = "failed"


class NukiFingerprintEnrollmentData(TypedDict):
    """Persisted non-biometric enrollment relationship."""

    person_id: str
    access_point_id: str
    authorization_external_id: str
    status: str
    created_at: str
    updated_at: str
    confirmed_at: str | None


class NukiFingerprintViewData(TypedDict):
    """Safe administrator presentation for one Nuki Door."""

    access_point_id: str
    door_name: str
    status: str
    updated_at: str | None
    confirmed_at: str | None


@dataclass(frozen=True, slots=True)
class NukiFingerprintEnrollment:
    """A user-to-Nuki authorization link; never biometric material."""

    person_id: UUID
    access_point_id: UUID
    authorization_external_id: str
    status: NukiFingerprintEnrollmentStatus
    created_at: datetime
    updated_at: datetime
    confirmed_at: datetime | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.person_id, UUID) or not isinstance(self.access_point_id, UUID):
            raise TypeError("Nuki fingerprint identities must be UUIDs")
        external_id = self.authorization_external_id.strip()
        if not external_id.isdecimal() or int(external_id) < 1:
            raise ValueError("Nuki fingerprint authorization ID must be positive")
        if not isinstance(self.status, NukiFingerprintEnrollmentStatus):
            raise TypeError("Nuki fingerprint enrollment status is invalid")
        created_at = _timestamp(self.created_at, "created_at")
        updated_at = _timestamp(self.updated_at, "updated_at")
        confirmed_at = (
            None if self.confirmed_at is None else _timestamp(self.confirmed_at, "confirmed_at")
        )
        if updated_at < created_at or (confirmed_at is not None and confirmed_at < created_at):
            raise ValueError("Nuki fingerprint enrollment timestamps are inconsistent")
        object.__setattr__(self, "authorization_external_id", external_id)
        object.__setattr__(self, "created_at", created_at)
        object.__setattr__(self, "updated_at", updated_at)
        object.__setattr__(self, "confirmed_at", confirmed_at)

    def to_dict(self) -> NukiFingerprintEnrollmentData:
        return {
            "person_id": str(self.person_id),
            "access_point_id": str(self.access_point_id),
            "authorization_external_id": self.authorization_external_id,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "confirmed_at": self.confirmed_at.isoformat() if self.confirmed_at else None,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> NukiFingerprintEnrollment:
        return cls(
            person_id=UUID(_string(data, "person_id")),
            access_point_id=UUID(_string(data, "access_point_id")),
            authorization_external_id=_string(data, "authorization_external_id"),
            status=NukiFingerprintEnrollmentStatus(_string(data, "status")),
            created_at=datetime.fromisoformat(_string(data, "created_at")),
            updated_at=datetime.fromisoformat(_string(data, "updated_at")),
            confirmed_at=(
                datetime.fromisoformat(value)
                if isinstance((value := data.get("confirmed_at")), str)
                else None
            ),
        )


def _timestamp(value: datetime, name: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"Nuki fingerprint {name} must be timezone-aware")
    return value.astimezone(UTC)


def _string(data: Mapping[str, object], name: str) -> str:
    value = data.get(name)
    if not isinstance(value, str):
        raise TypeError(f"Nuki fingerprint {name} must be a string")
    return value


def _key(person_id: UUID, access_point_id: UUID) -> str:
    return f"{person_id}:{access_point_id}"


class NukiFingerprintService:
    """Coordinate the Nuki-app scan step without handling biometric data."""

    def __init__(
        self,
        storage: HomePassStorageManager,
        activity_service: ActivityService,
        attribution: ActivityKeypadAttributionService,
    ) -> None:
        self._storage = storage
        self._activity_service = activity_service
        self._attribution = attribution

    async def status_for_person(self, person_id: UUID) -> dict[str, object]:
        snapshot = await self._storage.async_load()
        person = self._person(snapshot, person_id)
        targets = self._eligible_targets(snapshot, person_id)
        records = self._records(snapshot)
        doors: list[NukiFingerprintViewData] = []
        for metadata, access_point in targets:
            record = records.get(_key(person_id, access_point.id))
            if record is not None and not self._matches_authorization(record, metadata):
                # A Nuki fingerprint belongs to one keypad authorization. If
                # access was removed and later recreated, the new authorization
                # must never inherit the old fingerprint's status.
                record = None
            status = record.status.value if record else "not_started"
            doors.append(
                {
                    "access_point_id": str(access_point.id),
                    "door_name": access_point.display_name,
                    "status": status,
                    "updated_at": record.updated_at.isoformat() if record else None,
                    "confirmed_at": record.confirmed_at.isoformat()
                    if record and record.confirmed_at
                    else None,
                }
            )
        return {
            "person_id": str(person.person_id),
            "fingerprint_data_stored": False,
            "doors": doors,
        }

    async def storage_summary(self, lock_entity_id: str) -> dict[str, object]:
        """Return HomePASS-known fingerprint links without claiming lock inventory."""
        snapshot = await self._storage.async_load()
        active_authorizations = {
            (metadata.person_id, metadata.access_point_id): metadata
            for raw in snapshot["data"]["access_metadata"].values()
            if (metadata := AccessMetadata.from_dict(raw)).driver is AccessDriver.NUKI
            and metadata.lock_entity_id == lock_entity_id
        }
        records = tuple(
            record
            for record in self._records(snapshot).values()
            if (metadata := active_authorizations.get((record.person_id, record.access_point_id)))
            is not None
            and self._matches_authorization(record, metadata)
        )
        people = snapshot["data"]["people"]
        access_points = snapshot["data"]["access_points"]
        entries: list[dict[str, object]] = []
        for record in sorted(
            records,
            key=lambda item: (
                str(item.access_point_id),
                str(item.person_id),
            ),
        ):
            person_raw = people.get(str(record.person_id))
            access_point_raw = access_points.get(str(record.access_point_id))
            person_name = (
                Person.from_dict(person_raw).display_name
                if isinstance(person_raw, Mapping)
                else "Unknown user"
            )
            door_name = (
                AccessPoint.from_dict(access_point_raw).display_name
                if isinstance(access_point_raw, Mapping)
                else "Unknown door"
            )
            entries.append(
                {
                    "person_name": person_name,
                    "door_name": door_name,
                    "nuki_id": record.authorization_external_id,
                    "status": record.status.value,
                }
            )
        return {
            "linked_count": len(entries),
            "entries": entries,
            "complete_lock_inventory_available": False,
        }

    async def start(self, person_id: UUID, access_point_id: UUID) -> dict[str, object]:
        now = datetime.now(UTC)

        def mutate(snapshot: HomePassStorageData) -> None:
            self._person(snapshot, person_id)
            metadata, _access_point = self._require_target(snapshot, person_id, access_point_id)
            settings = cast("dict[str, object]", snapshot["data"]["settings"])
            raw_records = settings.setdefault(_SETTING, {})
            if not isinstance(raw_records, dict):
                raise ValueError("Nuki fingerprint enrollment storage is invalid")
            record_key = _key(person_id, access_point_id)
            existing_raw = raw_records.get(record_key)
            existing = (
                NukiFingerprintEnrollment.from_dict(existing_raw)
                if isinstance(existing_raw, Mapping)
                else None
            )
            if (
                existing is not None
                and existing.status is NukiFingerprintEnrollmentStatus.CONFIRMED
                and self._matches_authorization(existing, metadata)
            ):
                return
            created_at = (
                existing.created_at
                if existing is not None and self._matches_authorization(existing, metadata)
                else now
            )
            raw_records[record_key] = NukiFingerprintEnrollment(
                person_id=person_id,
                access_point_id=access_point_id,
                authorization_external_id=str(metadata.slot),
                status=NukiFingerprintEnrollmentStatus.AWAITING_NUKI_APP,
                created_at=created_at,
                updated_at=now,
            ).to_dict()

        await self._storage.async_transaction(mutate)
        return await self.status_for_person(person_id)

    async def mark_nuki_app_complete(
        self, person_id: UUID, access_point_id: UUID
    ) -> dict[str, object]:
        now = datetime.now(UTC)

        def mutate(snapshot: HomePassStorageData) -> None:
            metadata, _access_point = self._require_target(snapshot, person_id, access_point_id)
            records = self._raw_records(snapshot)
            raw = records.get(_key(person_id, access_point_id))
            if not isinstance(raw, Mapping):
                raise ValueError("Start fingerprint setup in HomePASS first")
            current = NukiFingerprintEnrollment.from_dict(raw)
            if not self._matches_authorization(current, metadata):
                raise ValueError("Start fingerprint setup in HomePASS first")
            if current.status is NukiFingerprintEnrollmentStatus.CONFIRMED:
                return
            records[_key(person_id, access_point_id)] = NukiFingerprintEnrollment(
                person_id=current.person_id,
                access_point_id=current.access_point_id,
                authorization_external_id=current.authorization_external_id,
                status=NukiFingerprintEnrollmentStatus.ENROLLED_UNVERIFIED,
                created_at=current.created_at,
                updated_at=now,
            ).to_dict()

        await self._storage.async_transaction(mutate)
        return await self.status_for_person(person_id)

    @staticmethod
    def _matches_authorization(record: NukiFingerprintEnrollment, metadata: AccessMetadata) -> bool:
        """Require both the current Nuki ID and the current access lifecycle."""
        return (
            record.authorization_external_id == str(metadata.slot)
            and record.updated_at >= metadata.created_at
        )

    async def remove_access_link(self, person_id: UUID, access_point_id: UUID) -> None:
        """Forget attribution after its Nuki keypad authorization is deleted."""

        def mutate(snapshot: HomePassStorageData) -> None:
            raw = snapshot["data"]["settings"].get(_SETTING)
            if raw is None:
                return
            if not isinstance(raw, dict):
                raise ValueError("Nuki fingerprint enrollment storage is invalid")
            raw.pop(_key(person_id, access_point_id), None)

        await self._storage.async_transaction(mutate)

    async def observe_provider_event(
        self,
        access_point_id: UUID,
        event: ProviderAuditEvent,
        *,
        record_activity: bool = True,
    ) -> bool:
        """Confirm and record one fingerprint unlock when authorization evidence matches."""
        if (
            not isinstance(event, ProviderAuditEvent)
            or event.source != "fingerprint"
            or event.outcome != "success"
            or event.action not in _SUCCESS_ACTIONS
            or event.authorization_external_id is None
            or not event.authorization_external_id.isdecimal()
        ):
            return False
        slot = int(event.authorization_external_id)
        person = await self._attribution.resolve_person(access_point_id, slot)
        if person is None:
            return False
        snapshot = await self._storage.async_load()
        access_point = AccessPoint.from_dict(
            snapshot["data"]["access_points"][str(access_point_id)]
        )
        records = self._records(snapshot)
        current = records.get(_key(person.person_id, access_point_id))
        if current is None or current.authorization_external_id != event.authorization_external_id:
            return False
        if event.occurred_at < current.updated_at:
            return False
        if current.status is not NukiFingerprintEnrollmentStatus.CONFIRMED:
            now = datetime.now(UTC)

            def confirm(working: HomePassStorageData) -> None:
                raw_records = self._raw_records(working)
                raw = raw_records.get(_key(person.person_id, access_point_id))
                if not isinstance(raw, Mapping):
                    return
                latest = NukiFingerprintEnrollment.from_dict(raw)
                if latest.authorization_external_id != event.authorization_external_id:
                    return
                raw_records[_key(person.person_id, access_point_id)] = NukiFingerprintEnrollment(
                    person_id=latest.person_id,
                    access_point_id=latest.access_point_id,
                    authorization_external_id=latest.authorization_external_id,
                    status=NukiFingerprintEnrollmentStatus.CONFIRMED,
                    created_at=latest.created_at,
                    updated_at=now,
                    confirmed_at=now,
                ).to_dict()

            await self._storage.async_transaction(confirm)
        if not record_activity:
            return True
        await self._activity_service.record(
            ActivityEventProposal(
                event_type=ActivityEventType.DOOR_UNLOCKED,
                occurred_at=event.occurred_at,
                source=ActivitySource.EXTERNAL,
                actor_type=ActivityActorType.PERSON,
                door_id=access_point.id,
                door_name=access_point.display_name,
                person_id=person.person_id,
                person_name=person.display_name,
                actor_id=person.person_id,
                actor_name=person.display_name,
                access_method=ActivityAccessMethod.FINGERPRINT,
                outcome=ActivityOutcome.SUCCEEDED,
                attributes={},
                navigation=(
                    ActivityNavigationReference(ActivityNavigationKind.DOOR, access_point.id),
                    ActivityNavigationReference(ActivityNavigationKind.PERSON, person.person_id),
                ),
                source_event_key=f"nuki:{access_point.id}:{event.external_id}",
            )
        )
        return True

    @staticmethod
    def _person(snapshot: HomePassStorageData, person_id: UUID) -> Person:
        try:
            person = Person.from_dict(snapshot["data"]["people"][str(person_id)])
        except KeyError as err:
            raise ValueError("HomePASS User is invalid") from err
        if person.person_id != person_id:
            raise ValueError("HomePASS User is invalid")
        return person

    @classmethod
    def _require_target(
        cls, snapshot: HomePassStorageData, person_id: UUID, access_point_id: UUID
    ) -> tuple[AccessMetadata, AccessPoint]:
        matches = [
            target
            for target in cls._eligible_targets(snapshot, person_id)
            if target[1].id == access_point_id
        ]
        if len(matches) != 1:
            raise ValueError("This user needs synchronized PIN access to this Nuki Door first")
        return matches[0]

    @staticmethod
    def _eligible_targets(
        snapshot: HomePassStorageData, person_id: UUID
    ) -> tuple[tuple[AccessMetadata, AccessPoint], ...]:
        data = snapshot["data"]
        grants = tuple(AccessGrant.from_dict(raw) for raw in data["access_grants"].values())
        managed = data["settings"].get("managed_access_points", {})
        results: list[tuple[AccessMetadata, AccessPoint]] = []
        for raw in data["access_metadata"].values():
            metadata = AccessMetadata.from_dict(raw)
            if (
                metadata.person_id != person_id
                or metadata.driver is not AccessDriver.NUKI
                or metadata.synchronization_status is not SynchronizationStatus.SYNCHRONIZED
                or metadata.vault_credential_id is None
            ):
                continue
            matching_grants = [
                grant
                for grant in grants
                if grant.person_id == person_id
                and grant.access_point_id == metadata.access_point_id
                and grant.credential_id == metadata.vault_credential_id.value
                and grant.synchronization_status is SynchronizationStatus.SYNCHRONIZED
            ]
            enrollment = (
                managed.get(str(metadata.access_point_id)) if isinstance(managed, Mapping) else None
            )
            if (
                len(matching_grants) != 1
                or not isinstance(enrollment, Mapping)
                or enrollment.get("managed") is not True
            ):
                continue
            try:
                access_point = AccessPoint.from_dict(
                    data["access_points"][str(metadata.access_point_id)]
                )
            except KeyError:
                continue
            if access_point.enabled:
                results.append((metadata, access_point))
        return tuple(results)

    @staticmethod
    def _raw_records(snapshot: HomePassStorageData) -> dict[str, object]:
        settings = cast("dict[str, object]", snapshot["data"]["settings"])
        raw = settings.setdefault(_SETTING, {})
        if not isinstance(raw, dict):
            raise ValueError("Nuki fingerprint enrollment storage is invalid")
        return raw

    @staticmethod
    def _records(snapshot: HomePassStorageData) -> dict[str, NukiFingerprintEnrollment]:
        raw = snapshot["data"]["settings"].get(_SETTING, {})
        if not isinstance(raw, Mapping):
            raise ValueError("Nuki fingerprint enrollment storage is invalid")
        return {
            key: NukiFingerprintEnrollment.from_dict(value)
            for key, value in raw.items()
            if isinstance(key, str) and isinstance(value, Mapping)
        }


__all__ = [
    "NukiFingerprintEnrollment",
    "NukiFingerprintEnrollmentStatus",
    "NukiFingerprintService",
]
