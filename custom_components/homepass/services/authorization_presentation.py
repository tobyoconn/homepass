"""Shared homeowner-facing presentation for authorization decisions."""

from __future__ import annotations

from typing import Literal

from ..models import AuthorizationDecision

type AuthorizationPolicySeverity = Literal["warning", "error"]

_DENIAL_EXPLANATIONS = {
    AuthorizationDecision.PERSON_DISABLED: "User disabled",
    AuthorizationDecision.NO_GRANT: "No access assigned",
    AuthorizationDecision.GRANT_DISABLED: "Access disabled",
    AuthorizationDecision.ACCESS_POINT_UNMANAGED: "Door not managed",
    AuthorizationDecision.ACCESS_POINT_DISABLED: "Door disabled",
    AuthorizationDecision.POLICY_CONFLICT: "Configuration needs attention",
    AuthorizationDecision.SCHEDULE_DISABLED: "Schedule disabled",
    AuthorizationDecision.SCHEDULE_NOT_YET_VALID: "Schedule has not started",
    AuthorizationDecision.SCHEDULE_EXPIRED: "Schedule has expired",
    AuthorizationDecision.OUTSIDE_WEEKLY_RULE: "Outside scheduled hours",
}

_ADMINISTRATIVE_DENIALS = {
    AuthorizationDecision.ACCESS_POINT_UNMANAGED,
    AuthorizationDecision.ACCESS_POINT_DISABLED,
    AuthorizationDecision.POLICY_CONFLICT,
}


def authorization_explanation(decision: AuthorizationDecision) -> str:
    """Return the established homeowner-facing explanation for a denial."""
    try:
        return _DENIAL_EXPLANATIONS[decision]
    except KeyError as err:
        raise ValueError("Allowed authorization has no denial explanation") from err


def authorization_severity(decision: AuthorizationDecision) -> AuthorizationPolicySeverity:
    """Return the established warning/error presentation severity for a denial."""
    return "error" if decision in _ADMINISTRATIVE_DENIALS else "warning"


__all__ = [
    "AuthorizationPolicySeverity",
    "authorization_explanation",
    "authorization_severity",
]
