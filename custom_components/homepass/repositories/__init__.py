"""Repository contracts for HomePASS."""

from .access_device import AccessDeviceRepository
from .access_grant import AccessGrantRepository
from .access_metadata import AccessMetadataRepository
from .access_point import AccessPointRepository
from .access_point_enrollment import AccessPointEnrollmentRepository
from .activity import ActivityAppendResult, ActivityRepository
from .base import Repository
from .credential_metadata import CredentialMetadataRepository
from .lifecycle_operation import LifecycleOperationRepository
from .notification_preferences import NotificationPreferencesRepository
from .property_settings import PropertySettingsRepository
from .schedule import ScheduleRepository
from .synchronization_history import SynchronizationHistoryRepository
from .synchronization_status import SynchronizationStatusRepository

__all__ = [
    "AccessGrantRepository",
    "AccessDeviceRepository",
    "AccessPointRepository",
    "AccessPointEnrollmentRepository",
    "AccessMetadataRepository",
    "CredentialMetadataRepository",
    "ActivityAppendResult",
    "ActivityRepository",
    "Repository",
    "LifecycleOperationRepository",
    "NotificationPreferencesRepository",
    "PropertySettingsRepository",
    "ScheduleRepository",
    "SynchronizationStatusRepository",
    "SynchronizationHistoryRepository",
]
