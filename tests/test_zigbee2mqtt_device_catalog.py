"""Zigbee2MQTT retained device-catalog parsing tests."""

import json

from custom_components.homepass.zigbee2mqtt_device_catalog import (
    parse_zigbee2mqtt_device_catalog,
)


def test_catalog_returns_only_supported_complete_keypads() -> None:
    payload = json.dumps(
        [
            {
                "ieee_address": "02:00:00:00:00:00:00:01",
                "friendly_name": "garage/keypad",
                "disabled": False,
                "interview_state": "SUCCESSFUL",
                "definition": {"vendor": "frient", "model": "KEPZB-110"},
            },
            {
                "ieee_address": "0x00124b0000000001",
                "friendly_name": "lamp",
                "disabled": False,
                "interview_state": "SUCCESSFUL",
                "definition": {"vendor": "Example", "model": "Lamp"},
            },
        ]
    )

    devices = parse_zigbee2mqtt_device_catalog(payload)

    assert len(devices) == 1
    assert devices[0].ieee_address == "0x0200000000000001"
    assert devices[0].friendly_name == "garage/keypad"
    assert devices[0].available is True


def test_catalog_rejects_malformed_json_and_unsafe_friendly_name() -> None:
    assert parse_zigbee2mqtt_device_catalog("not-json") == ()
    assert (
        parse_zigbee2mqtt_device_catalog(
            json.dumps(
                [
                    {
                        "ieee_address": "0x0200000000000001",
                        "friendly_name": "garage/#",
                        "disabled": False,
                        "interview_state": "SUCCESSFUL",
                        "definition": {"vendor": "Develco", "model": "KEYZB-110"},
                    }
                ]
            )
        )
        == ()
    )
