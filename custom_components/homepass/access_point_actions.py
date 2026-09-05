"""Home Assistant actions for HomePASS Access Points."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import cast
from uuid import UUID

import voluptuous as vol
from homeassistant.const import SERVICE_LOCK, SERVICE_UNLOCK
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
    callback,
)
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import entity_registry as er

from .const import (
    ATTR_ACCESS_POINT_ID,
    ATTR_CONTROL_ENTITY_ID,
    ATTR_CONTROL_PROFILE,
    ATTR_DISPLAY_NAME,
    ATTR_DEVICE_ID,
    ATTR_PULSE_SECONDS,
    ATTR_STATUS_ENTITY_ID,
    ATTR_STATUS_INVERTED,
    DOMAIN,
    SERVICE_ENROLL_ACCESS_POINT,
    SERVICE_ENROLL_HOME_ASSISTANT_ACCESS_POINT,
    SERVICE_GET_DOOR_DETAILS,
    SERVICE_LIST_ACCESS_POINTS,
    SERVICE_LIST_AVAILABLE_ACCESS_POINTS,
    SERVICE_LOCK_ACCESS_POINT,
    SERVICE_REMOVE_ACCESS_POINT,
    SERVICE_UPDATE_ACCESS_POINT,
    SERVICE_UNLOCK_ACCESS_POINT,
    SERVICE_OPEN_ACCESS_POINT,
)
from .battery import LOW_BATTERY_PERCENTAGE, CRITICAL_BATTERY_PERCENTAGE
from .exceptions import AccessPointHasGrantsError, HomePASSError
from .models import LockEventOrigin
from .nfc.repository import NfcAccessRepository
from .services import (
    AccessPointService,
    AccessPointSummary,
    AccessPointCommandService,
    DoorDetailsService,
    AccessDeviceService,
)

ACCESS_POINT_ACTIONS = (
    SERVICE_LIST_ACCESS_POINTS,
    SERVICE_LIST_AVAILABLE_ACCESS_POINTS,
    SERVICE_ENROLL_ACCESS_POINT,
    SERVICE_ENROLL_HOME_ASSISTANT_ACCESS_POINT,
    SERVICE_UPDATE_ACCESS_POINT,
    SERVICE_REMOVE_ACCESS_POINT,
    SERVICE_LOCK_ACCESS_POINT,
    SERVICE_UNLOCK_ACCESS_POINT,
    SERVICE_OPEN_ACCESS_POINT,
    SERVICE_GET_DOOR_DETAILS,
)
EMPTY_SCHEMA = vol.Schema({})
ACCESS_POINT_SCHEMA = vol.Schema({vol.Required(ATTR_ACCESS_POINT_ID): str})
OPEN_POLICY_FIELDS = {
    vol.Optional("open_enabled"): bool,
    vol.Optional("entry_action"): vol.In(("unlock", "open")),
}
ENROLL_ACCESS_POINT_SCHEMA = ACCESS_POINT_SCHEMA.extend(OPEN_POLICY_FIELDS)
UPDATE_ACCESS_POINT_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_ACCESS_POINT_ID): str,
        **OPEN_POLICY_FIELDS,
        vol.Optional(ATTR_DISPLAY_NAME): vol.All(str, vol.Length(min=1, max=80)),
        vol.Optional(ATTR_STATUS_ENTITY_ID): vol.Any(None, str),
        vol.Optional(ATTR_STATUS_INVERTED): bool,
    }
)
HOME_ASSISTANT_ACCESS_POINT_SCHEMA = vol.Schema(
    {
        **OPEN_POLICY_FIELDS,
        vol.Required(ATTR_DISPLAY_NAME): str,
        vol.Required(ATTR_DEVICE_ID): str,
        vol.Required(ATTR_CONTROL_ENTITY_ID): str,
        vol.Required(ATTR_CONTROL_PROFILE): vol.In(
            ("lock", "garage_cover", "garage_toggle", "electric_strike")
        ),
        vol.Optional(ATTR_STATUS_ENTITY_ID): str,
        vol.Optional(ATTR_STATUS_INVERTED, default=False): bool,
        vol.Optional(ATTR_PULSE_SECONDS, default=1.0): vol.All(
            vol.Coerce(float), vol.Range(min=0.1, max=10)
        ),
    }
)


def _access_points_response(
    access_points: tuple[AccessPointSummary, ...],
    nfc_tag_counts: dict[UUID, int] | None = None,
) -> ServiceResponse:
    """Serialize Access Points as action response data."""
    counts = nfc_tag_counts or {}
    items: list[dict[str, object]] = []
    for access_point in access_points:
        item = access_point.to_dict()
        count = counts.get(access_point.access_point.id, 0)
        item["nfc_enabled"] = count > 0
        item["nfc_tag_count"] = count
        items.append(item)
    return cast(
        ServiceResponse,
        {
            "access_points": items,
            "battery_thresholds": {
                "low": LOW_BATTERY_PERCENTAGE,
                "critical": CRITICAL_BATTERY_PERCENTAGE,
            },
        },
    )


@callback
def async_register_access_point_actions(
    hass: HomeAssistant,
    access_point_service: AccessPointService,
    door_details_service: DoorDetailsService,
    command_service: AccessPointCommandService,
    nfc_repository: NfcAccessRepository | None = None,
    access_device_service: AccessDeviceService | None = None,
) -> None:
    """Register HomePASS Access Point actions."""

    async def require_admin(call: ServiceCall) -> None:
        user = (
            await hass.auth.async_get_user(call.context.user_id)
            if call.context.user_id is not None
            else None
        )
        if user is None or not user.is_admin:
            raise ServiceValidationError("Only a HomePASS administrator can manage doors")

    async def nfc_tag_counts() -> dict[UUID, int]:
        if nfc_repository is None:
            return {}
        return await nfc_repository.enabled_tag_counts_by_access_point()

    async def handle_list_access_points(_call: ServiceCall) -> ServiceResponse:
        access_points = await access_point_service.list_access_point_summaries()
        response = _access_points_response(access_points, await nfc_tag_counts())
        devices = await access_device_service.list_views() if access_device_service else ()
        for door in response["access_points"]:
            door["access_device_batteries"] = [
                {
                    "id": str(view.device.id),
                    "display_name": view.device.display_name,
                    "battery_entity_id": view.battery_entity_id,
                    "battery_percentage": view.battery_percentage,
                    "battery_status": view.battery_status,
                }
                for view in sorted(devices, key=lambda view: str(view.device.id))
                if str(view.device.access_point_id) == door["id"] and view.battery_entity_id
            ]
        return response

    async def handle_list_available(_call: ServiceCall) -> ServiceResponse:
        return _access_points_response(
            await access_point_service.list_available_access_point_summaries(),
            await nfc_tag_counts(),
        )

    async def handle_enroll(call: ServiceCall) -> ServiceResponse:
        await require_admin(call)
        try:
            summary = await access_point_service.enroll_access_point(
                UUID(call.data[ATTR_ACCESS_POINT_ID]),
                open_enabled=call.data.get("open_enabled"),
                entry_action=call.data.get("entry_action", "unlock"),
            )
        except (TypeError, ValueError) as err:
            raise ServiceValidationError(str(err)) from None
        return cast(ServiceResponse, {"access_point": summary.to_dict()})

    async def handle_enroll_home_assistant(call: ServiceCall) -> ServiceResponse:
        await require_admin(call)
        device_id = call.data[ATTR_DEVICE_ID].strip()
        control_entity_id = call.data[ATTR_CONTROL_ENTITY_ID].strip()
        status_entity_id = call.data.get(ATTR_STATUS_ENTITY_ID)
        status_entity_id = status_entity_id.strip() if status_entity_id else None
        profile = call.data[ATTR_CONTROL_PROFILE]
        control = hass.states.get(control_entity_id)
        if control is None:
            raise ServiceValidationError("The selected control entity is unavailable")
        registry = er.async_get(hass)
        control_entry = registry.async_get(control_entity_id)
        if control_entry is None or control_entry.device_id != device_id:
            raise ServiceValidationError(
                "The selected control entity does not belong to the selected device"
            )
        domain = control_entity_id.split(".", 1)[0]
        allowed_domains = {
            "lock": {"lock"},
            "garage_cover": {"cover"},
            "garage_toggle": {"button", "switch"},
            "electric_strike": {"button", "switch", "lock"},
        }[profile]
        if domain not in allowed_domains:
            raise ServiceValidationError(
                f"The selected {profile.replace('_', ' ')} control must be one of: "
                + ", ".join(sorted(allowed_domains))
            )
        if status_entity_id == control_entity_id:
            raise ServiceValidationError("Control and status entities must be different")
        if status_entity_id is not None and hass.states.get(status_entity_id) is None:
            raise ServiceValidationError("The selected status entity is unavailable")
        if status_entity_id is not None and status_entity_id.split(".", 1)[0] not in {
            "binary_sensor",
            "cover",
            "lock",
            "sensor",
            "input_boolean",
        }:
            raise ServiceValidationError("The selected status entity cannot report door state")
        try:
            summary = await access_point_service.enroll_home_assistant_access_point(
                display_name=call.data[ATTR_DISPLAY_NAME],
                control_entity_id=control_entity_id,
                control_profile=profile,
                status_entity_id=status_entity_id,
                device_id=device_id,
                status_inverted=call.data[ATTR_STATUS_INVERTED],
                pulse_seconds=call.data[ATTR_PULSE_SECONDS],
                open_enabled=call.data.get("open_enabled"),
                entry_action=call.data.get("entry_action", "unlock"),
            )
        except (TypeError, ValueError) as err:
            raise ServiceValidationError(str(err)) from None
        return cast(ServiceResponse, {"access_point": summary.to_dict()})

    async def handle_remove(call: ServiceCall) -> ServiceResponse:
        await require_admin(call)
        try:
            await access_point_service.remove_access_point(UUID(call.data[ATTR_ACCESS_POINT_ID]))
        except AccessPointHasGrantsError as err:
            raise ServiceValidationError(str(err)) from None
        except (TypeError, ValueError) as err:
            raise ServiceValidationError(str(err)) from None
        return cast(ServiceResponse, {"removed": True})

    async def handle_update(call: ServiceCall) -> ServiceResponse:
        await require_admin(call)
        has_name = ATTR_DISPLAY_NAME in call.data
        has_status = ATTR_STATUS_ENTITY_ID in call.data
        has_inversion = ATTR_STATUS_INVERTED in call.data
        has_open = "open_enabled" in call.data or "entry_action" in call.data
        if has_open and not {"open_enabled", "entry_action"} <= call.data.keys():
            raise ServiceValidationError("Confirm Open Door permission and entry action together")
        if not has_name and not has_status and not has_open:
            raise ServiceValidationError("Choose a Door setting to update")
        if has_inversion and not has_status:
            raise ServiceValidationError("Choose a status entity before changing its direction")
        try:
            access_point_id = UUID(call.data[ATTR_ACCESS_POINT_ID])
            response: dict[str, object]
            if has_name:
                access_point = await access_point_service.update_access_point_policy(
                    access_point_id,
                    display_name=call.data[ATTR_DISPLAY_NAME],
                )
                response = dict(access_point.to_dict())
            else:
                response = {}
            if has_open:
                summary = await access_point_service.update_open_policy(
                    access_point_id,
                    open_enabled=call.data["open_enabled"],
                    entry_action=call.data["entry_action"],
                )
                response = summary.to_dict()
            if has_status:
                raw_status = call.data.get(ATTR_STATUS_ENTITY_ID)
                status_entity_id = raw_status.strip() if raw_status else None
                target = await access_point_service.get_target(access_point_id)
                if status_entity_id == target.control_entity_id:
                    raise ValueError("Control and status entities must be different")
                if status_entity_id is not None and hass.states.get(status_entity_id) is None:
                    raise ValueError("The selected status entity is unavailable")
                if status_entity_id is not None and status_entity_id.split(".", 1)[0] not in {
                    "binary_sensor",
                    "cover",
                    "lock",
                    "sensor",
                    "input_boolean",
                }:
                    raise ValueError("The selected status entity cannot report door state")
                summary = await access_point_service.update_access_point_status(
                    access_point_id,
                    status_entity_id=status_entity_id,
                    status_inverted=call.data.get(ATTR_STATUS_INVERTED, False),
                )
                response = summary.to_dict()
        except (TypeError, ValueError) as err:
            raise ServiceValidationError(str(err)) from None
        return cast(ServiceResponse, {"access_point": response})

    async def handle_get_door_details(call: ServiceCall) -> ServiceResponse:
        try:
            target = await access_point_service.get_target(UUID(call.data[ATTR_ACCESS_POINT_ID]))
            details = await door_details_service.get_door_details(
                access_point=target.access_point,
                instant_utc=datetime.now(UTC),
            )
        except (TypeError, ValueError) as err:
            raise ServiceValidationError(str(err)) from None
        except HomePASSError:
            raise HomeAssistantError("Current access is unavailable") from None
        return cast(ServiceResponse, details.to_dict())

    async def handle_operation(call: ServiceCall, operation: str) -> ServiceResponse:
        try:
            result = await command_service.execute(
                UUID(call.data[ATTR_ACCESS_POINT_ID]),
                operation,
                origin=LockEventOrigin.HOMEPASS_MANUAL,
                context=call.context,
            )
        except (TypeError, ValueError) as err:
            raise ServiceValidationError(str(err)) from None
        return cast(
            ServiceResponse,
            {
                "command_sent": result.command_sent,
                "confirmation_required": result.confirmation_required,
            },
        )

    async def handle_lock(call: ServiceCall) -> ServiceResponse:
        return await handle_operation(call, SERVICE_LOCK)

    async def handle_unlock(call: ServiceCall) -> ServiceResponse:
        return await handle_operation(call, SERVICE_UNLOCK)

    async def handle_open(call: ServiceCall) -> ServiceResponse:
        return await handle_operation(call, "open")

    hass.services.async_register(
        DOMAIN,
        SERVICE_OPEN_ACCESS_POINT,
        handle_open,
        schema=ACCESS_POINT_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_LIST_ACCESS_POINTS,
        handle_list_access_points,
        schema=EMPTY_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_LIST_AVAILABLE_ACCESS_POINTS,
        handle_list_available,
        schema=EMPTY_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_ENROLL_ACCESS_POINT,
        handle_enroll,
        schema=ENROLL_ACCESS_POINT_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_ENROLL_HOME_ASSISTANT_ACCESS_POINT,
        handle_enroll_home_assistant,
        schema=HOME_ASSISTANT_ACCESS_POINT_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_UPDATE_ACCESS_POINT,
        handle_update,
        schema=UPDATE_ACCESS_POINT_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_REMOVE_ACCESS_POINT,
        handle_remove,
        schema=ACCESS_POINT_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_DOOR_DETAILS,
        handle_get_door_details,
        schema=ACCESS_POINT_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_LOCK_ACCESS_POINT,
        handle_lock,
        schema=ACCESS_POINT_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_UNLOCK_ACCESS_POINT,
        handle_unlock,
        schema=ACCESS_POINT_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )


@callback
def async_unregister_access_point_actions(hass: HomeAssistant) -> None:
    """Remove HomePASS Access Point actions."""
    for action in ACCESS_POINT_ACTIONS:
        hass.services.async_remove(DOMAIN, action)
