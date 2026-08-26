"""Shared homeowner-facing synchronization status presentation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, TypedDict

from ..models import AccessPointSynchronization, SynchronizationStatus

type SynchronizationSeverity = Literal["success", "info", "warning", "error"]


class SynchronizationPresentationData(TypedDict):
    """Serialized presentation without internal synchronization identifiers."""

    title: str
    description: str
    severity: SynchronizationSeverity
    retry_allowed: bool
    last_evaluated_at: str


@dataclass(frozen=True, slots=True)
class SynchronizationPresentation:
    """Calm homeowner-facing synchronization explanation."""

    title: str
    description: str
    severity: SynchronizationSeverity
    retry_allowed: bool
    last_evaluated_at: datetime

    def to_dict(self) -> SynchronizationPresentationData:
        """Serialize presentation values without exposing enum names."""
        return {
            "title": self.title,
            "description": self.description,
            "severity": self.severity,
            "retry_allowed": self.retry_allowed,
            "last_evaluated_at": self.last_evaluated_at.isoformat(),
        }


_PRESENTATION: dict[
    SynchronizationStatus,
    tuple[str, str, SynchronizationSeverity, bool],
] = {
    SynchronizationStatus.SYNCHRONIZED: (
        "Synchronized",
        "HomePASS and this lock are synchronized.",
        "success",
        False,
    ),
    SynchronizationStatus.SYNCHRONIZING: (
        "Synchronizing",
        "HomePASS is updating this lock.",
        "info",
        False,
    ),
    SynchronizationStatus.PENDING: (
        "Synchronization pending",
        "HomePASS is waiting to confirm synchronization with this lock.",
        "info",
        False,
    ),
    SynchronizationStatus.RETRY_REQUIRED: (
        "Synchronization needs attention",
        "HomePASS could not confirm the latest change. You can try again.",
        "warning",
        True,
    ),
    SynchronizationStatus.MANUAL_ATTENTION_REQUIRED: (
        "Manual attention required",
        "HomePASS could not complete synchronization. Review this lock before continuing.",
        "error",
        False,
    ),
    SynchronizationStatus.UNKNOWN: (
        "Synchronization status unavailable",
        "HomePASS cannot currently determine synchronization status.",
        "warning",
        False,
    ),
}


def synchronization_presentation(
    record: AccessPointSynchronization,
) -> SynchronizationPresentation:
    """Present one canonical status without reflecting its internal value."""
    title, description, severity, retry_allowed = _PRESENTATION[record.status]
    return SynchronizationPresentation(
        title,
        description,
        severity,
        retry_allowed,
        record.last_evaluated_at,
    )


__all__ = [
    "SynchronizationPresentation",
    "SynchronizationPresentationData",
    "SynchronizationSeverity",
    "synchronization_presentation",
]
