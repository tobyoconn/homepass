"""Shared fixtures for HomePASS tests."""

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.homepass.const import CONF_INSTANCE_NAME, DOMAIN, NAME


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Enable loading HomePASS as a custom integration."""


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Return a HomePASS config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        title=NAME,
        data={CONF_INSTANCE_NAME: NAME},
    )
