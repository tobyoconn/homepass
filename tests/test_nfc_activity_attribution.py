"""NFC unlock attribution behavior."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from custom_components.homepass.models import (
    ActivityAccessMethod,
    ActivityActorType,
    ActivityCategory,
    ActivityEvent,
    ActivityEventType,
    ActivitySeverity,
    ActivitySource,
    LockEventOrigin,
)
from custom_components.homepass.services.activity_presentation import present_activity
from custom_components.homepass.services.lock_event_correlation import (
    LockCommandCorrelationService,
    LockStableState,
)


def test_nfc_identity_survives_physical_unlock_correlation() -> None:
    """The authenticated Person remains attached until the lock confirms."""
    now = datetime.now(UTC)
    access_point_id = uuid4()
    person_id = uuid4()
    command_id = uuid4()
    correlations = LockCommandCorrelationService(clock=lambda: now)

    correlations.register(
        access_point_id=access_point_id,
        requested_state=LockStableState.UNLOCKED,
        origin=LockEventOrigin.NFC_PASSKEY,
        command_id=command_id,
        person_id=person_id,
        person_name="Example Resident",
    )
    confirmed = correlations.consume(
        access_point_id=access_point_id,
        confirmed_state=LockStableState.UNLOCKED,
        confirmed_at=now,
    )

    assert confirmed is not None
    assert confirmed.person_id == person_id
    assert confirmed.person_name == "Example Resident"


def test_nfc_unlock_activity_names_user_and_method() -> None:
    """Recent Activity identifies both the HomePASS User and NFC method."""
    now = datetime.now(UTC)
    person_id = uuid4()
    event = ActivityEvent(
        event_id=uuid4(),
        occurred_at=now,
        recorded_at=now,
        event_type=ActivityEventType.DOOR_UNLOCKED,
        category=ActivityCategory.DOOR,
        severity=ActivitySeverity.INFO,
        source=ActivitySource.HOME_ASSISTANT,
        actor_type=ActivityActorType.PERSON,
        actor_id=person_id,
        actor_name="Example Resident",
        access_method=ActivityAccessMethod.REMOTE,
        door_id=uuid4(),
        door_name="Front Door Lock",
        person_id=person_id,
        person_name="Example Resident",
        attributes={"lock_origin": LockEventOrigin.NFC_PASSKEY.value},
    )

    presented = present_activity(event)

    assert presented.title == "Example Resident unlocked Front Door Lock by NFC."
    assert presented.actor == "Example Resident"
