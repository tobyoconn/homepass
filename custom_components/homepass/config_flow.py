"""Config flow for HomePASS."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.components import bluetooth
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_INSTANCE_NAME,
    CONF_NFC_PUBLIC_ORIGIN,
    CONF_NUKI_BLE_ADDRESS,
    CONF_NUKI_BLE_CREDENTIAL_ID,
    CONF_NUKI_ENABLED,
    CONF_NUKI_LOCK_ENTITY_ID,
    CONF_NUKI_SECURITY_PIN,
    DEFAULT_INSTANCE_NAME,
    DOMAIN,
)
from .models import AccessDriver
from .nfc.webauthn_service import normalize_public_origin
from .providers.base import (
    AuthorizationMutationState,
    AuthorizationRecord,
    ProviderCommunicationError,
)
from .providers.nuki_bluetooth import (
    NukiBluetoothCredential,
    NukiBluetoothOperationError,
    NukiBluetoothPairer,
    NukiBluetoothPairingError,
    NukiBluetoothTransport,
)
from .providers.nuki_local import NukiLocalAuthorizationProvider
from .vault.api import CredentialVault
from .vault.errors import VaultError
from .vault.identifiers import VaultCredentialId

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry, ConfigFlowResult

_CONFIG_SCHEMA = vol.Schema(
    {vol.Required(CONF_INSTANCE_NAME, default=DEFAULT_INSTANCE_NAME): str}
)

_CONF_NUKI_DELETE_AUTHORIZATIONS = "nuki_delete_authorizations"
_CONF_NUKI_DELETE_ALL_AUTHORIZATIONS = "nuki_delete_all_authorizations"
_NUKI_AUTHORIZATION_SCAN_ATTEMPTS = 3
_NUKI_AUTHORIZATION_SCAN_RETRY_DELAY = 2.0
_NUKI_AUTHORIZATION_SCAN_TIMEOUT = 40.0
_LOGGER = logging.getLogger(__name__)
_NUKI_PAIRING_GUIDANCE = {
    "nuki_pairing_not_enabled": (
        "Pairing stage: the lock is reachable but is not accepting a new app "
        "authorization. Hold its button for about six seconds until the light stays on, "
        "then submit while the light is still on."
    ),
    "nuki_pairing_bad_pin": (
        "Authorization stage: the lock rejected its Security PIN. Use the six-digit "
        "Security PIN from the Nuki lock settings, not a keypad access PIN."
    ),
    "nuki_pairing_authorization_full": (
        "Authorization stage: the lock has no free app authorization slots. Remove an "
        "obsolete app authorization in the Nuki app before trying again."
    ),
    "nuki_pairing_protocol_failed": (
        "Secure exchange stage: the lock responded but rejected the pairing protocol. "
        "Restart the lock, confirm its firmware is current, and try pairing again."
    ),
    "nuki_pairing_timeout": (
        "Secure exchange stage: the lock connected but did not finish pairing in time. "
        "Close the Nuki app nearby, put the lock back in pairing mode, and try again."
    ),
    "nuki_pairing_connection_failed": (
        "Connection stage: HomePASS can see the Nuki advertisement but could not open "
        "a Bluetooth connection. Close the Nuki app nearby and try again."
    ),
}


class HomePassConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Configure HomePASS."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> HomePassOptionsFlow:
        """Return the HomePASS options flow."""
        return HomePassOptionsFlow(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle initial setup."""
        if user_input is not None:
            name = user_input[CONF_INSTANCE_NAME].strip()
            if name:
                return self.async_create_entry(
                    title=name,
                    data={CONF_INSTANCE_NAME: name},
                )

            return self.async_show_form(
                step_id="user",
                data_schema=_CONFIG_SCHEMA,
                errors={CONF_INSTANCE_NAME: "invalid_instance_name"},
            )

        return self.async_show_form(
            step_id="user",
            data_schema=_CONFIG_SCHEMA,
        )


class HomePassOptionsFlow(config_entries.OptionsFlow):
    """Configure origin-bound NFC/passkey access."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        self._config_entry = config_entry
        self._pending_options: dict[str, Any] | None = None
        self._pending_nuki_provider: NukiLocalAuthorizationProvider | None = None
        self._pending_nuki_authorizations: tuple[AuthorizationRecord, ...] = ()
        self._pending_nuki_initial_pairing = False
        self._pending_nuki_delete_authorizations: set[str] = set()

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Configure the fixed public HTTPS origin used by NFC passkeys."""
        errors: dict[str, str] = {}
        pairing_guidance = ""
        current = str(self._config_entry.options.get(CONF_NFC_PUBLIC_ORIGIN, ""))
        current_nuki_enabled = bool(
            self._config_entry.options.get(CONF_NUKI_ENABLED, False)
        )
        current_nuki_entity = str(
            self._config_entry.options.get(CONF_NUKI_LOCK_ENTITY_ID, "")
        )
        current_nuki_address = str(
            self._config_entry.options.get(CONF_NUKI_BLE_ADDRESS, "")
        )
        current_credential_id = str(
            self._config_entry.options.get(CONF_NUKI_BLE_CREDENTIAL_ID, "")
        )
        if current_credential_id and current_nuki_address:
            pairing_guidance = (
                "Existing HomePASS Bluetooth authorization found. HomePASS will reuse it; "
                "no Security PIN or new pairing is required."
            )
        discovered_nuki = self._discovered_nuki_locks(current_nuki_address)
        if user_input is not None:
            raw_origin = str(user_input.get(CONF_NFC_PUBLIC_ORIGIN, "")).strip()
            if raw_origin:
                try:
                    raw_origin = normalize_public_origin(raw_origin)
                except ValueError:
                    errors[CONF_NFC_PUBLIC_ORIGIN] = "invalid_nfc_public_origin"
            nuki_enabled = bool(user_input.get(CONF_NUKI_ENABLED, False))
            nuki_entity = str(user_input.get(CONF_NUKI_LOCK_ENTITY_ID, "")).strip()
            nuki_address = str(user_input.get(CONF_NUKI_BLE_ADDRESS, "")).strip()
            security_pin = str(user_input.get(CONF_NUKI_SECURITY_PIN, "")).strip()
            credential_id = current_credential_id
            if nuki_enabled:
                if not nuki_entity.startswith("lock."):
                    errors[CONF_NUKI_LOCK_ENTITY_ID] = "invalid_nuki_lock_entity"
                if nuki_address not in discovered_nuki:
                    errors[CONF_NUKI_BLE_ADDRESS] = "nuki_not_discovered"
                reuse_pairing = bool(
                    credential_id
                    and current_nuki_address == nuki_address
                )
                if not reuse_pairing and (
                    len(security_pin) != 6 or not security_pin.isdecimal()
                ):
                    errors[CONF_NUKI_SECURITY_PIN] = "invalid_nuki_security_pin"
                if not errors and not reuse_pairing:
                    try:
                        vault = CredentialVault(self.hass)
                        await vault.initialize()
                        credential = await NukiBluetoothPairer(self.hass).pair(
                            nuki_address, security_pin
                        )
                        credential_id = str(await vault.store(credential.serialize()))
                    except NukiBluetoothPairingError as err:
                        _LOGGER.warning(
                            "Nuki pairing setup stopped: stage=%s, failure=%s",
                            err.stage,
                            err.translation_key,
                        )
                        if err.translation_key == "nuki_pairing_bad_pin":
                            errors[CONF_NUKI_SECURITY_PIN] = (
                                "invalid_nuki_security_pin"
                            )
                        else:
                            errors["base"] = "nuki_pairing_failed"
                        pairing_guidance = _NUKI_PAIRING_GUIDANCE.get(
                            err.translation_key,
                            "Pairing stopped before HomePASS could save a lock authorization.",
                        )
                    except ProviderCommunicationError as err:
                        _LOGGER.warning(
                            "Nuki pairing setup communication failure: error_type=%s",
                            type(err).__name__,
                        )
                        errors["base"] = "nuki_pairing_failed"
                        pairing_guidance = (
                            "Connection stage: HomePASS could not complete Bluetooth "
                            "communication with the selected lock."
                        )
                    except VaultError:
                        errors["base"] = "nuki_vault_unavailable"
                    except Exception as err:
                        # Keep unexpected dependency/runtime failures inside the
                        # options flow. Logging only the exception type avoids
                        # exposing pairing material that an upstream exception
                        # might embed in its message or representation.
                        _LOGGER.warning(
                            "Unexpected Nuki pairing setup failure: error_type=%s",
                            type(err).__name__,
                        )
                        errors["base"] = "nuki_pairing_failed"
                        pairing_guidance = (
                            "Pairing stage: an unexpected Bluetooth runtime failure occurred "
                            "before HomePASS could save the authorization."
                        )
                elif not errors:
                    try:
                        vault = CredentialVault(self.hass)
                        await vault.initialize()
                        credential = NukiBluetoothCredential.deserialize(
                            await vault.retrieve(
                                VaultCredentialId.from_string(credential_id)
                            )
                        )
                    except (ValueError, VaultError):
                        errors["base"] = "nuki_vault_unavailable"
                if not errors:
                    provider = NukiLocalAuthorizationProvider(
                        NukiBluetoothTransport(self.hass, nuki_address, credential)
                    )
                    try:
                        async with asyncio.timeout(_NUKI_AUTHORIZATION_SCAN_TIMEOUT):
                            existing = await self._list_unmanaged_nuki_authorizations(
                                provider, nuki_entity, attempts=1
                            )
                    except TimeoutError:
                        errors["base"] = "nuki_pairing_failed"
                        pairing_guidance = (
                            "Existing authorization check—overall timeout: HomePASS found the "
                            "stored authorization, but Bluetooth did not finish the connection "
                            "and keypad-data check within 40 seconds."
                        )
                    except ProviderCommunicationError as err:
                        errors["base"] = "nuki_pairing_failed"
                        pairing_guidance = self._nuki_scan_guidance(err)
                    except Exception as err:
                        _LOGGER.warning(
                            "Unexpected Nuki authorization scan failure: error_type=%s",
                            type(err).__name__,
                        )
                        errors["base"] = "nuki_authorization_scan_failed"
                        pairing_guidance = (
                            "Existing authorization check—unexpected runtime failure: "
                            f"HomePASS stopped safely at {type(err).__name__}."
                        )
                    else:
                        if existing:
                            self._pending_options = {
                                CONF_NFC_PUBLIC_ORIGIN: raw_origin,
                                CONF_NUKI_ENABLED: True,
                                CONF_NUKI_LOCK_ENTITY_ID: nuki_entity,
                                CONF_NUKI_BLE_ADDRESS: nuki_address,
                                CONF_NUKI_BLE_CREDENTIAL_ID: credential_id,
                            }
                            self._pending_nuki_provider = provider
                            self._pending_nuki_authorizations = existing
                            self._pending_nuki_initial_pairing = not reuse_pairing
                            return await self.async_step_nuki_existing_pins()
            if not errors:
                return self.async_create_entry(
                    title="",
                    data={
                        CONF_NFC_PUBLIC_ORIGIN: raw_origin,
                        CONF_NUKI_ENABLED: nuki_enabled,
                        CONF_NUKI_LOCK_ENTITY_ID: nuki_entity,
                        CONF_NUKI_BLE_ADDRESS: nuki_address,
                        CONF_NUKI_BLE_CREDENTIAL_ID: credential_id,
                    },
                )
            current = raw_origin
            current_nuki_enabled = nuki_enabled
            current_nuki_entity = nuki_entity
            current_nuki_address = nuki_address
        nuki_entity_key = (
            vol.Optional(
                CONF_NUKI_LOCK_ENTITY_ID,
                default=current_nuki_entity,
            )
            if current_nuki_entity
            else vol.Optional(CONF_NUKI_LOCK_ENTITY_ID)
        )
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_NFC_PUBLIC_ORIGIN, default=current
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.URL,
                            autocomplete="url",
                        )
                    ),
                    vol.Required(
                        CONF_NUKI_ENABLED, default=current_nuki_enabled
                    ): selector.BooleanSelector(),
                    nuki_entity_key: selector.EntitySelector(
                        selector.EntitySelectorConfig(domain="lock")
                    ),
                    vol.Optional(
                        CONF_NUKI_BLE_ADDRESS,
                        default=current_nuki_address,
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=(
                                [
                                    selector.SelectOptionDict(
                                        value=address, label=label
                                    )
                                    for address, label in discovered_nuki.items()
                                ]
                                or [
                                    selector.SelectOptionDict(
                                        value="", label="No nearby Nuki lock detected"
                                    )
                                ]
                            ),
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    ),
                    vol.Optional(CONF_NUKI_SECURITY_PIN): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.PASSWORD,
                            autocomplete="new-password",
                        )
                    ),
                }
            ),
            errors=errors,
            description_placeholders={"diagnostic": pairing_guidance},
        )

    async def async_step_nuki_existing_pins(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Keep existing Nuki PINs by default and delete only explicit selections."""
        if self._pending_options is None or self._pending_nuki_provider is None:
            return await self.async_step_init()

        errors: dict[str, str] = {}
        known_ids = {
            record.external_id for record in self._pending_nuki_authorizations
        }
        if user_input is not None:
            delete_all = self._pending_nuki_initial_pairing and bool(
                user_input.get(_CONF_NUKI_DELETE_ALL_AUTHORIZATIONS, False)
            )
            selected = (
                known_ids
                if delete_all
                else {
                    str(value)
                    for value in user_input.get(
                        _CONF_NUKI_DELETE_AUTHORIZATIONS, []
                    )
                }
            )
            if not selected.issubset(known_ids):
                errors["base"] = "nuki_authorization_selection_invalid"
            elif selected:
                self._pending_nuki_delete_authorizations = selected
                return await self.async_step_nuki_confirm_delete()
            else:
                return self.async_create_entry(title="", data=self._pending_options)

        options = [
            selector.SelectOptionDict(
                value=record.external_id,
                label=self._nuki_authorization_label(record),
            )
            for record in self._pending_nuki_authorizations
        ]
        schema: dict[vol.Marker, object] = {}
        if self._pending_nuki_initial_pairing:
            schema[
                vol.Optional(_CONF_NUKI_DELETE_ALL_AUTHORIZATIONS, default=False)
            ] = selector.BooleanSelector()
        schema[
            vol.Optional(_CONF_NUKI_DELETE_AUTHORIZATIONS, default=[])
        ] = selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=options,
                multiple=True,
                mode=selector.SelectSelectorMode.LIST,
            )
        )
        return self.async_show_form(
            step_id="nuki_existing_pins",
            data_schema=vol.Schema(schema),
            errors=errors,
        )

    async def async_step_nuki_confirm_delete(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Require a separate confirmation before permanently deleting Nuki PINs."""
        if self._pending_options is None or self._pending_nuki_provider is None:
            return await self.async_step_init()

        selected = self._pending_nuki_delete_authorizations
        known = {
            record.external_id: record for record in self._pending_nuki_authorizations
        }
        if not selected or not selected.issubset(known):
            return await self.async_step_nuki_existing_pins()

        errors: dict[str, str] = {}
        if user_input is not None:
            for external_id in sorted(selected, key=int):
                mutation = await self._pending_nuki_provider.delete_authorization(
                    external_id
                )
                if mutation.state is AuthorizationMutationState.FAILED:
                    errors["base"] = "nuki_authorization_delete_failed"
                    break
            if not errors:
                try:
                    remaining = await self._pending_nuki_provider.list_authorizations()
                except ProviderCommunicationError:
                    errors["base"] = "nuki_authorization_delete_unconfirmed"
                else:
                    remaining_ids = {record.external_id for record in remaining}
                    if selected & remaining_ids:
                        errors["base"] = "nuki_authorization_delete_unconfirmed"
            if not errors:
                return self.async_create_entry(title="", data=self._pending_options)

        labels = "; ".join(
            self._nuki_authorization_label(known[external_id])
            for external_id in sorted(selected, key=int)
        )
        return self.async_show_form(
            step_id="nuki_confirm_delete",
            data_schema=vol.Schema({}),
            errors=errors,
            description_placeholders={"pins": labels},
        )

    async def _list_unmanaged_nuki_authorizations(
        self,
        provider: NukiLocalAuthorizationProvider,
        lock_entity_id: str,
        *,
        attempts: int = _NUKI_AUTHORIZATION_SCAN_ATTEMPTS,
    ) -> tuple[AuthorizationRecord, ...]:
        """Return provider codes that HomePASS does not already own."""
        managed_ids: set[str] = set()
        runtime = getattr(self._config_entry, "runtime_data", None)
        if runtime is not None:
            metadata = await runtime.access_metadata_service.list_all()
            managed_ids = {
                str(record.slot)
                for record in metadata
                if record.driver is AccessDriver.NUKI
                and record.lock_entity_id == lock_entity_id
            }
        for attempt in range(attempts):
            try:
                authorizations = await provider.list_authorizations()
            except ProviderCommunicationError:
                if attempt + 1 == attempts:
                    raise
                await asyncio.sleep(_NUKI_AUTHORIZATION_SCAN_RETRY_DELAY)
            else:
                return tuple(
                    record
                    for record in authorizations
                    if record.external_id not in managed_ids
                )
        raise AssertionError("Nuki authorization scan retry loop did not terminate")

    @staticmethod
    def _nuki_authorization_label(record: AuthorizationRecord) -> str:
        """Return a secret-free review label for one existing keypad code."""
        state = "enabled" if record.enabled else "disabled"
        return f"{record.display_name} — {state} — Nuki ID {record.external_id}"

    @staticmethod
    def _nuki_scan_guidance(err: ProviderCommunicationError) -> str:
        """Return safe on-screen guidance for an existing pairing check."""
        if isinstance(err, NukiBluetoothOperationError):
            if err.stage == "discovery":
                return (
                    "Existing authorization check—discovery stage: the Nuki advertisement "
                    "was visible earlier, but no connectable device was available when "
                    "HomePASS tried to use it."
                )
            if err.stage == "connection":
                return (
                    "Existing authorization check—connection stage: HomePASS found the lock "
                    "but could not open the Bluetooth connection. Close the Nuki app nearby "
                    "and try again."
                )
            if err.stage == "device identification":
                return (
                    "Existing authorization check—identification stage: the Bluetooth device "
                    "did not expose the expected Nuki Ultra services."
                )
            return (
                "Existing authorization check—authenticated command stage: HomePASS connected "
                "but the lock did not accept or complete the keypad-data request."
            )
        return (
            "Existing authorization check—communication stage: HomePASS could not complete "
            "the keypad-data request using the stored authorization."
        )

    def _discovered_nuki_locks(self, current_address: str) -> dict[str, str]:
        """Return connectable Nuki locks without exposing unrelated BLE devices."""
        locks: dict[str, str] = {}
        for info in bluetooth.async_discovered_service_info(
            self.hass, connectable=True
        ):
            name = (info.name or info.address).strip()
            service_uuids = {value.lower() for value in info.service_uuids}
            if "nuki" not in name.lower() and (
                "a92ee300-5501-11e4-916c-0800200c9a66" not in service_uuids
            ):
                continue
            address = info.address.strip().upper()
            locks[address] = f"{name} — {address}"
        if current_address and current_address not in locks:
            locks[current_address] = f"Previously paired Nuki — {current_address}"
        return dict(sorted(locks.items(), key=lambda item: item[1].casefold()))
