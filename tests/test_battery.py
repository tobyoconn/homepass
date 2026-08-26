"""Battery discovery, alerting, copy, and frontend coverage."""

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from custom_components.homepass.battery import (
    BatteryStatus,
    resolve_entity_battery,
    status_for_percentage,
)
from custom_components.homepass.models import (
    NOTIFICATION_DEFINITIONS,
    AccessPoint,
    ActivityActorType,
    ActivityCategory,
    ActivityEvent,
    ActivityEventType,
    ActivitySeverity,
    ActivitySource,
    NotificationEvent,
)
from custom_components.homepass.services import (
    AccessPointAvailability,
    AccessPointState,
    AccessPointSummary,
    BatteryMonitoringService,
)
from custom_components.homepass.services.notification import format_notification

_FRONTEND = (
    Path(__file__).parents[1] / "custom_components" / "homepass" / "frontend" / "homepass-panel.js"
)


def test_battery_percentage_thresholds_are_explicit() -> None:
    assert status_for_percentage(100) is BatteryStatus.NORMAL
    assert status_for_percentage(21) is BatteryStatus.NORMAL
    assert status_for_percentage(20) is BatteryStatus.LOW
    assert status_for_percentage(11) is BatteryStatus.LOW
    assert status_for_percentage(10) is BatteryStatus.CRITICAL
    assert status_for_percentage(0) is BatteryStatus.CRITICAL


async def test_device_battery_entity_is_discovered_for_lock(hass, mock_config_entry) -> None:
    mock_config_entry.add_to_hass(hass)
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=mock_config_entry.entry_id,
        identifiers={("battery_test", "front-door")},
    )
    registry = er.async_get(hass)
    lock = registry.async_get_or_create(
        "lock",
        "battery_test",
        "front-door-lock",
        suggested_object_id="front_door",
        device_id=device.id,
    )
    battery = registry.async_get_or_create(
        "sensor",
        "battery_test",
        "front-door-battery",
        suggested_object_id="front_door_battery",
        device_id=device.id,
        original_device_class="battery",
    )
    hass.states.async_set(battery.entity_id, "54", {"device_class": "battery"})

    reading = resolve_entity_battery(hass, lock.entity_id)

    assert reading is not None
    assert reading.entity_id == battery.entity_id
    assert reading.percentage == 54
    assert reading.status is BatteryStatus.NORMAL


async def test_monitoring_is_quiet_at_start_and_alerts_on_escalation(hass) -> None:
    access_point = AccessPoint(display_name="Computer Room")
    summary = AccessPointSummary(
        access_point,
        AccessPointState(
            AccessPointAvailability.AVAILABLE,
            battery_entity_id="sensor.computer_room_battery",
        ),
    )
    access_points = MagicMock()
    access_points.list_access_point_summaries = AsyncMock(return_value=(summary,))
    access_points.add_change_listener.return_value = lambda: None
    access_devices = MagicMock()
    access_devices.list_views = AsyncMock(return_value=())
    activity = AsyncMock()
    hass.states.async_set("sensor.computer_room_battery", "50", {"device_class": "battery"})
    service = BatteryMonitoringService(hass, access_points, access_devices, activity)

    await service.async_start()
    await hass.async_block_till_done()
    activity.record.assert_not_awaited()

    hass.states.async_set("sensor.computer_room_battery", "20", {"device_class": "battery"})
    await hass.async_block_till_done()
    low = activity.record.await_args_list[0].args[0]
    assert low.event_type is ActivityEventType.BATTERY_LOW
    assert low.door_name == "Computer Room"
    assert low.attributes == {"battery_percentage": 20}

    hass.states.async_set("sensor.computer_room_battery", "10", {"device_class": "battery"})
    await hass.async_block_till_done()
    critical = activity.record.await_args_list[1].args[0]
    assert critical.event_type is ActivityEventType.BATTERY_CRITICAL
    assert critical.attributes == {"battery_percentage": 10}

    await service.async_stop()


def test_battery_notification_includes_the_available_percentage() -> None:
    now = datetime.now(UTC)
    activity = ActivityEvent(
        event_id=uuid4(),
        occurred_at=now,
        recorded_at=now,
        event_type=ActivityEventType.BATTERY_CRITICAL,
        category=ActivityCategory.MAINTENANCE,
        severity=ActivitySeverity.CRITICAL,
        source=ActivitySource.HOME_ASSISTANT,
        actor_type=ActivityActorType.SYSTEM,
        door_id=uuid4(),
        door_name="Computer Room door sensor",
        attributes={"battery_percentage": 8},
    )

    notification = format_notification(
        activity, NOTIFICATION_DEFINITIONS[NotificationEvent.BATTERY_CRITICAL]
    )

    assert notification.message == "Computer Room door sensor battery is critically low (8%)."


def test_doors_and_devices_frontend_presents_supported_batteries() -> None:
    source = _FRONTEND.read_text(encoding="utf-8")

    assert "door_sensor_battery_percentage" in source
    assert 'class="device-battery' in source
    assert '"mdi:battery-alert"' in source
    assert 'status === "critical" ? "critical"' in source
