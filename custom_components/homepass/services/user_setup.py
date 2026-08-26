"""Guided User setup and add-only multi-door assignment orchestration."""

from __future__ import annotations

import asyncio
import logging
import secrets
from collections.abc import Mapping
from contextlib import suppress
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import NAMESPACE_URL, UUID, uuid5

from ..exceptions import (
    AccessUpdateError,
    CredentialAuthorityConflictError,
    DuplicatePersonError,
    PersonNotFoundError,
)
from ..models import AccessGrant, AccessPoint, ActivityEventType, Person, Schedule
from ..models.schedule import PERMANENT_SCHEDULE_ID
from ..repositories import CredentialMetadataRepository
from ..storage import HomePassStorageData, HomePassStorageManager, JsonValue, StorageRecord
from ..vault import AccessMethod, CredentialMetadata, CredentialVaultProtocol, VaultCredentialId
from .access_management import AccessManagementService, AccessUpdateResult
from .access_point import AccessPointService
from .activity_producer import ActivityProducer

_SETUP_REQUESTS_SETTING = "user_setup_requests"
_ACCESS_REQUESTS_SETTING = "user_access_requests"
_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class UserAssignmentResult:
    """PIN-safe result for one requested door assignment."""

    access_point_id: UUID
    display_name: str
    status: str
    message: str | None = None


@dataclass(frozen=True, slots=True)
class UserSetupResult:
    """PIN-safe guided creation result."""

    person: Person
    assignments: tuple[UserAssignmentResult, ...]
    status: str
    attention: bool
    repeated: bool = False


@dataclass(frozen=True, slots=True)
class UserSetupOptions:
    """Stable policy choices used by the guided workflow."""

    access_points: tuple[dict[str, JsonValue], ...]
    schedules: tuple[Schedule, ...]


class UserSetupService:
    """Own one secure backend boundary for guided User workflows."""

    def __init__(
        self,
        storage: HomePassStorageManager,
        access_point_service: AccessPointService,
        access_management_service: AccessManagementService,
        credential_vault: CredentialVaultProtocol,
        credential_metadata_repository: CredentialMetadataRepository,
        activity_producer: ActivityProducer | None = None,
    ) -> None:
        self._storage = storage
        self._access_point_service = access_point_service
        self._access_management_service = access_management_service
        self._credential_vault = credential_vault
        self._credential_metadata_repository = credential_metadata_repository
        self._activity_producer = activity_producer
        self._lock = asyncio.Lock()

    async def get_options(self) -> UserSetupOptions:
        """Return durable doors and Schedules from one isolated snapshot."""
        snapshot = await self._storage.async_load()
        managed = snapshot["data"]["settings"].get("managed_access_points", {})
        managed_records = managed if isinstance(managed, dict) else {}
        runtime_capabilities: dict[str, tuple[bool, bool]] = {}
        try:
            summaries = await self._access_point_service.list_access_point_summaries()
            runtime_capabilities = {
                str(summary.access_point.id): (summary.pin_capable, summary.nfc_capable)
                for summary in summaries
            }
        except Exception:
            # Durable options remain available while Home Assistant discovery is restarting.
            runtime_capabilities = {}
        access_points: list[dict[str, JsonValue]] = []
        for identifier, record in snapshot["data"]["access_points"].items():
            enrollment = managed_records.get(identifier)
            if not isinstance(enrollment, dict) or enrollment.get("managed") is not True:
                continue
            access_point = self._access_point_from_record(record)
            stored_capabilities = (
                enrollment.get("pin_capable", True) is True,
                enrollment.get("nfc_capable", True) is True,
            )
            pin_capable, nfc_capable = runtime_capabilities.get(
                identifier,
                stored_capabilities,
            )
            access_points.append(
                {
                    "access_point_id": str(access_point.id),
                    "display_name": access_point.display_name,
                    "enabled": access_point.enabled,
                    "eligible": access_point.enabled and pin_capable,
                    "pin_capable": pin_capable,
                    "nfc_capable": nfc_capable,
                }
            )
        access_points.sort(
            key=lambda item: (
                cast(str, item["display_name"]).casefold(),
                cast(str, item["access_point_id"]),
            )
        )
        schedules = tuple(
            sorted(
                (Schedule.from_dict(record) for record in snapshot["data"]["schedules"].values()),
                key=lambda schedule: (
                    schedule.schedule_id != PERMANENT_SCHEDULE_ID,
                    schedule.name.casefold(),
                    str(schedule.schedule_id),
                ),
            )
        )
        return UserSetupOptions(tuple(access_points), schedules)

    async def create_user(
        self,
        *,
        request_id: UUID,
        display_name: str,
        description: str | None,
        notes: str | None,
        enabled: bool,
        pin: str | None,
        access_point_ids: tuple[UUID, ...],
        schedule_id: UUID = PERMANENT_SCHEDULE_ID,
        new_schedule: Schedule | None = None,
    ) -> UserSetupResult:
        """Create core objects once, then provision selected doors once as one operation."""
        if pin is not None:
            self._validate_pin(pin)
        if access_point_ids and pin is None:
            raise ValueError("Enter a PIN before assigning keypad Door access")
        if len(access_point_ids) != len(set(access_point_ids)):
            raise ValueError("Door selections must be unique")
        if not access_point_ids and (
            schedule_id != PERMANENT_SCHEDULE_ID or new_schedule is not None
        ):
            raise ValueError("Choose a door before selecting a Schedule")
        if new_schedule is not None and not new_schedule.enabled:
            raise ValueError("Selected Schedule must be enabled")
        async with self._lock:
            now = datetime.now(UTC)
            person_id = uuid5(NAMESPACE_URL, f"homepass:user-setup:{request_id}:person")
            candidate = Person(
                person_id=person_id,
                display_name=display_name,
                description=description,
                notes=notes,
                enabled=enabled,
                schedule_id=(new_schedule.schedule_id if new_schedule is not None else schedule_id),
                created_at=now,
                updated_at=now,
            )
            context = self._setup_context(candidate, access_point_ids, new_schedule, pin=pin)
            existing = await self._request_record(_SETUP_REQUESTS_SETTING, request_id)
            if existing is not None:
                person = await self._validate_setup_replay(existing, context, pin)
                return await self._finish_assignments(
                    person,
                    access_point_ids,
                    repeated=True,
                    request_collection=_SETUP_REQUESTS_SETTING,
                    request_id=request_id,
                    existing_record=existing,
                )

            credential_id = None if pin is None else await self._credential_vault.store(pin)
            try:
                person = candidate
                credential = (
                    None
                    if credential_id is None
                    else CredentialMetadata(
                        credential_id=credential_id,
                        person_id=person_id,
                        access_method=AccessMethod.PIN,
                        enabled=True,
                        created_at=now,
                        updated_at=now,
                    )
                )
                await self._storage.async_transaction(
                    lambda storage: self._create_core(
                        storage,
                        request_id=request_id,
                        person=person,
                        credential=credential,
                        new_schedule=new_schedule,
                        access_point_ids=access_point_ids,
                        context=context,
                    )
                )
            except Exception:
                if credential_id is not None:
                    with suppress(Exception):
                        await self._credential_vault.delete(credential_id)
                raise

            if self._activity_producer is not None:
                await self._activity_producer.record(
                    ActivityEventType.PERSON_ADDED,
                    occurred_at=person.created_at,
                    source_event_key=f"user-setup:{request_id}:person-created",
                    person=person,
                )
            return await self._finish_assignments(
                person,
                access_point_ids,
                credential_id=credential_id,
                plaintext=pin,
                repeated=False,
                request_collection=_SETUP_REQUESTS_SETTING,
                request_id=request_id,
            )

    async def assign_user_access(
        self,
        *,
        request_id: UUID,
        person_id: UUID,
        access_point_ids: tuple[UUID, ...],
        schedule_id: UUID,
        pin: str | None = None,
        new_schedule: Schedule | None = None,
    ) -> UserSetupResult:
        """Repair PIN authority and add doors without replacing an existing Grant."""
        if not access_point_ids and pin is None:
            raise ValueError("Choose at least one door or enter a PIN")
        if len(access_point_ids) != len(set(access_point_ids)):
            raise ValueError("Door selections must be unique")
        if pin is not None:
            self._validate_pin(pin)
        if new_schedule is not None and not new_schedule.enabled:
            raise ValueError("Selected Schedule must be enabled")
        if new_schedule is not None and not access_point_ids:
            raise ValueError("Choose a door before creating a Schedule")
        async with self._lock:
            context: dict[str, object] = {
                "person_id": str(person_id),
                "access_point_ids": sorted(str(value) for value in access_point_ids),
                "schedule_id": str(
                    new_schedule.schedule_id if new_schedule is not None else schedule_id
                ),
                "schedule_definition": self._schedule_definition(new_schedule),
                "pin_intent": "provided" if pin is not None else "reuse",
            }
            existing = await self._request_record(_ACCESS_REQUESTS_SETTING, request_id)
            if existing is not None:
                if existing.get("context") != context:
                    raise ValueError("This request was already used for different access details")
                person = await self._person_from_request(existing)
                if pin is not None:
                    await self._validate_access_replay(person, pin)
                return await self._finish_assignments(
                    person,
                    access_point_ids,
                    repeated=True,
                    request_collection=_ACCESS_REQUESTS_SETTING,
                    request_id=request_id,
                    existing_record=existing,
                )
            snapshot = await self._storage.async_load()
            if str(person_id) not in snapshot["data"]["people"]:
                raise PersonNotFoundError(str(person_id))
            authority = CredentialMetadataRepository._resolve_for_provisioning(snapshot, person_id)
            created_credential = False
            credential_id = None if authority is None else authority.credential_id
            credential: CredentialMetadata | None = None
            if authority is None:
                if pin is None:
                    raise ValueError("This User does not yet have a PIN")
                now = datetime.now(UTC)
                credential_id = await self._credential_vault.store(pin)
                created_credential = True
                credential = CredentialMetadata(
                    credential_id=credential_id,
                    person_id=person_id,
                    access_method=AccessMethod.PIN,
                    enabled=True,
                    created_at=now,
                    updated_at=now,
                )
            elif pin is not None:
                stored_pin = await self._credential_vault.retrieve(authority.credential_id)
                try:
                    if not secrets.compare_digest(pin, stored_pin):
                        raise ValueError("Use Change PIN before assigning a different PIN")
                finally:
                    stored_pin = ""
            try:
                person = await self._prepare_access_request(
                    request_id,
                    person_id,
                    schedule_id,
                    access_point_ids,
                    context,
                    credential=credential,
                    expected_credential_id=credential_id,
                    new_schedule=new_schedule,
                )
            except Exception:
                if created_credential and credential_id is not None:
                    with suppress(Exception):
                        await self._credential_vault.delete(credential_id)
                raise
            return await self._finish_assignments(
                person,
                access_point_ids,
                credential_id=credential_id,
                plaintext=pin,
                repeated=False,
                request_collection=_ACCESS_REQUESTS_SETTING,
                request_id=request_id,
            )

    async def _finish_assignments(
        self,
        person: Person,
        access_point_ids: tuple[UUID, ...],
        *,
        credential_id: VaultCredentialId | None = None,
        plaintext: str | None = None,
        repeated: bool,
        request_collection: str,
        request_id: UUID,
        existing_record: dict[str, object] | None = None,
    ) -> UserSetupResult:
        if existing_record is not None:
            state = existing_record.get("state")
            if state in {"completed", "failed", "needs_attention"}:
                return self._saved_result(person, existing_record, repeated=True)
        if not access_point_ids:
            no_door_result = UserSetupResult(person, (), "completed", False, repeated)
            await self._save_request_result(request_collection, request_id, no_door_result)
            return no_door_result
        names = {
            access_point.id: access_point.display_name
            for access_point in await self._access_point_service.list_access_points()
        }
        if existing_record is not None and existing_record.get("state") == "provisioning":
            interrupted = UserSetupResult(
                person,
                tuple(
                    UserAssignmentResult(
                        identifier,
                        names.get(identifier, "Door"),
                        "needs_attention",
                        "Synchronization needs attention.",
                    )
                    for identifier in access_point_ids
                ),
                "needs_attention",
                True,
                True,
            )
            await self._save_request_result(request_collection, request_id, interrupted)
            return interrupted
        current_ids = set(
            await self._access_management_service.current_access_point_ids(person.person_id)
        )
        if plaintext is None:
            credential = await self._credential_metadata_repository.resolve_for_provisioning(
                person.person_id
            )
            if credential is not None:
                if credential_id is not None and credential_id != credential.credential_id:
                    raise CredentialAuthorityConflictError()
                credential_id = credential.credential_id
                plaintext = await self._credential_vault.retrieve(credential_id)
        await self._mark_request_provisioning(request_collection, request_id)
        try:
            access_result = await self._access_management_service.add_access(
                person.person_id,
                access_point_ids,
                credential_id=credential_id,
                plaintext=plaintext,
            )
        except Exception as err:
            # AccessManagementService normally converts operation failures into a
            # typed AccessUpdateError.  Its pre-device validation paths and
            # post-persistence observers can still raise other exceptions.  Resolve
            # the terminal result from durable relationship state so the request is
            # never stranded in "provisioning" and never claims unsaved access.
            _LOGGER.error(
                "User assignment failed request_id=%s person_id=%s request_collection=%s "
                "access_point_count=%s exception_type=%s stage=%s failure_access_point_id=%s",
                request_id,
                person.person_id,
                request_collection,
                len(access_point_ids),
                type(err).__name__,
                err.stage.value if isinstance(err, AccessUpdateError) else None,
                err.access_point_id if isinstance(err, AccessUpdateError) else None,
            )
            try:
                persisted_statuses = (
                    await self._access_management_service.current_access_point_statuses(
                        person.person_id
                    )
                )
            except Exception:  # noqa: BLE001 - failed inspection cannot claim access exists
                persisted_statuses = {}
            assignments = self._failed_assignment_results(
                access_point_ids,
                names,
                current_ids,
                persisted_statuses,
            )
            attention = any(item.status == "needs_attention" for item in assignments)
            status = "needs_attention" if attention else "failed"
            safe_result = UserSetupResult(person, assignments, status, attention, repeated)
            await self._save_request_result(request_collection, request_id, safe_result)
            return safe_result
        finally:
            plaintext = None
        safe_result = UserSetupResult(
            person,
            self._assignment_results(access_point_ids, names, access_result, current_ids),
            access_result.status,
            access_result.status != "completed",
            repeated,
        )
        await self._save_request_result(request_collection, request_id, safe_result)
        return safe_result

    async def _request_record(self, collection: str, request_id: UUID) -> dict[str, object] | None:
        snapshot = await self._storage.async_load()
        requests = snapshot["data"]["settings"].get(collection, {})
        if not isinstance(requests, dict):
            raise ValueError("User setup state is invalid")
        record = requests.get(str(request_id))
        if record is None:
            return None
        if not isinstance(record, dict):
            raise ValueError("User setup state is invalid")
        return cast(dict[str, object], record)

    async def _person_from_request(self, request: dict[str, object]) -> Person:
        person_id = request.get("person_id")
        if not isinstance(person_id, str):
            raise ValueError("User setup state is invalid")
        snapshot = await self._storage.async_load()
        person_record = snapshot["data"]["people"].get(person_id)
        if person_record is None:
            raise ValueError("User setup state is invalid")
        return Person.from_dict(person_record)

    async def _validate_setup_replay(
        self,
        request: dict[str, object],
        context: dict[str, object],
        pin: str | None,
    ) -> Person:
        if request.get("context") != context:
            raise ValueError("This request was already used for different User details")
        person = await self._person_from_request(request)
        credential = CredentialMetadataRepository._resolve_for_provisioning(
            await self._storage.async_load(), person.person_id
        )
        if pin is None:
            if credential is not None:
                raise ValueError("This request was already used with a PIN")
            return person
        if credential is None:
            raise ValueError("This User's PIN is unavailable")
        persisted_pin = await self._credential_vault.retrieve(credential.credential_id)
        try:
            if not secrets.compare_digest(pin, persisted_pin):
                raise ValueError("This request was already used with a different PIN")
        finally:
            persisted_pin = ""
        return person

    async def _validate_access_replay(self, person: Person, pin: str) -> None:
        """Require a repeated PIN-bearing request to match persisted authority."""
        credential = await self._credential_metadata_repository.resolve_for_provisioning(
            person.person_id
        )
        if credential is None:
            raise ValueError("This User's PIN is unavailable")
        persisted_pin = await self._credential_vault.retrieve(credential.credential_id)
        try:
            if not secrets.compare_digest(pin, persisted_pin):
                raise ValueError("This request was already used with a different PIN")
        finally:
            persisted_pin = ""

    @staticmethod
    def _create_core(
        storage: HomePassStorageData,
        *,
        request_id: UUID,
        person: Person,
        credential: CredentialMetadata | None,
        new_schedule: Schedule | None,
        access_point_ids: tuple[UUID, ...],
        context: dict[str, object],
    ) -> None:
        people = {
            identifier: Person.from_dict(record)
            for identifier, record in storage["data"]["people"].items()
        }
        if str(person.person_id) in people or any(
            existing.display_name.casefold() == person.display_name.casefold()
            for existing in people.values()
        ):
            raise DuplicatePersonError(person.display_name)
        if new_schedule is not None:
            UserSetupService._store_new_schedule(storage, new_schedule)
        else:
            selected_record = storage["data"]["schedules"].get(str(person.schedule_id))
            if selected_record is None:
                raise ValueError("Selected Schedule is unavailable")
            if not Schedule.from_dict(selected_record).enabled:
                raise ValueError("Selected Schedule must be enabled")
        UserSetupService._validate_access_point_selections(
            storage,
            access_point_ids,
            existing_access_point_ids=set(),
        )
        storage["data"]["people"][str(person.person_id)] = cast(StorageRecord, person.to_dict())
        if credential is not None:
            storage["data"]["credential_metadata"][str(person.person_id)] = cast(
                StorageRecord, credential.to_dict()
            )
        settings = storage["data"]["settings"]
        raw_requests = settings.setdefault(_SETUP_REQUESTS_SETTING, {})
        if not isinstance(raw_requests, dict):
            raise ValueError("User setup state is invalid")
        raw_requests[str(request_id)] = {
            "person_id": str(person.person_id),
            "context": cast(JsonValue, context),
            "state": "core_created",
            "assignments": [],
        }

    async def _prepare_access_request(
        self,
        request_id: UUID,
        person_id: UUID,
        schedule_id: UUID,
        access_point_ids: tuple[UUID, ...],
        context: dict[str, object],
        *,
        credential: CredentialMetadata | None,
        expected_credential_id: VaultCredentialId | None,
        new_schedule: Schedule | None,
    ) -> Person:
        """Select policy and journal the operation in one transaction."""
        now = datetime.now(UTC)

        def mutate(storage: HomePassStorageData) -> Person:
            record = storage["data"]["people"].get(str(person_id))
            if record is None:
                raise PersonNotFoundError(str(person_id))
            person = Person.from_dict(record)
            selected_schedule_id = (
                new_schedule.schedule_id if new_schedule is not None else schedule_id
            )
            if new_schedule is not None:
                if existing_grants := tuple(
                    AccessGrant.from_dict(grant)
                    for grant in storage["data"]["access_grants"].values()
                    if grant.get("person_id") == str(person_id)
                ):
                    raise ValueError(
                        "Edit this User's Schedule separately before assigning more doors"
                    )
                self._store_new_schedule(storage, new_schedule)
            else:
                existing_grants = tuple(
                    AccessGrant.from_dict(grant)
                    for grant in storage["data"]["access_grants"].values()
                    if grant.get("person_id") == str(person_id)
                )
            schedule_record = storage["data"]["schedules"].get(str(selected_schedule_id))
            if schedule_record is None:
                raise ValueError("Selected Schedule is unavailable")
            if not existing_grants and not Schedule.from_dict(schedule_record).enabled:
                raise ValueError("Selected Schedule must be enabled")
            if existing_grants and selected_schedule_id != person.schedule_id:
                raise ValueError("Edit this User's Schedule separately before assigning more doors")
            if not access_point_ids and selected_schedule_id != person.schedule_id:
                raise ValueError("Choose a door before changing a Schedule")
            UserSetupService._validate_access_point_selections(
                storage,
                access_point_ids,
                existing_access_point_ids={grant.access_point_id for grant in existing_grants},
            )
            if selected_schedule_id != person.schedule_id:
                person = replace(
                    person,
                    schedule_id=selected_schedule_id,
                    updated_at=max(now, person.updated_at + timedelta(microseconds=1)),
                )
                storage["data"]["people"][str(person_id)] = cast(StorageRecord, person.to_dict())
            current_authority = CredentialMetadataRepository._resolve_for_provisioning(
                storage, person_id
            )
            if credential is not None:
                if current_authority is not None:
                    raise CredentialAuthorityConflictError()
                storage["data"]["credential_metadata"][str(person_id)] = cast(
                    StorageRecord, credential.to_dict()
                )
                CredentialMetadataRepository._validate_authority_claim(storage, credential)
            elif (
                current_authority is None
                or expected_credential_id is None
                or current_authority.credential_id != expected_credential_id
            ):
                raise CredentialAuthorityConflictError()
            settings = storage["data"]["settings"]
            requests = settings.setdefault(_ACCESS_REQUESTS_SETTING, {})
            if not isinstance(requests, dict):
                raise ValueError("User access request state is invalid")
            requests[str(request_id)] = {
                "person_id": str(person.person_id),
                "context": cast(JsonValue, context),
                "state": "core_created",
                "assignments": [],
            }
            return person

        return await self._storage.async_transaction(mutate)

    @staticmethod
    def _validate_access_point_selections(
        storage: HomePassStorageData,
        access_point_ids: tuple[UUID, ...],
        *,
        existing_access_point_ids: set[UUID],
    ) -> None:
        """Require every new assignment to target an eligible durable policy door."""
        managed = storage["data"]["settings"].get("managed_access_points")
        if not isinstance(managed, dict):
            raise ValueError("Door enrollment state is unavailable")
        for access_point_id in access_point_ids:
            if access_point_id in existing_access_point_ids:
                continue
            identifier = str(access_point_id)
            record = storage["data"]["access_points"].get(identifier)
            enrollment = managed.get(identifier)
            if (
                record is None
                or not isinstance(enrollment, dict)
                or enrollment.get("managed") is not True
                or not AccessPoint.from_dict(record).enabled
            ):
                raise ValueError("One or more selected doors are unavailable")

    async def _mark_request_provisioning(self, collection: str, request_id: UUID) -> None:
        def mutate(storage: HomePassStorageData) -> None:
            requests = storage["data"]["settings"].get(collection)
            if not isinstance(requests, dict):
                raise ValueError("User workflow state is invalid")
            record = requests.get(str(request_id))
            if not isinstance(record, dict) or record.get("state") != "core_created":
                raise ValueError("User workflow state changed")
            record["state"] = "provisioning"

        await self._storage.async_transaction(mutate)

    async def _save_request_result(
        self,
        collection: str,
        request_id: UUID,
        result: UserSetupResult,
    ) -> None:
        def mutate(storage: HomePassStorageData) -> None:
            requests = storage["data"]["settings"].get(collection)
            if not isinstance(requests, dict):
                raise ValueError("User workflow state is invalid")
            record = requests.get(str(request_id))
            if not isinstance(record, dict):
                raise ValueError("User workflow state is invalid")
            record["state"] = (
                "needs_attention"
                if result.attention
                else "failed"
                if result.status == "failed"
                else "completed"
            )
            record["assignments"] = [
                {
                    "access_point_id": str(item.access_point_id),
                    "display_name": item.display_name,
                    "status": item.status,
                    "message": item.message,
                }
                for item in result.assignments
            ]

        await self._storage.async_transaction(mutate)

    @staticmethod
    def _saved_result(
        person: Person,
        record: dict[str, object],
        *,
        repeated: bool,
    ) -> UserSetupResult:
        raw_assignments = record.get("assignments")
        if not isinstance(raw_assignments, list):
            raise ValueError("User workflow result is invalid")
        assignments: list[UserAssignmentResult] = []
        for item in raw_assignments:
            if not isinstance(item, dict):
                raise ValueError("User workflow result is invalid")
            identifier = item.get("access_point_id")
            display_name = item.get("display_name")
            status = item.get("status")
            message = item.get("message")
            if (
                not isinstance(identifier, str)
                or not isinstance(display_name, str)
                or not isinstance(status, str)
                or (message is not None and not isinstance(message, str))
            ):
                raise ValueError("User workflow result is invalid")
            assignments.append(
                UserAssignmentResult(UUID(identifier), display_name, status, message)
            )
        state = record.get("state")
        attention = state == "needs_attention"
        return UserSetupResult(
            person,
            tuple(assignments),
            "needs_attention" if attention else "failed" if state == "failed" else "completed",
            attention,
            repeated,
        )

    @staticmethod
    def _setup_context(
        person: Person,
        access_point_ids: tuple[UUID, ...],
        new_schedule: Schedule | None,
        *,
        pin: str | None,
    ) -> dict[str, object]:
        return {
            "display_name": person.display_name,
            "description": person.description,
            "notes": person.notes,
            "enabled": person.enabled,
            "access_point_ids": sorted(str(value) for value in access_point_ids),
            "schedule_id": str(person.schedule_id),
            "schedule_definition": UserSetupService._schedule_definition(new_schedule),
            "pin_intent": "provided" if pin is not None else "omitted",
        }

    @staticmethod
    def _schedule_definition(schedule: Schedule | None) -> dict[str, object] | None:
        """Return stable PIN-safe Schedule identity for idempotency checks."""
        if schedule is None:
            return None
        return {
            "name": schedule.name,
            "enabled": schedule.enabled,
            "time_zone": schedule.time_zone,
            "valid_from": None if schedule.valid_from is None else schedule.valid_from.isoformat(),
            "valid_until": (
                None if schedule.valid_until is None else schedule.valid_until.isoformat()
            ),
            "weekly_rules": [rule.to_dict() for rule in schedule.weekly_rules],
        }

    @staticmethod
    def _store_new_schedule(storage: HomePassStorageData, schedule: Schedule) -> Schedule:
        """Persist one deterministic new Schedule, resolving only a name collision."""
        existing_schedules = {
            Schedule.from_dict(record).name.casefold()
            for record in storage["data"]["schedules"].values()
        }
        stored = schedule
        if stored.name.casefold() in existing_schedules:
            base = stored.name
            identifier = str(stored.schedule_id)
            for length in range(8, len(identifier) + 1):
                candidate = f"{base} {identifier[:length]}"
                if candidate.casefold() not in existing_schedules:
                    stored = replace(stored, name=candidate)
                    break
            else:
                raise ValueError("Unable to generate a unique User Schedule name")
        if str(stored.schedule_id) in storage["data"]["schedules"]:
            raise ValueError("Schedule already exists")
        storage["data"]["schedules"][str(stored.schedule_id)] = cast(
            StorageRecord, stored.to_dict()
        )
        return stored

    @staticmethod
    def _assignment_results(
        requested: tuple[UUID, ...],
        names: dict[UUID, str],
        result: AccessUpdateResult,
        current_ids: set[UUID],
    ) -> tuple[UserAssignmentResult, ...]:
        statuses = {item.access_point_id: item.status for item in result.access_points}
        return tuple(
            UserAssignmentResult(
                identifier,
                names.get(identifier, "Door"),
                (
                    "already_assigned"
                    if identifier in current_ids
                    else "added"
                    if identifier in result.added
                    and statuses.get(identifier, "completed") == "completed"
                    else statuses.get(identifier, "completed")
                ),
            )
            for identifier in requested
        )

    @staticmethod
    def _failed_assignment_results(
        requested: tuple[UUID, ...],
        names: dict[UUID, str],
        previously_assigned: set[UUID],
        persisted_statuses: Mapping[UUID, str],
    ) -> tuple[UserAssignmentResult, ...]:
        """Describe a failed orchestration from durable relationship truth only."""
        results: list[UserAssignmentResult] = []
        for identifier in requested:
            if identifier in previously_assigned:
                results.append(
                    UserAssignmentResult(
                        identifier,
                        names.get(identifier, "Door"),
                        "already_assigned",
                    )
                )
                continue
            persisted_status = persisted_statuses.get(identifier)
            if persisted_status == "completed":
                results.append(
                    UserAssignmentResult(identifier, names.get(identifier, "Door"), "added")
                )
            elif persisted_status is not None:
                results.append(
                    UserAssignmentResult(
                        identifier,
                        names.get(identifier, "Door"),
                        "needs_attention",
                        "Synchronization needs attention.",
                    )
                )
            else:
                results.append(
                    UserAssignmentResult(
                        identifier,
                        names.get(identifier, "Door"),
                        "failed",
                        "Access was not added.",
                    )
                )
        return tuple(results)

    @staticmethod
    def _access_point_from_record(record: Mapping[str, object]) -> AccessPoint:
        return AccessPoint.from_dict(record)

    @staticmethod
    def _validate_pin(pin: str) -> None:
        if (
            not isinstance(pin, str)
            or not 4 <= len(pin) <= 10
            or not pin.isascii()
            or not pin.isdigit()
        ):
            raise ValueError("PIN must contain 4 to 10 ASCII digits")


__all__ = [
    "UserAssignmentResult",
    "UserSetupOptions",
    "UserSetupResult",
    "UserSetupService",
]
