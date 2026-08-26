"""Application service for consistent access-authorization snapshots."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from typing import Protocol
from uuid import UUID

from ..exceptions import (
    AccessPointNotFoundError,
    AuthorizationContextError,
    AuthorizationInvariantError,
    HomePASSError,
    InvalidPersonScheduleReferenceError,
    PersonNotFoundError,
)
from ..models import (
    AccessGrant,
    AccessPoint,
    AuthorizationDecision,
    Person,
    Schedule,
    SynchronizationStatus,
    authorize_access,
)
from ..storage import HomePassStorageData, HomePassStorageManager, StorageRecord

_MANAGED_ACCESS_POINTS_SETTING = "managed_access_points"


class AuthorizationAccessPointLookup(Protocol):
    """Load a stable policy-domain Access Point without operational state."""

    async def get_access_point(
        self,
        snapshot: HomePassStorageData,
        access_point_id: UUID,
    ) -> AccessPoint:
        """Decode the stable Access Point from the request's policy snapshot."""

    async def list_access_points(
        self,
        snapshot: HomePassStorageData,
    ) -> tuple[AccessPoint, ...]:
        """Decode all stable Access Points from the request's policy snapshot."""


@dataclass(frozen=True, slots=True)
class _PersistedAuthorizationContext:
    """Authorization inputs decoded from one persisted snapshot."""

    person: Person
    access_grant: AccessGrant | None
    schedule: Schedule
    access_point_managed: bool


@dataclass(frozen=True, slots=True)
class PersonAuthorizationResult:
    """Authorization decision paired with its Person from one snapshot."""

    person: Person
    decision: AuthorizationDecision


@dataclass(frozen=True, slots=True)
class AccessPointAuthorizationResult:
    """Authorization decision paired with its Access Point from one snapshot."""

    access_point: AccessPoint
    decision: AuthorizationDecision


@dataclass(frozen=True, slots=True)
class AuthorizationRelationshipResult:
    """Complete safe policy context and decision from one persisted snapshot."""

    person: Person
    access_point: AccessPoint
    schedule: Schedule
    decision: AuthorizationDecision


@dataclass(frozen=True, slots=True)
class AuthorizationMatrixCell:
    """One relationship result, or a fail-closed unavailable context."""

    access_point: AccessPoint
    person: Person | None
    decision: AuthorizationDecision | None


@dataclass(frozen=True, slots=True)
class AuthorizationPolicyMatrix:
    """All durable policy relationships evaluated from one snapshot."""

    access_points: tuple[AccessPoint, ...]
    cells: tuple[AuthorizationMatrixCell, ...]


class AuthorizationService:
    """Load one policy snapshot and delegate its decision to the pure engine."""

    def __init__(
        self,
        storage_manager: HomePassStorageManager,
        access_point_lookup: AuthorizationAccessPointLookup | None = None,
    ) -> None:
        """Initialize persistence and the optional single-Person lookup boundary."""
        self._storage_manager = storage_manager
        self._access_point_lookup = access_point_lookup

    async def authorize_person_for_access_point(
        self,
        *,
        person_id: UUID,
        access_point_id: UUID,
        instant_utc: datetime,
    ) -> AuthorizationDecision:
        """Authorize one Person and Access Point using one persisted snapshot."""
        result = await self.resolve_person_for_access_point(
            person_id=person_id,
            access_point_id=access_point_id,
            instant_utc=instant_utc,
        )
        return result.decision

    async def resolve_person_for_access_point(
        self,
        *,
        person_id: UUID,
        access_point_id: UUID,
        instant_utc: datetime,
    ) -> AuthorizationRelationshipResult:
        """Resolve one relationship and decision from one persisted snapshot."""
        return await self._resolve_person_for_access_point(
            person_id=person_id,
            access_point_id=access_point_id,
            instant_utc=instant_utc,
            supplemental_grant=False,
        )

    async def resolve_person_for_access_point_with_nfc_grant(
        self,
        *,
        person_id: UUID,
        access_point_id: UUID,
        instant_utc: datetime,
    ) -> AuthorizationRelationshipResult:
        """Evaluate an explicit NFC grant without persisting fake PIN metadata."""
        return await self._resolve_person_for_access_point(
            person_id=person_id,
            access_point_id=access_point_id,
            instant_utc=instant_utc,
            supplemental_grant=True,
        )

    async def _resolve_person_for_access_point(
        self,
        *,
        person_id: UUID,
        access_point_id: UUID,
        instant_utc: datetime,
        supplemental_grant: bool,
    ) -> AuthorizationRelationshipResult:
        """Resolve one relationship, optionally supplying an in-memory NFC grant."""
        snapshot = await self._load_snapshot()
        context = _decode_snapshot(snapshot, person_id, access_point_id)
        if supplemental_grant and context.access_grant is None:
            context = replace(
                context,
                access_grant=AccessGrant(
                    person_id=person_id,
                    credential_id=UUID(int=0),
                    access_point_id=access_point_id,
                    schedule_id=context.person.schedule_id,
                    synchronization_status=SynchronizationStatus.SYNCHRONIZED,
                ),
            )
        access_point = await self._load_access_point(
            snapshot,
            access_point_id,
            any_managed=context.access_point_managed,
        )
        return AuthorizationRelationshipResult(
            person=context.person,
            access_point=access_point,
            schedule=context.schedule,
            decision=_authorize_context(context, access_point, instant_utc),
        )

    async def authorize_people_for_access_point(
        self,
        *,
        access_point: AccessPoint,
        instant_utc: datetime,
    ) -> tuple[PersonAuthorizationResult, ...]:
        """Authorize every persisted Person from one isolated policy snapshot."""
        if not isinstance(access_point, AccessPoint):
            raise AuthorizationContextError
        snapshot = await self._load_snapshot()
        contexts = tuple(
            _decode_snapshot(snapshot, person_id, access_point.id)
            for person_id in _decode_person_ids(snapshot)
        )
        return tuple(
            PersonAuthorizationResult(
                context.person,
                _authorize_context(context, access_point, instant_utc),
            )
            for context in contexts
        )

    async def authorize_person_for_access_points(
        self,
        *,
        person_id: UUID,
        instant_utc: datetime,
    ) -> tuple[AccessPointAuthorizationResult, ...]:
        """Authorize one Person for every durable Access Point in one snapshot."""
        snapshot = await self._load_snapshot()
        _decode_person(snapshot, person_id)
        access_points = await self._list_access_points(snapshot)
        return tuple(
            AccessPointAuthorizationResult(
                access_point,
                _authorize_context(
                    _decode_snapshot(snapshot, person_id, access_point.id),
                    access_point,
                    instant_utc,
                ),
            )
            for access_point in access_points
        )

    async def evaluate_policy_matrix(
        self,
        *,
        instant_utc: datetime,
    ) -> AuthorizationPolicyMatrix:
        """Evaluate every durable Person-to-Access-Point relationship once."""
        snapshot = await self._load_snapshot()
        access_points = await self._list_access_points(snapshot)
        person_keys = _decode_person_keys(snapshot)
        cells: list[AuthorizationMatrixCell] = []
        for access_point in access_points:
            for person_key in person_keys:
                try:
                    person_id = UUID(person_key)
                    context = _decode_snapshot(snapshot, person_id, access_point.id)
                    decision = _authorize_context(context, access_point, instant_utc)
                except (HomePASSError, TypeError, ValueError):
                    person = _try_decode_person(snapshot, person_key)
                    cells.append(AuthorizationMatrixCell(access_point, person, None))
                    continue
                cells.append(AuthorizationMatrixCell(access_point, context.person, decision))
        return AuthorizationPolicyMatrix(access_points, tuple(cells))

    async def _load_snapshot(self) -> HomePassStorageData:
        """Load one isolated persistence snapshot with sanitized failures."""
        try:
            return await self._storage_manager.async_load()
        except AuthorizationInvariantError:
            raise
        except Exception as err:
            raise AuthorizationContextError from err

    async def _load_access_point(
        self,
        snapshot: HomePassStorageData,
        access_point_id: UUID,
        *,
        any_managed: bool,
    ) -> AccessPoint:
        """Load the stable Access Point policy object with sanitized failures."""
        if self._access_point_lookup is None:
            raise AuthorizationContextError
        try:
            access_point = await self._access_point_lookup.get_access_point(
                snapshot,
                access_point_id,
            )
        except AuthorizationInvariantError:
            raise
        except AccessPointNotFoundError as err:
            if any_managed:
                raise AuthorizationContextError from err
            raise
        except Exception as err:
            raise AuthorizationContextError from err

        if not isinstance(access_point, AccessPoint) or access_point.id != access_point_id:
            raise AuthorizationContextError
        return access_point

    async def _list_access_points(
        self,
        snapshot: HomePassStorageData,
    ) -> tuple[AccessPoint, ...]:
        """Load every durable Access Point from the same isolated snapshot."""
        if self._access_point_lookup is None:
            raise AuthorizationContextError
        try:
            access_points = await self._access_point_lookup.list_access_points(snapshot)
        except AuthorizationInvariantError:
            raise
        except Exception as err:
            raise AuthorizationContextError from err
        if not isinstance(access_points, tuple) or any(
            not isinstance(access_point, AccessPoint) for access_point in access_points
        ):
            raise AuthorizationContextError
        return access_points


def _authorize_context(
    context: _PersistedAuthorizationContext,
    access_point: AccessPoint,
    instant_utc: datetime,
) -> AuthorizationDecision:
    """Delegate one decoded context to the pure authorization engine."""
    return authorize_access(
        person=context.person,
        access_grant=context.access_grant,
        access_point=access_point,
        access_point_managed=context.access_point_managed,
        schedule=context.schedule,
        instant_utc=instant_utc,
    )


def _decode_person_ids(snapshot: HomePassStorageData) -> tuple[UUID, ...]:
    """Decode every Person key selected from one isolated snapshot."""
    try:
        people = snapshot["data"]["people"]
    except (KeyError, TypeError) as err:
        raise AuthorizationContextError from err
    if not isinstance(people, dict):
        raise AuthorizationContextError
    try:
        return tuple(UUID(person_id) for person_id in people)
    except (TypeError, ValueError) as err:
        raise AuthorizationContextError from err


def _decode_person_keys(snapshot: HomePassStorageData) -> tuple[str, ...]:
    """Return deterministic raw Person keys without trusting their records."""
    try:
        people = snapshot["data"]["people"]
    except (KeyError, TypeError) as err:
        raise AuthorizationContextError from err
    if not isinstance(people, dict) or any(not isinstance(key, str) for key in people):
        raise AuthorizationContextError
    return tuple(sorted(people))


def _try_decode_person(snapshot: HomePassStorageData, person_key: str) -> Person | None:
    """Best-effort Person identity for an unavailable matrix cell."""
    try:
        return _decode_person(snapshot, UUID(person_key))
    except (HomePASSError, TypeError, ValueError):
        return None


def _decode_snapshot(
    snapshot: HomePassStorageData,
    person_id: UUID,
    access_point_id: UUID,
) -> _PersistedAuthorizationContext:
    """Decode only the selected relationship from one isolated storage snapshot."""
    try:
        data = snapshot["data"]
        grants = data["access_grants"]
        schedules = data["schedules"]
        settings = data["settings"]
    except (KeyError, TypeError) as err:
        raise AuthorizationContextError from err

    person = _decode_person(snapshot, person_id)

    person_schedule_key = str(person.schedule_id)
    if person_schedule_key not in schedules:
        raise InvalidPersonScheduleReferenceError(person_id)
    schedule = _decode_schedule(schedules[person_schedule_key], person.schedule_id)

    grant_key = f"{person_id}:{access_point_id}"
    access_grant: AccessGrant | None = None
    if grant_key in grants:
        try:
            access_grant = AccessGrant.from_dict(grants[grant_key])
        except (KeyError, TypeError, ValueError) as err:
            raise AuthorizationContextError from err
        if access_grant.person_id != person_id or access_grant.access_point_id != access_point_id:
            raise AuthorizationContextError
        grant_schedule_key = str(access_grant.schedule_id)
        if grant_schedule_key not in schedules:
            raise AuthorizationContextError
        if access_grant.schedule_id != schedule.schedule_id:
            schedule = _decode_schedule(schedules[grant_schedule_key], access_grant.schedule_id)

    access_point_managed = _decode_managed_state(settings, access_point_id)
    return _PersistedAuthorizationContext(
        person=person,
        access_grant=access_grant,
        schedule=schedule,
        access_point_managed=access_point_managed,
    )


def _decode_person(snapshot: HomePassStorageData, person_id: UUID) -> Person:
    """Decode one selected Person while preserving the existing error contract."""
    try:
        people = snapshot["data"]["people"]
    except (KeyError, TypeError) as err:
        raise AuthorizationContextError from err
    if not isinstance(people, dict):
        raise AuthorizationContextError
    person_key = str(person_id)
    if person_key not in people:
        raise PersonNotFoundError("Person not found")
    try:
        person = Person.from_dict(people[person_key])
    except (KeyError, TypeError, ValueError) as err:
        raise AuthorizationContextError from err
    if person.person_id != person_id:
        raise AuthorizationContextError
    return person


def _decode_schedule(record: StorageRecord, expected_id: UUID) -> Schedule:
    """Decode a Schedule and verify its storage key identity."""
    try:
        schedule = Schedule.from_dict(record)
    except (KeyError, TypeError, ValueError) as err:
        raise AuthorizationContextError from err
    if schedule.schedule_id != expected_id:
        raise AuthorizationContextError
    return schedule


def _decode_managed_state(settings: object, access_point_id: UUID) -> bool:
    """Return explicit managed state without coercing malformed persisted values."""
    if not isinstance(settings, dict):
        raise AuthorizationContextError
    enrollments = settings.get(_MANAGED_ACCESS_POINTS_SETTING)
    if not isinstance(enrollments, dict):
        raise AuthorizationContextError
    enrollment = enrollments.get(str(access_point_id))
    if enrollment is None:
        return False
    if not isinstance(enrollment, dict) or not {
        "discovery_key", "managed"
    } <= set(enrollment):
        raise AuthorizationContextError
    discovery_key = enrollment["discovery_key"]
    managed = enrollment["managed"]
    if discovery_key is not None and not isinstance(discovery_key, str):
        raise AuthorizationContextError
    if not isinstance(managed, bool):
        raise AuthorizationContextError
    return managed


__all__ = [
    "AccessPointAuthorizationResult",
    "AuthorizationAccessPointLookup",
    "AuthorizationMatrixCell",
    "AuthorizationPolicyMatrix",
    "AuthorizationRelationshipResult",
    "AuthorizationService",
    "PersonAuthorizationResult",
]
