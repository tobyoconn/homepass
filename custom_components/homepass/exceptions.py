"""Domain exceptions for HomePASS."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class HomePASSError(Exception):
    """Base exception for all HomePASS domain failures."""


class ValidationError(HomePASSError):
    """Raised when domain data fails validation."""


class CredentialAuthorityConflictError(ValidationError):
    """Raised when a Person's PIN authority cannot be resolved safely."""

    def __init__(self) -> None:
        super().__init__(
            "This User's PIN configuration needs attention before access can be changed"
        )


class CredentialSlotIntegrityError(ValidationError):
    """Raised when one Door slot cannot be assigned to exactly one User safely."""

    def __init__(self) -> None:
        super().__init__(
            "Credential slot ownership needs attention before synchronization can continue"
        )


class AuthorizationInvariantError(HomePASSError):
    """Raised when authorization inputs describe inconsistent domain relationships."""


class ActivityDuplicateConflictError(HomePASSError):
    """Raised when a stable Activity identity is reused for a different fact."""


class AccessPointNotFoundError(HomePASSError):
    """Raised when a requested policy Access Point is unknown."""

    def __init__(self) -> None:
        super().__init__("This access point is unavailable")


class AuthorizationContextError(HomePASSError):
    """Raised when a trustworthy authorization context cannot be assembled."""

    def __init__(self) -> None:
        super().__init__("Authorization context is unavailable")


class PolicyExplanationUnavailableError(HomePASSError):
    """Raised when a safe denied-policy explanation cannot be produced."""


class DuplicatePersonError(ValidationError):
    """Raised when a person conflicts with an existing person."""


class PersonNotFoundError(HomePASSError):
    """Raised when a requested person does not exist."""


class DuplicateScheduleError(ValidationError):
    """Raised when a schedule conflicts with an existing schedule."""


class ScheduleNotFoundError(HomePASSError):
    """Raised when a requested schedule does not exist."""


class ProtectedScheduleError(ValidationError):
    """Raised when an operation would modify a protected system schedule."""


@dataclass(frozen=True, slots=True)
class PersonScheduleSummary:
    """Safe homeowner-facing summary of one Schedule in a conflict."""

    name: str
    validity: str
    access_hours: str


class InvalidPersonScheduleReferenceError(HomePASSError):
    """Raised when a Person or grant references a missing Schedule."""

    def __init__(self, person_id: UUID) -> None:
        super().__init__("This person's schedule is unavailable")
        self.person_id = person_id


class PersonScheduleConflictError(HomePASSError):
    """Raised when one Person has inconsistent Schedule projections."""

    def __init__(
        self,
        person_id: UUID,
        distinct_schedule_count: int,
        summaries: tuple[PersonScheduleSummary, ...],
    ) -> None:
        super().__init__(
            "This person currently has different schedules assigned to different access points"
        )
        self.person_id = person_id
        self.distinct_schedule_count = distinct_schedule_count
        self.summaries = summaries


class ConcurrentPersonScheduleUpdateError(HomePASSError):
    """Raised when Person Schedule editor expectations are stale."""

    def __init__(
        self,
        person_id: UUID,
        expected_person_updated_at: datetime,
    ) -> None:
        super().__init__("This person's schedule changed while it was being edited")
        self.person_id = person_id
        self.expected_person_updated_at = expected_person_updated_at


class DuplicateAccessError(ValidationError):
    """Raised when a Person already has access to an Access Point."""


class AccessPointHasGrantsError(ValidationError):
    """Raised when a managed door cannot be removed while access remains assigned."""


class AccessPointPolicyInUseError(ValidationError):
    """Raised when a retained Access Point policy record is still referenced."""


class AccessUpdateStage(StrEnum):
    """Non-secret stages of an access update operation."""

    REQUEST_VALIDATION = "request_validation"
    DELTA_CALCULATION = "delta_calculation"
    LOCK_SLOT_REMOVAL = "lock_slot_removal"
    FINGERPRINT_LINK_DELETION = "fingerprint_link_deletion"
    ACCESS_GRANT_DELETION = "access_grant_deletion"
    SYNCHRONIZATION_METADATA_DELETION = "synchronization_metadata_deletion"
    VAULT_REFERENCE_CHECK = "vault_reference_check"
    VAULT_CREDENTIAL_DELETION = "vault_credential_deletion"
    FINAL_PERSISTENCE = "final_persistence"


class AccessUpdateError(HomePASSError):
    """Describe one failed access stage without retaining secret material."""

    def __init__(
        self,
        *,
        operation_id: UUID,
        person_id: UUID,
        stage: AccessUpdateStage,
        access_point_id: UUID | None = None,
        exception_type: str = "AccessUpdateError",
        sanitized_message: str = "Access update stage did not complete",
    ) -> None:
        """Initialize fixed, non-secret diagnostic fields."""
        super().__init__(f"Access update failed during {stage.value}")
        self.operation_id = operation_id
        self.person_id = person_id
        self.access_point_id = access_point_id
        self.stage = stage
        self.exception_type = exception_type
        self.sanitized_message = sanitized_message


class StorageError(HomePASSError):
    """Raised when a domain persistence operation fails."""


class MigrationError(StorageError):
    """Raised when stored domain data cannot be migrated."""


class LifecycleOperationNotFoundError(HomePASSError):
    """Raised when a lifecycle operation does not exist."""


class LifecycleOperationConflictError(HomePASSError):
    """Raised when lifecycle progress changed concurrently."""


class LifecycleOperationExecutionError(HomePASSError):
    """Raised after a lifecycle step failure has been persisted."""


class CredentialReplacementError(HomePASSError):
    """Raised after a sanitized credential replacement failure is persisted."""


class ConcurrentCredentialReplacementError(CredentialReplacementError):
    """Raised when credential or relationship state changed during replacement."""


__all__ = [
    "AccessPointNotFoundError",
    "AccessPointPolicyInUseError",
    "AuthorizationContextError",
    "AuthorizationInvariantError",
    "ActivityDuplicateConflictError",
    "DuplicateAccessError",
    "AccessPointHasGrantsError",
    "AccessUpdateError",
    "AccessUpdateStage",
    "DuplicatePersonError",
    "DuplicateScheduleError",
    "ConcurrentPersonScheduleUpdateError",
    "ConcurrentCredentialReplacementError",
    "CredentialAuthorityConflictError",
    "CredentialSlotIntegrityError",
    "CredentialReplacementError",
    "HomePASSError",
    "MigrationError",
    "LifecycleOperationConflictError",
    "LifecycleOperationExecutionError",
    "LifecycleOperationNotFoundError",
    "InvalidPersonScheduleReferenceError",
    "PersonNotFoundError",
    "PersonScheduleConflictError",
    "PersonScheduleSummary",
    "ProtectedScheduleError",
    "ScheduleNotFoundError",
    "StorageError",
    "ValidationError",
]
