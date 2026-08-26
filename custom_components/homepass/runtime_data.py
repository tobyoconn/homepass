"""Runtime data types for HomePASS."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigEntry

from .reveal import CredentialRevealService
from .services import (
    AboutService,
    AccessDeviceService,
    AccessManagementService,
    AccessMetadataService,
    AccessPointCommandService,
    AccessPointService,
    ActivityPublisher,
    ActivityReadService,
    ActivityService,
    AuthorizationService,
    BatteryMonitoringService,
    CredentialReplacementLifecycleService,
    DashboardAttentionService,
    DoorDetailsService,
    GiveAccessService,
    KeypadCommandProcessor,
    LockCommandCorrelationService,
    NotificationEngine,
    NotificationPreferencesService,
    NukiFingerprintService,
    PersonCardService,
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
)
from .storage import HomePassStorageManager
from .vault import CredentialVaultProtocol

if TYPE_CHECKING:
    from .nfc.access import NfcAccessService
    from .nfc.repository import NfcAccessRepository
    from .nfc.webauthn_service import HomePassWebAuthnService
    from .providers import AuthorizationProviderRegistry
    from .services.nuki_audit_ingestion import NukiAuditIngestionService


@dataclass(slots=True)
class HomePassRuntimeData:
    """Runtime state attached to the config entry."""

    storage: HomePassStorageManager
    activity_publisher: ActivityPublisher
    activity_service: ActivityService
    activity_read_service: ActivityReadService
    lock_command_correlation_service: LockCommandCorrelationService
    about_service: AboutService
    notification_preferences_service: NotificationPreferencesService
    notification_engine: NotificationEngine
    nuki_fingerprint_service: NukiFingerprintService
    nuki_audit_ingestion_service: NukiAuditIngestionService | None
    property_settings_service: PropertySettingsService
    physical_activity_ingestion_service: PhysicalActivityIngestionService
    battery_monitoring_service: BatteryMonitoringService
    access_metadata_service: AccessMetadataService
    access_management_service: AccessManagementService
    access_device_service: AccessDeviceService
    access_point_service: AccessPointService
    access_point_command_service: AccessPointCommandService
    authorization_service: AuthorizationService
    dashboard_attention_service: DashboardAttentionService
    door_details_service: DoorDetailsService
    give_access_service: GiveAccessService
    person_service: PersonService
    person_card_service: PersonCardService
    person_policy_details_service: PersonPolicyDetailsService
    person_schedule_service: PersonScheduleService
    policy_explanation_service: PolicyExplanationService
    schedule_service: ScheduleService
    synchronization_status_service: SynchronizationStatusService
    synchronization_history_service: SynchronizationHistoryService
    synchronization_recovery_service: SynchronizationRecoveryService
    user_setup_service: UserSetupService
    zwave_pin_sync_service: ZWavePinSyncService
    keypad_command_processor: KeypadCommandProcessor
    zha_keypad_service: ZhaKeypadService
    zigbee2mqtt_keypad_service: Zigbee2MqttKeypadService
    credential_vault: CredentialVaultProtocol
    credential_reveal_service: CredentialRevealService
    credential_replacement_service: CredentialReplacementLifecycleService
    authorization_provider_registry: AuthorizationProviderRegistry
    nfc_repository: NfcAccessRepository | None = None
    nfc_webauthn_service: HomePassWebAuthnService | None = None
    nfc_access_service: NfcAccessService | None = None


HomePassConfigEntry = ConfigEntry[HomePassRuntimeData]

