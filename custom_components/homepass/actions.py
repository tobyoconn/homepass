"""Home Assistant actions for HomePASS."""

from __future__ import annotations

from collections.abc import Awaitable
from datetime import UTC, datetime
from typing import cast
from uuid import UUID

import voluptuous as vol
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
    callback,
)
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv

from .const import (
    ATTR_DESCRIPTION,
    ATTR_DISPLAY_NAME,
    ATTR_ENABLED,
    ATTR_NOTES,
    ATTR_PERSON_ID,
    DOMAIN,
    SERVICE_CREATE_PERSON,
    SERVICE_DELETE_PERSON,
    SERVICE_GET_PERSON,
    SERVICE_GET_PERSON_POLICY_DETAILS,
    SERVICE_LIST_PEOPLE,
    SERVICE_UPDATE_PERSON,
)
from .exceptions import (
    DuplicatePersonError,
    HomePASSError,
    LifecycleOperationExecutionError,
    PersonNotFoundError,
    PersonScheduleConflictError,
    StorageError,
    ValidationError,
)
from .models import Person
from .models.person import MAX_PERSON_DESCRIPTION_LENGTH
from .services import (
    AccessMetadataService,
    AccessPointService,
    CredentialReplacementLifecycleService,
    PersonCardService,
    PersonPolicyDetailsService,
    PersonScheduleService,
    PersonService,
)

PERSON_ACTIONS = (
    SERVICE_CREATE_PERSON,
    SERVICE_UPDATE_PERSON,
    SERVICE_DELETE_PERSON,
    SERVICE_GET_PERSON,
    SERVICE_GET_PERSON_POLICY_DETAILS,
    SERVICE_LIST_PEOPLE,
)


def _display_name(value: object) -> str:
    """Validate and normalize a display name."""
    display_name = cv.string(value).strip()
    if not display_name:
        raise vol.Invalid("display_name must not be empty")
    return display_name


def _person_id(value: object) -> UUID:
    """Validate and convert a Person UUID."""
    try:
        return UUID(cv.string(value))
    except ValueError as err:
        raise vol.Invalid("person_id must be a valid UUID") from err


def _description(value: object) -> str | None:
    """Validate and normalize an optional informational description."""
    if value is None:
        return None
    description = cv.string(value).strip()
    if not description:
        return None
    if len(description) > MAX_PERSON_DESCRIPTION_LENGTH:
        raise vol.Invalid(f"description must not exceed {MAX_PERSON_DESCRIPTION_LENGTH} characters")
    return description


CREATE_PERSON_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_DISPLAY_NAME): _display_name,
        vol.Optional(ATTR_ENABLED, default=True): cv.boolean,
        vol.Optional(ATTR_DESCRIPTION): _description,
        vol.Optional(ATTR_NOTES): vol.Any(None, cv.string),
    }
)

UPDATE_PERSON_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_PERSON_ID): _person_id,
        vol.Optional(ATTR_DISPLAY_NAME): _display_name,
        vol.Optional(ATTR_ENABLED): cv.boolean,
        vol.Optional(ATTR_DESCRIPTION): _description,
        vol.Optional(ATTR_NOTES): vol.Any(None, cv.string),
    }
)

PERSON_ID_SCHEMA = vol.Schema({vol.Required(ATTR_PERSON_ID): _person_id})
EMPTY_SCHEMA = vol.Schema({})


async def _execute[ResultT](operation: Awaitable[ResultT]) -> ResultT:
    """Execute an application operation and expose Home Assistant errors."""
    try:
        return await operation
    except DuplicatePersonError as err:
        raise ServiceValidationError("A user with this display name already exists") from err
    except PersonNotFoundError as err:
        raise ServiceValidationError("User not found") from err
    except ValidationError as err:
        raise ServiceValidationError(str(err)) from err
    except StorageError as err:
        raise HomeAssistantError("HomePASS could not save User data") from err
    except LifecycleOperationExecutionError as err:
        raise HomeAssistantError("HomePASS could not remove access from every device") from err


def _person_response(person: Person) -> ServiceResponse:
    """Serialize one Person as action response data."""
    return cast(ServiceResponse, {"person": person.to_dict()})


async def _people_response(
    person_service: PersonService,
    person_card_service: PersonCardService | None,
) -> ServiceResponse:
    """Serialize People with PIN-safe card summaries from one storage snapshot."""
    if person_card_service is None:
        people = await person_service.list_people()
        return cast(ServiceResponse, {"people": [person.to_dict() for person in people]})
    return cast(ServiceResponse, {"people": list(await person_card_service.list_cards())})


async def _person_details_response(
    person: Person,
    metadata_service: AccessMetadataService,
    access_point_service: AccessPointService,
    person_schedule_service: PersonScheduleService,
    credential_replacement_service: CredentialReplacementLifecycleService,
    person_card_service: PersonCardService | None = None,
) -> ServiceResponse:
    """Serialize one Person with resolved, non-secret access summaries."""
    summaries: list[dict[str, object]] = []
    for metadata in await metadata_service.list_for_person(person.person_id):
        summary: dict[str, object] = dict(metadata.to_dict())
        summary["credential_stored"] = summary.pop("vault_credential_id") is not None
        summary["access_point_display_name"] = (
            await access_point_service.get_target(metadata.access_point_id)
        ).access_point.display_name
        summary["credential_capabilities"] = credential_replacement_service.capabilities_for(
            metadata
        )
        summaries.append(summary)
    response: dict[str, object] = {
        "person": person.to_dict(),
        "access_metadata": summaries,
        "credential_stored": (
            any(summary["credential_stored"] is True for summary in summaries)
            if person_card_service is None
            else await person_card_service.credential_stored(person.person_id)
        ),
    }
    try:
        state = await person_schedule_service.get_schedule_state(person.person_id)
        response["person"] = state.person.to_dict()
        response["effective_schedule"] = state.schedule.to_dict()
        names = {
            str(summary["access_point_id"]): summary["access_point_display_name"]
            for summary in summaries
        }
        response["schedule_groups"] = [
            {
                "schedule": group.schedule.to_dict(),
                "access_point_ids": [
                    str(access_point_id) for access_point_id in group.access_point_ids
                ],
                "access_point_names": [
                    names.get(str(access_point_id), "Door")
                    for access_point_id in group.access_point_ids
                ],
            }
            for group in state.groups
        ]
        response["schedule_status"] = "ok"
    except PersonScheduleConflictError as err:
        response["effective_schedule"] = None
        response["schedule_status"] = "conflict"
        response["schedule_summaries"] = [
            {
                "name": summary.name,
                "validity": summary.validity,
                "access_hours": summary.access_hours,
            }
            for summary in err.summaries
        ]
    return cast(ServiceResponse, response)


@callback
def async_register_person_actions(
    hass: HomeAssistant,
    person_service: PersonService,
    access_metadata_service: AccessMetadataService,
    access_point_service: AccessPointService,
    person_schedule_service: PersonScheduleService,
    credential_replacement_service: CredentialReplacementLifecycleService,
    person_policy_details_service: PersonPolicyDetailsService,
    person_card_service: PersonCardService | None = None,
) -> None:
    """Register HomePASS Person actions."""

    async def handle_create_person(call: ServiceCall) -> ServiceResponse:
        person = await _execute(
            person_service.create_person(
                cast(str, call.data[ATTR_DISPLAY_NAME]),
                cast(str | None, call.data.get(ATTR_NOTES)),
                description=cast(str | None, call.data.get(ATTR_DESCRIPTION)),
                enabled=cast(bool, call.data[ATTR_ENABLED]),
            )
        )
        return _person_response(person)

    async def handle_update_person(call: ServiceCall) -> ServiceResponse:
        person = await _execute(
            person_service.update_person(
                cast(UUID, call.data[ATTR_PERSON_ID]),
                display_name=cast(str | None, call.data.get(ATTR_DISPLAY_NAME)),
                enabled=cast(bool | None, call.data.get(ATTR_ENABLED)),
                description=cast(str | None, call.data.get(ATTR_DESCRIPTION)),
                description_provided=ATTR_DESCRIPTION in call.data,
                notes=cast(str | None, call.data.get(ATTR_NOTES)),
            )
        )
        return _person_response(person)

    async def handle_delete_person(call: ServiceCall) -> None:
        await _execute(person_service.delete_person(cast(UUID, call.data[ATTR_PERSON_ID])))

    async def handle_get_person(call: ServiceCall) -> ServiceResponse:
        person = await _execute(person_service.get_person(cast(UUID, call.data[ATTR_PERSON_ID])))
        try:
            return await _person_details_response(
                person,
                access_metadata_service,
                access_point_service,
                person_schedule_service,
                credential_replacement_service,
                person_card_service,
            )
        except StorageError as err:
            raise HomeAssistantError("HomePASS could not load access metadata") from err

    async def handle_get_person_policy_details(call: ServiceCall) -> ServiceResponse:
        try:
            details = await person_policy_details_service.get_person_policy_details(
                person_id=cast(UUID, call.data[ATTR_PERSON_ID]),
                instant_utc=datetime.now(UTC),
            )
        except PersonNotFoundError as err:
            raise ServiceValidationError("User not found") from err
        except HomePASSError:
            raise HomeAssistantError("Current access is unavailable") from None
        return cast(ServiceResponse, details.to_dict())

    async def handle_list_people(_call: ServiceCall) -> ServiceResponse:
        return await _execute(_people_response(person_service, person_card_service))

    hass.services.async_register(
        DOMAIN,
        SERVICE_CREATE_PERSON,
        handle_create_person,
        schema=CREATE_PERSON_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_UPDATE_PERSON,
        handle_update_person,
        schema=UPDATE_PERSON_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_DELETE_PERSON,
        handle_delete_person,
        schema=PERSON_ID_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_PERSON,
        handle_get_person,
        schema=PERSON_ID_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_LIST_PEOPLE,
        handle_list_people,
        schema=EMPTY_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_PERSON_POLICY_DETAILS,
        handle_get_person_policy_details,
        schema=PERSON_ID_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )


@callback
def async_unregister_person_actions(hass: HomeAssistant) -> None:
    """Remove HomePASS Person actions."""
    for action in PERSON_ACTIONS:
        hass.services.async_remove(DOMAIN, action)
