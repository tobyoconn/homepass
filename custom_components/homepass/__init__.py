"""HomePASS integration."""

from __future__ import annotations

import logging
from uuid import UUID

import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall, callback

from .about_actions import async_register_about_action, async_unregister_about_action
from .access_device_actions import (
    async_register_access_device_actions,
    async_unregister_access_device_actions,
)
from .access_device_discovery import HomeAssistantAccessDeviceDiscovery
from .access_management_actions import (
    async_register_access_management_actions,
    async_unregister_access_management_actions,
)
from .access_point_actions import (
    async_register_access_point_actions,
    async_unregister_access_point_actions,
)
from .access_point_discovery import HomeAssistantAccessPointDiscovery
from .access_point_naming import HomeAssistantAccessPointNameResolver
from .access_point_state import HomeAssistantAccessPointStateResolver
from .actions import async_register_person_actions, async_unregister_person_actions
from .activity_actions import async_register_activity_actions, async_unregister_activity_actions
from .const import (
    CONF_NFC_PUBLIC_ORIGIN,
    CONF_NUKI_BLE_ADDRESS,
    CONF_NUKI_BLE_CREDENTIAL_ID,
    CONF_NUKI_ENABLED,
    CONF_NUKI_LOCK_ENTITY_ID,
    DOMAIN,
    SERVICE_PING,
)
from .credential_replacement_websocket import (
    async_register_credential_replacement_websocket,
    async_unregister_credential_replacement_websocket,
)
from .dashboard_attention_actions import (
    async_register_dashboard_attention_actions,
    async_unregister_dashboard_attention_actions,
)
from .drivers import (
    AccessCredentialDriverRouter,
    HomeAssistantZWaveLockDriver,
    HomePassKeypadCredentialDriver,
)
from .give_access_actions import (
    async_register_give_access_actions,
    async_unregister_give_access_actions,
)
from .lifecycle import LifecycleOperationManager
from .models import AccessDriver, LifecycleOperation
from .nfc.access import NfcAccessService
from .nfc.actions import async_register_nfc_actions, async_unregister_nfc_actions
from .nfc.repository import NfcAccessRepository
from .nfc.views import async_register_nfc_views, async_unregister_nfc_views
from .nfc.webauthn_service import HomePassWebAuthnService
from .notification_discovery import HomeAssistantNotificationDeviceDiscovery
from .nuki_fingerprint_actions import (
    async_register_nuki_fingerprint_actions,
    async_unregister_nuki_fingerprint_actions,
)
from .nuki_storage_actions import (
    async_register_nuki_storage_action,
    async_unregister_nuki_storage_action,
)
from .panel import async_register_homepass_panel, async_unregister_homepass_panel
from .person_schedule_actions import (
    async_register_person_schedule_actions,
    async_unregister_person_schedule_actions,
)
from .policy_explanation_actions import (
    async_register_policy_explanation_actions,
    async_unregister_policy_explanation_actions,
)
from .providers import AuthorizationProviderRegistry
from .providers.nuki_bluetooth import NukiBluetoothCredential, NukiBluetoothTransport
from .providers.nuki_credential import NukiNumberedCredentialDriver
from .providers.nuki_local import NukiLocalAuthorizationProvider
from .repositories import CredentialMetadataRepository
from .repositories.access_device import AccessDeviceRepository
from .repositories.access_grant import AccessGrantRepository
from .repositories.access_metadata import AccessMetadataRepository
from .repositories.access_point import AccessPointRepository
from .repositories.access_point_enrollment import AccessPointEnrollmentRepository
from .repositories.activity import ActivityRepository
from .repositories.lifecycle_operation import LifecycleOperationRepository
from .repositories.notification_preferences import NotificationPreferencesRepository
from .repositories.person import PersonRepository
from .repositories.property_settings import PropertySettingsRepository
from .repositories.schedule import ScheduleRepository
from .repositories.synchronization_history import SynchronizationHistoryRepository
from .repositories.synchronization_status import SynchronizationStatusRepository
from .reveal import CredentialRevealService, RevealAuditRepository
from .reveal_websocket import (
    async_register_reveal_websocket,
    async_unregister_reveal_websocket,
)
from .runtime_data import HomePassConfigEntry, HomePassRuntimeData
from .schedule_actions import (
    async_register_schedule_actions,
    async_unregister_schedule_actions,
)
from .services import (
    AboutService,
    AccessDeviceService,
    AccessManagementService,
    AccessMetadataService,
    AccessPointCommandService,
    AccessPointService,
    ActivityKeypadAttributionService,
    ActivityProducer,
    ActivityPublisher,
    ActivityReadService,
    ActivityService,
    AuthorizationService,
    BatteryMonitoringService,
    CredentialReplacementLifecycleService,
    DashboardAttentionService,
    DoorDetailsService,
    GiveAccessService,
    HomeAssistantCompanionNotificationChannel,
    KeypadCommandProcessor,
    LockCommandCorrelationService,
    NotificationEngine,
    NotificationPreferencesService,
    NukiFingerprintService,
    PersonCardService,
    PersonDeletionService,
    PersonPolicyDetailsService,
    PersonScheduleService,
    PersonService,
    PhysicalActivityIngestionService,
    PolicyExplanationService,
    PropertySettingsService,
    ScheduleService,
    SynchronizationHistoryService,
    SynchronizationRecoveryService,
    SynchronizationStatusService,
    UserSetupService,
    ZhaKeypadService,
    Zigbee2MqttKeypadService,
    ZWavePinSyncService,
    developer_git_commit,
)
from .services.credential_replacement import CredentialReplacementDriver
from .services.nuki_audit_ingestion import NukiAuditIngestionService
from .services.person_deletion import CredentialRemovalDriver
from .settings_actions import (
    async_register_settings_actions,
    async_unregister_settings_actions,
)
from .storage import HomePassStorageManager
from .synchronization_recovery_actions import (
    async_register_synchronization_recovery_action,
    async_unregister_synchronization_recovery_action,
)
from .user_setup_actions import (
    async_register_user_setup_actions,
    async_unregister_user_setup_actions,
)
from .vault.api import CredentialVault
from .vault.errors import VaultError
from .vault.identifiers import VaultCredentialId
from .vault_crypto_actions import (
    async_register_vault_crypto_spike_action,
    async_unregister_vault_crypto_spike_action,
)
from .zwave_actions import (
    async_register_zwave_spike_actions,
    async_unregister_zwave_spike_actions,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: HomePassConfigEntry) -> bool:
    """Set up HomePASS from a config entry."""
    _LOGGER.debug("Setting up HomePASS config entry %s", entry.entry_id)
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    storage = HomePassStorageManager(hass)
    credential_vault = CredentialVault(hass)
    await credential_vault.initialize()
    authorization_provider_registry = AuthorizationProviderRegistry()
    nuki_enabled = bool(entry.options.get(CONF_NUKI_ENABLED, False))
    nuki_lock_entity_id = str(entry.options.get(CONF_NUKI_LOCK_ENTITY_ID, "")).strip()
    nuki_authorization_provider: NukiLocalAuthorizationProvider | None = None
    nuki_transport: NukiBluetoothTransport | None = None
    if nuki_enabled:
        nuki_address = str(entry.options.get(CONF_NUKI_BLE_ADDRESS, "")).strip()
        credential_id = str(entry.options.get(CONF_NUKI_BLE_CREDENTIAL_ID, "")).strip()
        try:
            pairing_material = await credential_vault.retrieve(
                VaultCredentialId.from_string(credential_id)
            )
            nuki_transport = NukiBluetoothTransport(
                hass,
                nuki_address,
                NukiBluetoothCredential.deserialize(pairing_material),
            )
            nuki_authorization_provider = NukiLocalAuthorizationProvider(nuki_transport)
            authorization_provider_registry.register(
                AccessDriver.NUKI.value, nuki_authorization_provider
            )
        except ValueError, VaultError:
            _LOGGER.error(
                "Nuki local access is enabled but its encrypted pairing is unavailable; "
                "re-pair Nuki in HomePASS integration options"
            )
    nfc_repository = NfcAccessRepository(hass)
    activity_repository = ActivityRepository(storage)
    notification_preferences_service = NotificationPreferencesService(
        NotificationPreferencesRepository(storage),
        HomeAssistantNotificationDeviceDiscovery(hass),
    )
    await notification_preferences_service.initialize()
    property_settings_service = PropertySettingsService(
        PropertySettingsRepository(storage),
    )
    about_service = AboutService(
        property_settings_service,
        git_commit=developer_git_commit(),
    )
    notification_engine = NotificationEngine(
        notification_preferences_service,
        HomeAssistantCompanionNotificationChannel(hass),
    )
    activity_publisher = ActivityPublisher((notification_engine.activity_recorded,))
    activity_service = ActivityService(activity_repository, activity_publisher)
    activity_producer = ActivityProducer(activity_service)
    activity_read_service = ActivityReadService(activity_repository)
    credential_metadata_repository = CredentialMetadataRepository(storage)
    access_grant_repository = AccessGrantRepository(storage)
    access_device_repository = AccessDeviceRepository(storage)
    access_point_repository = AccessPointRepository(storage)
    access_metadata_repository = AccessMetadataRepository(storage)
    synchronization_status_repository = SynchronizationStatusRepository(storage)
    synchronization_status_service = SynchronizationStatusService(
        storage,
        synchronization_status_repository,
        access_metadata_repository,
    )
    synchronization_history_service = SynchronizationHistoryService(
        SynchronizationHistoryRepository(storage)
    )

    async def before_remove_access_point(access_point_id: UUID) -> None:
        await nfc_repository.disable_tags_for_access_point(access_point_id)
        await access_device_repository.remove_for_access_point(access_point_id)

    access_point_service = AccessPointService(
        name_resolver=HomeAssistantAccessPointNameResolver(hass),
        state_resolver=HomeAssistantAccessPointStateResolver(
            hass,
            nuki_entity_id=nuki_lock_entity_id,
            nuki_entry_recommendation=(
                nuki_transport.entry_recommendation if nuki_transport else None
            ),
        ),
        target_discovery=HomeAssistantAccessPointDiscovery(
            hass,
            nuki_authorization_entity_id=(
                nuki_lock_entity_id if nuki_authorization_provider is not None else None
            ),
        ),
        enrollment_store=AccessPointEnrollmentRepository(storage),
        policy_store=access_point_repository,
        grant_lookup=access_grant_repository,
        activity_producer=activity_producer,
        before_remove=before_remove_access_point,
    )
    access_device_service = AccessDeviceService(
        access_device_repository,
        HomeAssistantAccessDeviceDiscovery(hass),
        access_point_service,
    )
    battery_monitoring_service = BatteryMonitoringService(
        hass,
        access_point_service,
        access_device_service,
        activity_service,
    )
    lock_command_correlation_service = LockCommandCorrelationService()
    access_point_command_service = AccessPointCommandService(
        hass,
        access_point_service,
        lock_command_correlation_service,
    )
    activity_attribution_service = ActivityKeypadAttributionService(storage)
    physical_activity_ingestion_service = PhysicalActivityIngestionService(
        hass,
        access_point_service,
        activity_service,
        lock_command_correlation_service,
        activity_attribution_service,
    )
    nuki_fingerprint_service = NukiFingerprintService(
        storage, activity_service, activity_attribution_service
    )
    access_metadata_service = AccessMetadataService(
        access_metadata_repository,
        access_grant_repository,
        synchronization_status_service,
        synchronization_history_service,
        credential_metadata_repository,
    )
    authorization_service = AuthorizationService(storage, access_point_repository)
    dashboard_attention_service = DashboardAttentionService(
        storage,
        synchronization_status_service,
    )
    door_details_service = DoorDetailsService(
        authorization_service,
        synchronization_status_service,
        synchronization_history_service,
    )
    person_policy_details_service = PersonPolicyDetailsService(
        authorization_service,
        synchronization_status_service,
        synchronization_history_service,
    )
    policy_explanation_service = PolicyExplanationService(authorization_service)

    async def observe_lifecycle(operation: LifecycleOperation) -> None:
        await synchronization_status_service.lifecycle_changed(operation)
        await synchronization_history_service.lifecycle_changed(operation)

    lifecycle_manager = LifecycleOperationManager(
        LifecycleOperationRepository(storage),
        transition_observer=observe_lifecycle,
    )
    person_schedule_service = PersonScheduleService(storage, activity_producer)
    schedule_service = ScheduleService(ScheduleRepository(storage), activity_producer)
    zwave_driver = HomeAssistantZWaveLockDriver(hass)
    credential_driver = AccessCredentialDriverRouter(zwave_driver)
    nuki_credential_driver: NukiNumberedCredentialDriver | None = None
    if nuki_authorization_provider is not None:
        nuki_credential_driver = NukiNumberedCredentialDriver(
            nuki_authorization_provider,
            nuki_lock_entity_id,
        )
        credential_driver.register(nuki_lock_entity_id, nuki_credential_driver)
    keypad_credential_driver = HomePassKeypadCredentialDriver()

    def credential_replacement_driver(
        driver: AccessDriver,
    ) -> CredentialReplacementDriver | None:
        if driver is AccessDriver.ZWAVE_JS:
            return zwave_driver
        if driver is AccessDriver.NUKI:
            return nuki_credential_driver
        if driver is AccessDriver.HOMEPASS_KEYPAD:
            return keypad_credential_driver
        return None

    def credential_removal_driver(driver: AccessDriver) -> CredentialRemovalDriver | None:
        if driver is AccessDriver.ZWAVE_JS:
            return zwave_driver
        if driver is AccessDriver.NUKI:
            return nuki_credential_driver
        if driver is AccessDriver.HOMEPASS_KEYPAD:
            return keypad_credential_driver
        return None

    keypad_command_processor = KeypadCommandProcessor(
        access_device_service,
        credential_metadata_repository,
        credential_vault,
        authorization_service,
        access_point_service,
        access_point_command_service,
        activity_service,
    )
    zha_keypad_service = ZhaKeypadService(
        hass,
        access_device_repository,
        keypad_command_processor,
    )
    zigbee2mqtt_keypad_service = Zigbee2MqttKeypadService(
        hass,
        access_device_repository,
        keypad_command_processor,
    )
    access_device_service.set_change_listener(zigbee2mqtt_keypad_service.async_reconcile)
    await nfc_repository.initialize()
    person_deletion_service = PersonDeletionService(
        storage,
        lifecycle_manager,
        credential_removal_driver,
        synchronization_status_service,
        credential_vault,
        before_delete=nfc_repository.disable_credentials_for_person,
    )
    person_service = PersonService(
        PersonRepository(storage), person_deletion_service, activity_producer
    )
    person_card_service = PersonCardService(storage)
    zwave_pin_sync_service = ZWavePinSyncService(zwave_driver)
    give_access_service = GiveAccessService(
        person_service,
        access_point_service,
        credential_driver,
        access_metadata_service,
        credential_vault,
        synchronization_history_service,
        activity_producer,
        credential_metadata_repository,
        schedule_service,
    )
    access_management_service = AccessManagementService(
        person_service,
        access_point_service,
        credential_driver,
        access_metadata_service,
        credential_vault,
        synchronization_history_service,
        activity_producer,
        credential_metadata_repository,
        schedule_service,
        nuki_fingerprint_service.remove_access_link,
    )
    reveal_audit_repository = RevealAuditRepository(hass)
    await reveal_audit_repository.async_initialize()
    credential_reveal_service = CredentialRevealService(
        person_service,
        access_metadata_service,
        credential_vault,
        reveal_audit_repository,
        credential_metadata_repository=credential_metadata_repository,
    )
    user_setup_service = UserSetupService(
        storage,
        access_point_service,
        access_management_service,
        credential_vault,
        credential_metadata_repository,
        activity_producer,
    )
    credential_replacement_service = CredentialReplacementLifecycleService(
        storage,
        lifecycle_manager,
        credential_vault,
        credential_replacement_driver,
        credential_reveal_service.reset_rate_limit_after_replacement,
        synchronization_status_service,
        activity_producer,
    )
    synchronization_recovery_service = SynchronizationRecoveryService(
        storage,
        credential_vault,
        synchronization_status_service,
        access_management_service,
        credential_replacement_service,
        person_deletion_service,
        synchronization_history_service,
        activity_producer,
    )
    nuki_audit_ingestion_service = (
        NukiAuditIngestionService(
            hass,
            nuki_authorization_provider,
            nuki_lock_entity_id,
            access_point_service,
            physical_activity_ingestion_service,
            nuki_fingerprint_service,
        )
        if nuki_authorization_provider is not None
        else None
    )
    nfc_webauthn_service: HomePassWebAuthnService | None = None
    nfc_access_service: NfcAccessService | None = None
    nfc_public_origin = str(entry.options.get(CONF_NFC_PUBLIC_ORIGIN, "")).strip()
    if nfc_public_origin:
        nfc_webauthn_service = HomePassWebAuthnService(
            nfc_repository,
            public_origin=nfc_public_origin,
        )
        nfc_access_service = NfcAccessService(
            hass,
            nfc_repository,
            credential_vault,
            authorization_service,
            access_point_service,
            access_point_command_service,
            access_point_command_service,
        )
    entry.runtime_data = HomePassRuntimeData(
        storage=storage,
        activity_publisher=activity_publisher,
        activity_service=activity_service,
        activity_read_service=activity_read_service,
        lock_command_correlation_service=lock_command_correlation_service,
        about_service=about_service,
        notification_preferences_service=notification_preferences_service,
        notification_engine=notification_engine,
        nuki_fingerprint_service=nuki_fingerprint_service,
        nuki_audit_ingestion_service=nuki_audit_ingestion_service,
        property_settings_service=property_settings_service,
        physical_activity_ingestion_service=physical_activity_ingestion_service,
        battery_monitoring_service=battery_monitoring_service,
        access_metadata_service=access_metadata_service,
        access_management_service=access_management_service,
        access_device_service=access_device_service,
        access_point_service=access_point_service,
        access_point_command_service=access_point_command_service,
        authorization_service=authorization_service,
        dashboard_attention_service=dashboard_attention_service,
        door_details_service=door_details_service,
        give_access_service=give_access_service,
        person_service=person_service,
        person_card_service=person_card_service,
        person_policy_details_service=person_policy_details_service,
        person_schedule_service=person_schedule_service,
        policy_explanation_service=policy_explanation_service,
        schedule_service=schedule_service,
        synchronization_status_service=synchronization_status_service,
        synchronization_history_service=synchronization_history_service,
        synchronization_recovery_service=synchronization_recovery_service,
        user_setup_service=user_setup_service,
        zwave_pin_sync_service=zwave_pin_sync_service,
        keypad_command_processor=keypad_command_processor,
        zha_keypad_service=zha_keypad_service,
        zigbee2mqtt_keypad_service=zigbee2mqtt_keypad_service,
        credential_vault=credential_vault,
        credential_reveal_service=credential_reveal_service,
        credential_replacement_service=credential_replacement_service,
        authorization_provider_registry=authorization_provider_registry,
        nfc_repository=nfc_repository,
        nfc_webauthn_service=nfc_webauthn_service,
        nfc_access_service=nfc_access_service,
    )
    await synchronization_status_service.recompute_all()
    await access_management_service.async_resume_pending_verifications()

    @callback
    def handle_ping(_call: ServiceCall) -> None:
        """Handle a HomePASS ping service call."""
        _LOGGER.info("HomePASS ping service called")

    try:
        await _async_register_entry_surfaces(hass, entry, handle_ping)
        await access_device_service.reconcile_pin_capabilities()
        await battery_monitoring_service.async_start()
        await physical_activity_ingestion_service.async_start()
        if nuki_audit_ingestion_service is not None:
            await nuki_audit_ingestion_service.async_start()
        await zha_keypad_service.async_start()
        await zigbee2mqtt_keypad_service.async_start()
    except BaseException:
        await zigbee2mqtt_keypad_service.async_stop()
        await zha_keypad_service.async_stop()
        if nuki_audit_ingestion_service is not None:
            await nuki_audit_ingestion_service.async_stop()
        keypad_command_processor.reset()
        await physical_activity_ingestion_service.async_stop()
        await battery_monitoring_service.async_stop()
        await access_management_service.async_shutdown()
        _unregister_entry_surfaces(hass, entry)
        raise
    return True


async def async_unload_entry(hass: HomeAssistant, entry: HomePassConfigEntry) -> bool:
    """Unload a HomePASS config entry."""
    _LOGGER.debug("Unloading HomePASS config entry %s", entry.entry_id)
    await entry.runtime_data.zigbee2mqtt_keypad_service.async_stop()
    await entry.runtime_data.zha_keypad_service.async_stop()
    if entry.runtime_data.nuki_audit_ingestion_service is not None:
        await entry.runtime_data.nuki_audit_ingestion_service.async_stop()
    entry.runtime_data.keypad_command_processor.reset()
    await entry.runtime_data.physical_activity_ingestion_service.async_stop()
    await entry.runtime_data.battery_monitoring_service.async_stop()
    await entry.runtime_data.access_management_service.async_shutdown()
    _unregister_entry_surfaces(hass, entry)
    return True


async def _async_reload_entry(hass: HomeAssistant, entry: HomePassConfigEntry) -> None:
    """Reload HomePASS when origin-bound passkey options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def _async_register_entry_surfaces(
    hass: HomeAssistant,
    entry: HomePassConfigEntry,
    handle_ping: object,
) -> None:
    """Register every action and view before starting background listeners."""
    runtime = entry.runtime_data
    hass.services.async_register(DOMAIN, SERVICE_PING, handle_ping, schema=vol.Schema({}))
    async_register_access_point_actions(
        hass,
        runtime.access_point_service,
        runtime.door_details_service,
        runtime.access_point_command_service,
        runtime.nfc_repository,
        runtime.access_device_service,
    )
    async_register_access_device_actions(hass, runtime.access_device_service)
    async_register_about_action(hass, runtime.about_service)
    async_register_activity_actions(hass, runtime.activity_read_service)
    async_register_dashboard_attention_actions(hass, runtime.dashboard_attention_service)
    async_register_nuki_fingerprint_actions(hass, runtime.nuki_fingerprint_service)
    async_register_nuki_storage_action(
        hass,
        runtime.authorization_provider_registry.get(AccessDriver.NUKI.value),
        str(entry.options.get(CONF_NUKI_LOCK_ENTITY_ID, "")).strip(),
        runtime.access_metadata_service,
        runtime.nuki_fingerprint_service,
    )
    async_register_settings_actions(
        hass,
        runtime.notification_preferences_service,
        runtime.property_settings_service,
        entry,
    )
    async_register_access_management_actions(hass, runtime.access_management_service)
    async_register_give_access_actions(hass, runtime.give_access_service)
    async_register_person_actions(
        hass,
        runtime.person_service,
        runtime.access_metadata_service,
        runtime.access_point_service,
        runtime.person_schedule_service,
        runtime.credential_replacement_service,
        runtime.person_policy_details_service,
        runtime.person_card_service,
    )
    async_register_person_schedule_actions(hass, runtime.person_schedule_service)
    async_register_policy_explanation_actions(hass, runtime.policy_explanation_service)
    async_register_synchronization_recovery_action(hass, runtime.synchronization_recovery_service)
    async_register_user_setup_actions(hass, runtime.user_setup_service)
    async_register_schedule_actions(hass, runtime.schedule_service)
    async_register_zwave_spike_actions(hass, runtime.zwave_pin_sync_service)
    async_register_vault_crypto_spike_action(hass)
    async_register_reveal_websocket(hass, runtime.credential_reveal_service)
    async_register_credential_replacement_websocket(hass, runtime.credential_replacement_service)
    if (
        runtime.nfc_repository is not None
        and runtime.nfc_webauthn_service is not None
        and runtime.nfc_access_service is not None
    ):
        async_register_nfc_actions(
            hass,
            runtime.nfc_repository,
            runtime.nfc_webauthn_service,
            runtime.person_service,
            runtime.access_point_service,
            runtime.credential_vault,
            runtime.access_point_command_service,
        )
        await async_register_nfc_views(
            hass,
            runtime.nfc_access_service,
            runtime.nfc_webauthn_service,
            runtime.property_settings_service,
        )
    await async_register_homepass_panel(hass)


def _unregister_entry_surfaces(hass: HomeAssistant, entry: HomePassConfigEntry) -> None:
    """Best-effort remove surfaces after normal unload or partial setup."""
    if entry.runtime_data.nfc_access_service is not None:
        async_unregister_nfc_actions(hass)
        async_unregister_nfc_views(hass)
    hass.services.async_remove(DOMAIN, SERVICE_PING)
    async_unregister_about_action(hass)
    async_unregister_access_point_actions(hass)
    async_unregister_access_device_actions(hass)
    async_unregister_activity_actions(hass)
    async_unregister_dashboard_attention_actions(hass)
    async_unregister_nuki_fingerprint_actions(hass)
    async_unregister_nuki_storage_action(hass)
    async_unregister_settings_actions(hass)
    async_unregister_access_management_actions(hass)
    async_unregister_give_access_actions(hass)
    async_unregister_person_actions(hass)
    async_unregister_person_schedule_actions(hass)
    async_unregister_policy_explanation_actions(hass)
    async_unregister_synchronization_recovery_action(hass)
    async_unregister_user_setup_actions(hass)
    async_unregister_schedule_actions(hass)
    async_unregister_zwave_spike_actions(hass)
    async_unregister_vault_crypto_spike_action(hass)
    async_unregister_reveal_websocket(hass)
    async_unregister_credential_replacement_websocket(hass)
    async_unregister_homepass_panel(hass)
