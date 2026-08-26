"""Persistence for explicitly managed Access Point enrolments."""

from __future__ import annotations

from datetime import datetime
from typing import cast
from uuid import UUID

from ..models import AccessPoint, AccessPointSynchronization, SynchronizationStatus
from ..services.access_point import AccessPointEnrollment
from ..storage import HomePassStorageData, HomePassStorageManager, StorageRecord

_SETTING = "managed_access_points"
_NAME_FALLBACKS_SETTING = "access_point_name_fallbacks"


class AccessPointEnrollmentRepository:
    """Persist the minimal stable relationship between discovery and HomePASS."""

    def __init__(self, storage: HomePassStorageManager) -> None:
        self._storage = storage

    async def list_all(self) -> tuple[AccessPointEnrollment, ...]:
        data = await self._storage.async_load()
        records = cast(dict[str, object], data["data"]["settings"][_SETTING])
        return tuple(
            AccessPointEnrollment(
                access_point_id=UUID(identifier),
                discovery_key=cast(dict[str, object], record)["discovery_key"],
                managed=cast(dict[str, object], record)["managed"],
                control_entity_id=cast(dict[str, object], record)["control_entity_id"],
                status_entity_id=cast(dict[str, object], record)["status_entity_id"],
                control_profile=cast(dict[str, object], record)["control_profile"],
                status_inverted=cast(dict[str, object], record)["status_inverted"],
                pulse_seconds=cast(dict[str, object], record)["pulse_seconds"],
                pin_capable=cast(dict[str, object], record)["pin_capable"],
                nfc_capable=cast(dict[str, object], record)["nfc_capable"],
                device_id=cast(dict[str, object], record)["device_id"],
            )
            for identifier, record in sorted(records.items())
        )

    async def upsert(
        self,
        enrollment: AccessPointEnrollment,
        access_point: AccessPoint,
        *,
        expected_policy_updated_at: datetime | None = None,
        clear_name_fallback: bool = False,
    ) -> AccessPointEnrollment:
        """Persist policy definition and enrolment in one shared transaction."""
        if enrollment.access_point_id != access_point.id:
            raise ValueError("Access Point enrolment and policy identifiers must match")

        def mutate(data: HomePassStorageData) -> None:
            records = cast(dict[str, object], data["data"]["settings"][_SETTING])
            existing_record = data["data"]["access_points"].get(str(access_point.id))
            if existing_record is not None:
                existing = AccessPoint.from_dict(existing_record)
                if expected_policy_updated_at is None:
                    if access_point != existing:
                        raise ValueError(
                            "Existing Access Point policy update requires an expectation"
                        )
                elif existing.updated_at != expected_policy_updated_at:
                    raise ValueError("Access Point policy changed concurrently")
                if access_point.created_at != existing.created_at:
                    raise ValueError("Access Point created_at cannot be changed")
                if access_point.updated_at < existing.updated_at:
                    raise ValueError("Access Point updated_at cannot move backwards")
            data["data"]["access_points"][str(access_point.id)] = cast(
                StorageRecord, access_point.to_dict()
            )
            if clear_name_fallback:
                fallbacks = cast(
                    dict[str, object],
                    data["data"]["settings"].setdefault(_NAME_FALLBACKS_SETTING, {}),
                )
                if fallbacks.pop(str(access_point.id), None) is not True:
                    raise ValueError("Access Point name fallback is no longer eligible")
            records[str(enrollment.access_point_id)] = {
                "discovery_key": enrollment.discovery_key,
                "managed": enrollment.managed,
                "control_entity_id": enrollment.control_entity_id,
                "status_entity_id": enrollment.status_entity_id,
                "control_profile": enrollment.control_profile,
                "status_inverted": enrollment.status_inverted,
                "pulse_seconds": enrollment.pulse_seconds,
                "pin_capable": enrollment.pin_capable,
                "nfc_capable": enrollment.nfc_capable,
                "device_id": enrollment.device_id,
            }
            synchronization_statuses = data["data"]["synchronization_statuses"]
            if enrollment.managed:
                synchronization_statuses.setdefault(
                    str(enrollment.access_point_id),
                    cast(
                        StorageRecord,
                        AccessPointSynchronization(
                            enrollment.access_point_id,
                            SynchronizationStatus.UNKNOWN,
                            access_point.updated_at,
                        ).to_dict(),
                    ),
                )
            else:
                synchronization_statuses.pop(str(enrollment.access_point_id), None)

        await self._storage.async_transaction(mutate)
        return enrollment

    async def remove(self, access_point_id: UUID) -> None:
        def mutate(data: HomePassStorageData) -> None:
            records = cast(dict[str, object], data["data"]["settings"][_SETTING])
            record = records.get(str(access_point_id))
            if isinstance(record, dict):
                record["managed"] = False
                data["data"]["synchronization_statuses"].pop(str(access_point_id), None)

        await self._storage.async_transaction(mutate)
