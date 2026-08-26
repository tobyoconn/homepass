"""Access-device discovery tests."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from custom_components.homepass.access_device_discovery import (
    HomeAssistantAccessDeviceDiscovery,
)
from custom_components.homepass.models import AccessDeviceIntegration


class _States:
    def __init__(self, states: dict[str, str]) -> None:
        self._states = states

    def get(self, entity_id: str) -> object | None:
        state = self._states.get(entity_id)
        return None if state is None else SimpleNamespace(state=state, attributes={})


class _Entities(dict[str, SimpleNamespace]):
    """Minimal entity-registry mapping compatible with current Home Assistant."""

    def get_entries_for_device_id(
        self,
        device_id: str,
        include_disabled_entities: bool = False,
    ) -> list[SimpleNamespace]:
        return [
            entry
            for entry in self.values()
            if entry.device_id == device_id
            and (include_disabled_entities or entry.disabled_by is None)
        ]


@pytest.mark.asyncio
async def test_discovers_observed_zigbee2mqtt_frient_registry_shape(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    device = SimpleNamespace(
        id="mqtt-device-id",
        name="garage_keypad",
        name_by_user="Garage keypad",
        manufacturer="Develco",
        model="Keypad",
        model_id="KEYZB-110",
        identifiers={("mqtt", "zigbee2mqtt_0x0200000000000001")},
    )
    entities = _Entities(
        {
            name: SimpleNamespace(
                device_id=device.id,
                entity_id=f"sensor.garage_keypad_{suffix}",
                original_name=name,
                platform="mqtt",
                domain="sensor",
                device_class=None,
                original_device_class=None,
                disabled_by=disabled_by,
            )
            for name, suffix, disabled_by in (
                ("Action code", "action_code", "user"),
                ("Action transaction", "action_transaction", None),
                ("Action zone", "action_zone", None),
                ("Voltage", "voltage", None),
            )
        }
    )
    hass = SimpleNamespace(
        states=_States({"sensor.garage_keypad_voltage": "6300"}),
    )
    monkeypatch.setattr(
        "custom_components.homepass.access_device_discovery.dr.async_get",
        lambda _hass: SimpleNamespace(devices={device.id: device}),
    )
    monkeypatch.setattr(
        "custom_components.homepass.access_device_discovery.er.async_get",
        lambda _hass: SimpleNamespace(entities=entities),
    )

    discovered = await HomeAssistantAccessDeviceDiscovery(hass).discover_supported()

    assert len(discovered) == 1
    candidate = discovered[0]
    assert candidate.integration is AccessDeviceIntegration.ZIGBEE2MQTT
    assert candidate.home_assistant_device_id == "mqtt-device-id"
    assert candidate.display_name == "Garage keypad"
    assert candidate.available is True
    assert candidate.zigbee_ieee_address == "0x0200000000000001"
    assert candidate.zigbee2mqtt_base_topic == "zigbee2mqtt"
    assert candidate.zigbee2mqtt_friendly_name == "garage_keypad"


@pytest.mark.asyncio
async def test_rejects_generic_mqtt_keypad_without_complete_action_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    device = SimpleNamespace(
        id="mqtt-device-id",
        name="garage_keypad",
        name_by_user=None,
        manufacturer="Develco",
        model="Keypad",
        model_id="KEYZB-110",
        identifiers={("mqtt", "zigbee2mqtt_0x0200000000000001")},
    )
    entity = SimpleNamespace(
        device_id=device.id,
        entity_id="sensor.garage_keypad_action_code",
        original_name="Action code",
        platform="mqtt",
        domain="sensor",
        device_class=None,
        original_device_class=None,
        disabled_by="user",
    )
    hass = SimpleNamespace(states=_States({}))
    monkeypatch.setattr(
        "custom_components.homepass.access_device_discovery.dr.async_get",
        lambda _hass: SimpleNamespace(devices={device.id: device}),
    )
    monkeypatch.setattr(
        "custom_components.homepass.access_device_discovery.er.async_get",
        lambda _hass: SimpleNamespace(entities=_Entities({entity.entity_id: entity})),
    )

    assert await HomeAssistantAccessDeviceDiscovery(hass).discover_supported() == ()
