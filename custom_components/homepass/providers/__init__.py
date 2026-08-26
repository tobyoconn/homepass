"""Physical access provider adapters used by HomePASS."""

from .base import (
    AccessProviderCapabilities,
    AuthorizationMutation,
    AuthorizationMutationState,
    AuthorizationProvider,
    AuthorizationProviderRegistry,
    AuthorizationRecord,
    AuthorizationRequest,
    AuthorizationSchedule,
    LockControlProvider,
    LockState,
    ProviderAuditEvent,
    ProviderCommunicationError,
)

__all__ = [
    "AccessProviderCapabilities",
    "AuthorizationMutation",
    "AuthorizationMutationState",
    "AuthorizationProvider",
    "AuthorizationProviderRegistry",
    "AuthorizationRecord",
    "AuthorizationRequest",
    "AuthorizationSchedule",
    "LockControlProvider",
    "LockState",
    "ProviderAuditEvent",
    "ProviderCommunicationError",
]
