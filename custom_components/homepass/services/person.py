"""Person application service for HomePASS."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from ..exceptions import ValidationError
from ..models import ActivityEventType, LifecycleOperationStatus, Person
from ..models.schedule import PERMANENT_SCHEDULE_ID
from ..repositories.person import PersonRepository
from .activity_producer import ActivityProducer
from .person_deletion import PersonDeletionService


class PersonService:
    """Coordinate application operations for people."""

    def __init__(
        self,
        repository: PersonRepository,
        deletion_service: PersonDeletionService | None = None,
        activity_producer: ActivityProducer | None = None,
    ) -> None:
        """Initialize the service with its Person repository."""
        self._repository = repository
        self._deletion_service = deletion_service
        self._activity_producer = activity_producer

    async def create_person(
        self,
        display_name: str,
        notes: str | None = None,
        *,
        description: str | None = None,
        enabled: bool = True,
    ) -> Person:
        """Create and persist a person."""
        person = self._build_person(
            display_name=display_name,
            enabled=enabled,
            description=description,
            notes=notes,
        )
        await self._repository.add(person)
        if self._activity_producer is not None:
            await self._activity_producer.record(
                ActivityEventType.PERSON_ADDED,
                occurred_at=person.created_at,
                source_event_key=f"person:{person.person_id}:created",
                person=person,
            )
        return person

    async def update_person(
        self,
        person_id: UUID,
        *,
        display_name: str | None = None,
        enabled: bool | None = None,
        description: str | None = None,
        description_provided: bool = False,
        notes: str | None = None,
    ) -> Person:
        """Create and persist an updated immutable person snapshot."""
        current = await self._repository.get(person_id)
        next_display_name = current.display_name if display_name is None else display_name
        next_enabled = current.enabled if enabled is None else enabled
        next_description = current.description if not description_provided else description
        next_notes = current.notes if notes is None else notes
        details_changed = (
            next_display_name != current.display_name
            or next_description != current.description
            or next_notes != current.notes
        )
        enabled_changed = next_enabled != current.enabled
        updated = self._build_person(
            person_id=current.person_id,
            display_name=next_display_name,
            enabled=next_enabled,
            schedule_id=current.schedule_id,
            description=next_description,
            notes=next_notes,
            created_at=current.created_at,
            updated_at=max(
                datetime.now(UTC),
                current.updated_at + timedelta(microseconds=1),
            ),
        )
        await self._repository.update(updated)
        if self._activity_producer is not None:
            correlation_id = uuid4()
            if details_changed:
                await self._activity_producer.record(
                    ActivityEventType.PERSON_UPDATED,
                    occurred_at=updated.updated_at,
                    source_event_key=(
                        f"person:{person_id}:updated:{updated.updated_at.isoformat()}"
                    ),
                    person=updated,
                    correlation_id=correlation_id,
                )
            if enabled_changed:
                await self._activity_producer.record(
                    (
                        ActivityEventType.PERSON_ENABLED
                        if updated.enabled
                        else ActivityEventType.PERSON_DISABLED
                    ),
                    occurred_at=updated.updated_at,
                    source_event_key=(
                        f"person:{person_id}:enabled:{updated.updated_at.isoformat()}"
                    ),
                    person=updated,
                    correlation_id=correlation_id,
                )
        return updated

    async def delete_person(self, person_id: UUID) -> None:
        """Delete a person."""
        person = await self._repository.get(person_id)
        if self._deletion_service is not None:
            operation = await self._deletion_service.delete_person(person_id)
            if (
                operation.status is LifecycleOperationStatus.COMPLETED
                and self._activity_producer is not None
            ):
                await self._activity_producer.record(
                    ActivityEventType.PERSON_REMOVED,
                    occurred_at=operation.updated_at,
                    source_event_key=f"lifecycle:{operation.operation_id}:person-removed",
                    person=person,
                    correlation_id=operation.operation_id,
                )
            return
        await self._repository.remove(person_id)
        if self._activity_producer is not None:
            await self._activity_producer.record(
                ActivityEventType.PERSON_REMOVED,
                occurred_at=datetime.now(UTC),
                source_event_key=(
                    f"person:{person.person_id}:removed:{person.updated_at.isoformat()}"
                ),
                person=person,
            )

    async def get_person(self, person_id: UUID) -> Person:
        """Return a person."""
        return await self._repository.get(person_id)

    async def list_people(self) -> tuple[Person, ...]:
        """Return all people in repository order."""
        return await self._repository.list_all()

    @staticmethod
    def _build_person(
        *,
        display_name: str,
        person_id: UUID | None = None,
        enabled: bool = True,
        schedule_id: UUID = PERMANENT_SCHEDULE_ID,
        description: str | None = None,
        notes: str | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> Person:
        """Build a validated person and expose domain validation errors."""
        default_time = datetime.now(UTC)
        try:
            return Person(
                person_id=uuid4() if person_id is None else person_id,
                display_name=display_name,
                enabled=enabled,
                schedule_id=schedule_id,
                description=description,
                notes=notes,
                created_at=default_time if created_at is None else created_at,
                updated_at=default_time if updated_at is None else updated_at,
            )
        except (TypeError, ValueError) as err:
            raise ValidationError(str(err)) from err
