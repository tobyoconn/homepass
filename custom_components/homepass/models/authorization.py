"""Pure domain authorization for one Person and Access Point relationship."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from ..exceptions import AuthorizationInvariantError
from .access_grant import AccessGrant
from .access_point import AccessPoint
from .person import Person
from .schedule import Schedule
from .schedule_evaluation import ScheduleEvaluation, evaluate_schedule


class AuthorizationDecision(StrEnum):
    """Stable policy result for one access authorization evaluation."""

    ALLOWED = "allowed"
    PERSON_DISABLED = "person_disabled"
    NO_GRANT = "no_grant"
    GRANT_DISABLED = "grant_disabled"
    ACCESS_POINT_UNMANAGED = "access_point_unmanaged"
    ACCESS_POINT_DISABLED = "access_point_disabled"
    POLICY_CONFLICT = "policy_conflict"
    SCHEDULE_DISABLED = "schedule_disabled"
    SCHEDULE_NOT_YET_VALID = "schedule_not_yet_valid"
    SCHEDULE_EXPIRED = "schedule_expired"
    OUTSIDE_WEEKLY_RULE = "outside_weekly_rule"

    @property
    def allowed(self) -> bool:
        """Return whether policy authorizes access."""
        return self is AuthorizationDecision.ALLOWED


_SCHEDULE_DECISIONS = {
    ScheduleEvaluation.ACTIVE: AuthorizationDecision.ALLOWED,
    ScheduleEvaluation.DISABLED: AuthorizationDecision.SCHEDULE_DISABLED,
    ScheduleEvaluation.NOT_YET_VALID: AuthorizationDecision.SCHEDULE_NOT_YET_VALID,
    ScheduleEvaluation.EXPIRED: AuthorizationDecision.SCHEDULE_EXPIRED,
    ScheduleEvaluation.OUTSIDE_WEEKLY_RULE: AuthorizationDecision.OUTSIDE_WEEKLY_RULE,
}


def authorize_access(
    *,
    person: Person,
    access_grant: AccessGrant | None,
    access_point: AccessPoint,
    access_point_managed: bool,
    schedule: Schedule,
    instant_utc: datetime,
) -> AuthorizationDecision:
    """Evaluate pure access policy over one consistent set of domain snapshots."""
    _validate_invariants(
        person=person,
        access_grant=access_grant,
        access_point=access_point,
        access_point_managed=access_point_managed,
        schedule=schedule,
    )

    if not person.enabled:
        return AuthorizationDecision.PERSON_DISABLED
    if access_grant is None:
        return AuthorizationDecision.NO_GRANT
    if not access_grant.enabled:
        return AuthorizationDecision.GRANT_DISABLED
    if not access_point_managed:
        return AuthorizationDecision.ACCESS_POINT_UNMANAGED
    if not access_point.enabled:
        return AuthorizationDecision.ACCESS_POINT_DISABLED
    if access_grant.schedule_id != schedule.schedule_id:
        return AuthorizationDecision.POLICY_CONFLICT
    return _SCHEDULE_DECISIONS[evaluate_schedule(schedule, instant_utc)]


def _validate_invariants(
    *,
    person: Person,
    access_grant: AccessGrant | None,
    access_point: AccessPoint,
    access_point_managed: bool,
    schedule: Schedule,
) -> None:
    """Reject inputs that do not describe one internally consistent relationship."""
    if access_grant is not None and access_grant.person_id != person.person_id:
        raise AuthorizationInvariantError("Access Grant does not belong to the supplied Person")
    if access_grant is not None and access_grant.access_point_id != access_point.id:
        raise AuthorizationInvariantError("Access Grant does not target the supplied Access Point")
    expected_schedule_ids = {person.schedule_id}
    if access_grant is not None:
        expected_schedule_ids.add(access_grant.schedule_id)
    if schedule.schedule_id not in expected_schedule_ids:
        raise AuthorizationInvariantError(
            "Schedule does not match the supplied access relationship"
        )
    if not isinstance(access_point_managed, bool):
        raise AuthorizationInvariantError("Access Point managed state must be a boolean")
