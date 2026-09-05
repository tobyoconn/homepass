"""Tests for the HomePASS config flow."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.homepass.config_flow import HomePassOptionsFlow
from custom_components.homepass.const import (
    CONF_INSTANCE_NAME,
    CONF_NFC_PUBLIC_ORIGIN,
    CONF_NUKI_BLE_ADDRESS,
    CONF_NUKI_BLE_CREDENTIAL_ID,
    CONF_NUKI_ENABLED,
    CONF_NUKI_LOCK_ENTITY_ID,
    CONF_NUKI_SECURITY_PIN,
    DOMAIN,
    NAME,
)
from custom_components.homepass.models import AccessDriver
from custom_components.homepass.providers.base import (
    AuthorizationMutation,
    AuthorizationMutationState,
    AuthorizationRecord,
    ProviderCommunicationError,
)
from custom_components.homepass.providers.nuki_bluetooth import (
    NukiBluetoothCredential,
    NukiBluetoothOperationError,
    NukiBluetoothPairer,
    NukiBluetoothPairingError,
)
from custom_components.homepass.providers.nuki_local import NukiLocalAuthorizationProvider
from custom_components.homepass.vault.api import CredentialVault


async def test_user_flow(hass: HomeAssistant) -> None:
    """Test creating a HomePASS config entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_INSTANCE_NAME: "  My Home  "},
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "My Home"
    assert result["data"] == {CONF_INSTANCE_NAME: "My Home"}


async def test_user_flow_rejects_blank_name(
    hass: HomeAssistant,
) -> None:
    """Test that an instance name cannot be blank."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_INSTANCE_NAME: "   "},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_INSTANCE_NAME: "invalid_instance_name"}


async def test_user_flow_aborts_when_configured(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test that only one HomePASS instance can be configured."""
    mock_config_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "single_instance_allowed"


async def test_user_flow_uses_default_name(
    hass: HomeAssistant,
) -> None:
    """Test the default instance name."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {},
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == NAME


async def test_options_flow_prevents_unrelated_credential_autofill(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    monkeypatch,
) -> None:
    """NFC and Nuki fields must not be mistaken for saved login credentials."""
    monkeypatch.setattr(
        HomePassOptionsFlow,
        "_discovered_nuki_locks",
        lambda self, current: {},
    )
    mock_config_entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)

    assert result["type"] is FlowResultType.FORM
    fields = {marker.schema: field for marker, field in result["data_schema"].schema.items()}
    assert fields[CONF_NFC_PUBLIC_ORIGIN].config["autocomplete"] == "url"
    assert fields[CONF_NUKI_SECURITY_PIN].config["autocomplete"] == "new-password"


async def test_options_flow_pairs_nuki_without_storing_security_pin(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    monkeypatch,
) -> None:
    """Nuki pairing material is vaulted and the Security PIN is not an option."""
    address = "AA:BB:CC:DD:EE:FF"
    credential = NukiBluetoothCredential(
        auth_id="01" * 4,
        nuki_public_key="02" * 32,
        client_public_key="03" * 32,
        client_private_key="04" * 32,
        app_id=42,
        security_pin="123456",
    )
    monkeypatch.setattr(
        HomePassOptionsFlow,
        "_discovered_nuki_locks",
        lambda self, current: {address: f"Nuki Ultra — {address}"},
    )
    pair = AsyncMock(return_value=credential)
    monkeypatch.setattr(NukiBluetoothPairer, "pair", pair)
    monkeypatch.setattr(
        HomePassOptionsFlow,
        "_list_unmanaged_nuki_authorizations",
        AsyncMock(return_value=()),
    )
    mock_config_entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_NFC_PUBLIC_ORIGIN: "",
            CONF_NUKI_ENABLED: True,
            CONF_NUKI_LOCK_ENTITY_ID: "lock.computer_room_computer_room_smart_lock",
            CONF_NUKI_BLE_ADDRESS: address,
            CONF_NUKI_SECURITY_PIN: "123456",
        },
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_NUKI_BLE_ADDRESS] == address
    assert result["data"][CONF_NUKI_BLE_CREDENTIAL_ID]
    assert CONF_NUKI_SECURITY_PIN not in result["data"]
    pair.assert_awaited_once_with(address, "123456")


async def test_options_flow_uses_existing_label_for_pairing_diagnostics(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    monkeypatch,
) -> None:
    """Pairing diagnostics remain actionable in the options form."""
    address = "AA:BB:CC:DD:EE:FF"
    monkeypatch.setattr(
        HomePassOptionsFlow,
        "_discovered_nuki_locks",
        lambda self, current: {address: f"Nuki Ultra — {address}"},
    )
    monkeypatch.setattr(
        NukiBluetoothPairer,
        "pair",
        AsyncMock(
            side_effect=NukiBluetoothPairingError(
                "nuki_pairing_not_enabled",
                "authorize",
            )
        ),
    )
    mock_config_entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_NFC_PUBLIC_ORIGIN: "",
            CONF_NUKI_ENABLED: True,
            CONF_NUKI_LOCK_ENTITY_ID: "lock.computer_room",
            CONF_NUKI_BLE_ADDRESS: address,
            CONF_NUKI_SECURITY_PIN: "123456",
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "nuki_pairing_failed"}
    assert result["description_placeholders"]["diagnostic"].startswith(
        "Pairing stage: the lock is reachable"
    )


async def test_options_flow_contains_unexpected_pairing_failure(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    monkeypatch,
) -> None:
    """Unexpected Bluetooth dependency errors never escape as HA's unknown error."""
    address = "AA:BB:CC:DD:EE:FF"
    monkeypatch.setattr(
        HomePassOptionsFlow,
        "_discovered_nuki_locks",
        lambda self, current: {address: f"Nuki Ultra — {address}"},
    )
    monkeypatch.setattr(
        NukiBluetoothPairer,
        "pair",
        AsyncMock(side_effect=RuntimeError("upstream detail must remain private")),
    )
    mock_config_entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_NFC_PUBLIC_ORIGIN: "",
            CONF_NUKI_ENABLED: True,
            CONF_NUKI_LOCK_ENTITY_ID: "lock.computer_room",
            CONF_NUKI_BLE_ADDRESS: address,
            CONF_NUKI_SECURITY_PIN: "123456",
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "nuki_pairing_failed"}


async def test_options_flow_retains_existing_nuki_pairing_when_pin_is_blank(
    hass: HomeAssistant,
    monkeypatch,
) -> None:
    """Reconfiguration never requires the existing Security PIN in the form."""
    address = "AA:BB:CC:DD:EE:FF"
    credential_id = "4ecbaf4e-b93d-4187-a15f-fcd0bc91dd08"
    credential = NukiBluetoothCredential(
        auth_id="01" * 4,
        nuki_public_key="02" * 32,
        client_public_key="03" * 32,
        client_private_key="04" * 32,
        app_id=42,
        security_pin="123456",
    )
    monkeypatch.setattr(
        HomePassOptionsFlow,
        "_discovered_nuki_locks",
        lambda self, current: {address: f"Nuki Ultra — {address}"},
    )
    pair = AsyncMock()
    monkeypatch.setattr(NukiBluetoothPairer, "pair", pair)
    monkeypatch.setattr(CredentialVault, "retrieve", AsyncMock(return_value=credential.serialize()))
    monkeypatch.setattr(
        HomePassOptionsFlow,
        "_list_unmanaged_nuki_authorizations",
        AsyncMock(return_value=(AuthorizationRecord("17", "Existing guest", True),)),
    )
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_INSTANCE_NAME: NAME},
        options={
            CONF_NUKI_ENABLED: True,
            CONF_NUKI_LOCK_ENTITY_ID: "lock.computer_room_computer_room_smart_lock",
            CONF_NUKI_BLE_ADDRESS: address,
            CONF_NUKI_BLE_CREDENTIAL_ID: credential_id,
        },
    )
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_NFC_PUBLIC_ORIGIN: "",
            CONF_NUKI_ENABLED: True,
            CONF_NUKI_LOCK_ENTITY_ID: "lock.computer_room_computer_room_smart_lock",
            CONF_NUKI_BLE_ADDRESS: address,
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "nuki_existing_pins"
    assert "nuki_delete_all_authorizations" not in {
        marker.schema for marker in result["data_schema"].schema
    }
    result = await hass.config_entries.options.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_NUKI_BLE_CREDENTIAL_ID] == credential_id
    pair.assert_not_awaited()


async def test_options_flow_reuses_existing_pairing_even_if_pin_is_supplied(
    hass: HomeAssistant,
    monkeypatch,
) -> None:
    """An existing authorization is never replaced merely because a PIN was autofilled."""
    address = "AA:BB:CC:DD:EE:FF"
    credential_id = "4ecbaf4e-b93d-4187-a15f-fcd0bc91dd08"
    credential = NukiBluetoothCredential(
        auth_id="01" * 4,
        nuki_public_key="02" * 32,
        client_public_key="03" * 32,
        client_private_key="04" * 32,
        app_id=42,
        security_pin="123456",
    )
    monkeypatch.setattr(
        HomePassOptionsFlow,
        "_discovered_nuki_locks",
        lambda self, current: {address: f"Nuki Ultra — {address}"},
    )
    pair = AsyncMock()
    monkeypatch.setattr(NukiBluetoothPairer, "pair", pair)
    monkeypatch.setattr(CredentialVault, "retrieve", AsyncMock(return_value=credential.serialize()))
    monkeypatch.setattr(
        HomePassOptionsFlow,
        "_list_unmanaged_nuki_authorizations",
        AsyncMock(side_effect=NukiBluetoothOperationError("connection", "TimeoutError")),
    )
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_INSTANCE_NAME: NAME},
        options={
            CONF_NUKI_ENABLED: True,
            CONF_NUKI_LOCK_ENTITY_ID: "lock.computer_room",
            CONF_NUKI_BLE_ADDRESS: address,
            CONF_NUKI_BLE_CREDENTIAL_ID: credential_id,
        },
    )
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_NFC_PUBLIC_ORIGIN: "",
            CONF_NUKI_ENABLED: True,
            CONF_NUKI_LOCK_ENTITY_ID: "lock.computer_room",
            CONF_NUKI_BLE_ADDRESS: address,
            CONF_NUKI_SECURITY_PIN: "654321",
        },
    )

    assert result["errors"] == {"base": "nuki_pairing_failed"}
    assert "connection stage" in result["description_placeholders"]["diagnostic"]
    pair.assert_not_awaited()


async def test_options_flow_contains_existing_pairing_scan_timeout(
    hass: HomeAssistant,
    monkeypatch,
) -> None:
    """A stalled stored-authorization check finishes before HA cancels the flow."""
    address = "AA:BB:CC:DD:EE:FF"
    credential_id = "4ecbaf4e-b93d-4187-a15f-fcd0bc91dd08"
    credential = NukiBluetoothCredential(
        auth_id="01" * 4,
        nuki_public_key="02" * 32,
        client_public_key="03" * 32,
        client_private_key="04" * 32,
        app_id=42,
        security_pin="123456",
    )
    monkeypatch.setattr(
        HomePassOptionsFlow,
        "_discovered_nuki_locks",
        lambda self, current: {address: f"Nuki Ultra — {address}"},
    )
    monkeypatch.setattr(CredentialVault, "retrieve", AsyncMock(return_value=credential.serialize()))

    async def stall(*args, **kwargs):
        await asyncio.sleep(60)

    monkeypatch.setattr(
        HomePassOptionsFlow,
        "_list_unmanaged_nuki_authorizations",
        stall,
    )
    monkeypatch.setattr(
        "custom_components.homepass.config_flow._NUKI_AUTHORIZATION_SCAN_TIMEOUT",
        0.01,
    )
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_INSTANCE_NAME: NAME},
        options={
            CONF_NUKI_ENABLED: True,
            CONF_NUKI_LOCK_ENTITY_ID: "lock.computer_room",
            CONF_NUKI_BLE_ADDRESS: address,
            CONF_NUKI_BLE_CREDENTIAL_ID: credential_id,
        },
    )
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_NFC_PUBLIC_ORIGIN: "",
            CONF_NUKI_ENABLED: True,
            CONF_NUKI_LOCK_ENTITY_ID: "lock.computer_room",
            CONF_NUKI_BLE_ADDRESS: address,
        },
    )

    assert result["errors"] == {"base": "nuki_pairing_failed"}
    assert "overall timeout" in result["description_placeholders"]["diagnostic"]


async def test_options_flow_keeps_existing_nuki_pins_by_default(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    monkeypatch,
) -> None:
    """Existing Nuki codes survive reconciliation unless explicitly selected."""
    address = "AA:BB:CC:DD:EE:FF"
    credential = NukiBluetoothCredential(
        auth_id="01" * 4,
        nuki_public_key="02" * 32,
        client_public_key="03" * 32,
        client_private_key="04" * 32,
        app_id=42,
        security_pin="123456",
    )
    existing = (AuthorizationRecord("17", "Existing guest", True),)
    monkeypatch.setattr(
        HomePassOptionsFlow,
        "_discovered_nuki_locks",
        lambda self, current: {address: f"Nuki Ultra — {address}"},
    )
    monkeypatch.setattr(NukiBluetoothPairer, "pair", AsyncMock(return_value=credential))
    monkeypatch.setattr(
        HomePassOptionsFlow,
        "_list_unmanaged_nuki_authorizations",
        AsyncMock(return_value=existing),
    )
    remove = AsyncMock()
    monkeypatch.setattr(NukiLocalAuthorizationProvider, "delete_authorization", remove)
    mock_config_entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_NFC_PUBLIC_ORIGIN: "",
            CONF_NUKI_ENABLED: True,
            CONF_NUKI_LOCK_ENTITY_ID: "lock.front_door",
            CONF_NUKI_BLE_ADDRESS: address,
            CONF_NUKI_SECURITY_PIN: "123456",
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "nuki_existing_pins"
    assert "nuki_delete_all_authorizations" in {
        marker.schema for marker in result["data_schema"].schema
    }
    result = await hass.config_entries.options.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    remove.assert_not_awaited()


async def test_initial_pairing_can_delete_every_existing_nuki_pin(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    monkeypatch,
) -> None:
    """First pairing offers one explicit switch to clear all discovered PINs."""
    address = "AA:BB:CC:DD:EE:FF"
    credential = NukiBluetoothCredential(
        auth_id="01" * 4,
        nuki_public_key="02" * 32,
        client_public_key="03" * 32,
        client_private_key="04" * 32,
        app_id=42,
        security_pin="123456",
    )
    existing = (
        AuthorizationRecord("17", "Old guest", True),
        AuthorizationRecord("18", "Old cleaner", False),
    )
    monkeypatch.setattr(
        HomePassOptionsFlow,
        "_discovered_nuki_locks",
        lambda self, current: {address: f"Nuki Ultra — {address}"},
    )
    monkeypatch.setattr(NukiBluetoothPairer, "pair", AsyncMock(return_value=credential))
    monkeypatch.setattr(
        HomePassOptionsFlow,
        "_list_unmanaged_nuki_authorizations",
        AsyncMock(return_value=existing),
    )
    remove = AsyncMock(
        side_effect=(
            AuthorizationMutation(AuthorizationMutationState.PENDING, external_id="17"),
            AuthorizationMutation(AuthorizationMutationState.PENDING, external_id="18"),
        )
    )
    monkeypatch.setattr(NukiLocalAuthorizationProvider, "delete_authorization", remove)
    monkeypatch.setattr(
        NukiLocalAuthorizationProvider,
        "list_authorizations",
        AsyncMock(return_value=()),
    )
    mock_config_entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_NFC_PUBLIC_ORIGIN: "",
            CONF_NUKI_ENABLED: True,
            CONF_NUKI_LOCK_ENTITY_ID: "lock.front_door",
            CONF_NUKI_BLE_ADDRESS: address,
            CONF_NUKI_SECURITY_PIN: "123456",
        },
    )

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"nuki_delete_all_authorizations": True}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "nuki_confirm_delete"
    remove.assert_not_awaited()

    result = await hass.config_entries.options.async_configure(result["flow_id"], {})

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert [call.args[0] for call in remove.await_args_list] == ["17", "18"]


async def test_options_flow_deletes_only_selected_existing_nuki_pins(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    monkeypatch,
) -> None:
    """Reconciliation deletes an explicit code and confirms its absence."""
    address = "AA:BB:CC:DD:EE:FF"
    credential = NukiBluetoothCredential(
        auth_id="01" * 4,
        nuki_public_key="02" * 32,
        client_public_key="03" * 32,
        client_private_key="04" * 32,
        app_id=42,
        security_pin="123456",
    )
    existing = (
        AuthorizationRecord("17", "Remove me", True),
        AuthorizationRecord("18", "Keep me", True),
    )
    monkeypatch.setattr(
        HomePassOptionsFlow,
        "_discovered_nuki_locks",
        lambda self, current: {address: f"Nuki Ultra — {address}"},
    )
    monkeypatch.setattr(NukiBluetoothPairer, "pair", AsyncMock(return_value=credential))
    monkeypatch.setattr(
        HomePassOptionsFlow,
        "_list_unmanaged_nuki_authorizations",
        AsyncMock(return_value=existing),
    )
    remove = AsyncMock(
        return_value=AuthorizationMutation(AuthorizationMutationState.PENDING, external_id="17")
    )
    monkeypatch.setattr(NukiLocalAuthorizationProvider, "delete_authorization", remove)
    monkeypatch.setattr(
        NukiLocalAuthorizationProvider,
        "list_authorizations",
        AsyncMock(return_value=(existing[1],)),
    )
    mock_config_entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_NFC_PUBLIC_ORIGIN: "",
            CONF_NUKI_ENABLED: True,
            CONF_NUKI_LOCK_ENTITY_ID: "lock.front_door",
            CONF_NUKI_BLE_ADDRESS: address,
            CONF_NUKI_SECURITY_PIN: "123456",
        },
    )

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"nuki_delete_authorizations": ["17"]}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "nuki_confirm_delete"
    assert result["description_placeholders"] == {"pins": "Remove me — enabled — Nuki ID 17"}
    remove.assert_not_awaited()

    result = await hass.config_entries.options.async_configure(result["flow_id"], {})

    assert result["type"] is FlowResultType.CREATE_ENTRY
    remove.assert_awaited_once_with("17")


async def test_existing_pin_review_excludes_homepass_managed_authorizations(
    hass: HomeAssistant,
) -> None:
    """A PIN already owned by HomePASS can never be offered for bulk deletion."""
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_INSTANCE_NAME: NAME})
    entry.runtime_data = SimpleNamespace(
        access_metadata_service=SimpleNamespace(
            list_all=AsyncMock(
                return_value=(
                    SimpleNamespace(
                        driver=AccessDriver.NUKI,
                        lock_entity_id="lock.front_door",
                        slot=17,
                    ),
                )
            )
        )
    )
    provider = AsyncMock()
    provider.list_authorizations.return_value = (
        AuthorizationRecord("17", "Managed user", True),
        AuthorizationRecord("18", "Existing guest", True),
    )
    flow = HomePassOptionsFlow(entry)
    flow.hass = hass

    records = await flow._list_unmanaged_nuki_authorizations(provider, "lock.front_door")

    assert tuple(record.external_id for record in records) == ("18",)


async def test_existing_pin_review_retries_transient_bluetooth_read_failures(
    hass: HomeAssistant,
    monkeypatch,
) -> None:
    """A brief Bluetooth collision does not hide the existing-PIN review."""
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_INSTANCE_NAME: NAME})
    provider = AsyncMock()
    provider.list_authorizations.side_effect = (
        ProviderCommunicationError("temporary Bluetooth contention"),
        ProviderCommunicationError("temporary Bluetooth contention"),
        (AuthorizationRecord("17", "Existing guest", True),),
    )
    retry_delay = AsyncMock()
    monkeypatch.setattr("custom_components.homepass.config_flow.asyncio.sleep", retry_delay)
    flow = HomePassOptionsFlow(entry)
    flow.hass = hass

    records = await flow._list_unmanaged_nuki_authorizations(provider, "lock.front_door")

    assert tuple(record.external_id for record in records) == ("17",)
    assert provider.list_authorizations.await_count == 3
    assert retry_delay.await_count == 2


async def test_options_flow_requires_complete_nuki_configuration(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    monkeypatch,
) -> None:
    """Partial Nuki settings cannot activate a broken provider."""
    mock_config_entry.add_to_hass(hass)
    monkeypatch.setattr(
        HomePassOptionsFlow,
        "_discovered_nuki_locks",
        lambda self, current: {},
    )
    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_NFC_PUBLIC_ORIGIN: "",
            CONF_NUKI_ENABLED: True,
            CONF_NUKI_BLE_ADDRESS: "",
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {
        CONF_NUKI_LOCK_ENTITY_ID: "invalid_nuki_lock_entity",
        CONF_NUKI_BLE_ADDRESS: "nuki_not_discovered",
        CONF_NUKI_SECURITY_PIN: "invalid_nuki_security_pin",
    }
