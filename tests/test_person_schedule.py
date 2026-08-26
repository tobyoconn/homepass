"""Person Schedule behavior before Door access is assigned."""

from datetime import time
from pathlib import Path
from uuid import uuid4

from homeassistant.core import HomeAssistant

from custom_components.homepass.models import (
    AccessGrant,
    AccessPoint,
    DayOfWeek,
    Person,
    WeeklyRule,
)
from custom_components.homepass.repositories import (
    AccessGrantRepository,
    AccessPointEnrollmentRepository,
)
from custom_components.homepass.repositories.person import PersonRepository
from custom_components.homepass.services import AccessPointEnrollment, PersonScheduleService
from custom_components.homepass.storage import HomePassStorageManager

_FRONTEND_SOURCE = (
    Path(__file__).parents[1] / "custom_components" / "homepass" / "frontend" / "homepass-panel.js"
).read_text(encoding="utf-8")


def test_frontend_opens_user_schedule_before_door_access() -> None:
    """The Schedule editor is useful before a Door relationship exists."""
    assert "this._scheduleGroupEditorOpen = Boolean(activeGroup) || !hasAssignedDoors" in (
        _FRONTEND_SOURCE
    )
    assert "this._scheduleBeforeDoorAccessSection()" in _FRONTEND_SOURCE
    assert "Set the schedule now and HomePASS will apply it when door access is added later." in (
        _FRONTEND_SOURCE
    )
    assert "...(hasAssignedDoors ? [this._scheduleDoorsSection()] : [])" in _FRONTEND_SOURCE
    assert "add.disabled = this._scheduleSaving;" in _FRONTEND_SOURCE


async def test_saved_user_schedule_is_inherited_by_first_door_access(
    hass: HomeAssistant,
) -> None:
    """A no-Door user policy becomes the default for a later grant."""
    storage = HomePassStorageManager(hass)
    people = PersonRepository(storage)
    person = Person("Future Guest")
    await people.add(person)
    service = PersonScheduleService(storage)
    state = await service.get_schedule_state(person.person_id)
    rule = WeeklyRule(DayOfWeek.MONDAY, time(9), time(17))

    schedule = await service.save_person_schedule(
        person.person_id,
        time_zone="Asia/Dubai",
        valid_from=None,
        valid_until=None,
        weekly_rules=(rule,),
        expected_person_updated_at=state.person.updated_at,
        expected_schedule_id=state.schedule.schedule_id,
        expected_schedule_revision=state.schedule.revision,
    )

    updated_person = await people.get(person.person_id)
    access_point = AccessPoint("Future Door")
    await AccessPointEnrollmentRepository(storage).upsert(
        AccessPointEnrollment(
            access_point_id=access_point.id,
            discovery_key="manual:lock.future_door",
            control_entity_id="lock.future_door",
        ),
        access_point,
    )
    grant = await AccessGrantRepository(storage).upsert_inheriting_person_schedule(
        AccessGrant(
            person_id=person.person_id,
            credential_id=uuid4(),
            access_point_id=access_point.id,
        )
    )

    assert updated_person.schedule_id == schedule.schedule_id
    assert grant.schedule_id == schedule.schedule_id
