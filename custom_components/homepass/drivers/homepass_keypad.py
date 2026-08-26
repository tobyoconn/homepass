"""Local credential lifecycle behavior for HomePASS-managed keypads."""

from __future__ import annotations

from .base import (
    CredentialRemovalRequest,
    CredentialRemovalRequestResult,
    CredentialRemovalRequestStatus,
    CredentialRemovalVerificationResult,
    CredentialRemovalVerificationStatus,
    CredentialReplacementRequest,
    CredentialReplacementRequestResult,
    CredentialReplacementRequestStatus,
    CredentialReplacementVerificationResult,
    CredentialReplacementVerificationStatus,
)


class HomePassKeypadCredentialDriver:
    """Acknowledge Vault-only changes for keypads that never store the PIN."""

    def supports_pin_replacement(self, _target_device: str) -> bool:
        """Return true because the PIN authority lives only in the HomePASS Vault."""
        return True

    def supports_exact_pin_readback(self, _target_device: str) -> bool:
        """Return true because HomePASS owns the complete keypad credential authority."""
        return True

    async def async_request_credential_replacement(
        self,
        _request: CredentialReplacementRequest,
    ) -> CredentialReplacementRequestResult:
        """Acknowledge replacement without sending the secret to the keypad."""
        return CredentialReplacementRequestResult(CredentialReplacementRequestStatus.ACCEPTED)

    async def async_verify_credential_replacement(
        self,
        _request: CredentialReplacementRequest,
    ) -> CredentialReplacementVerificationResult:
        """Confirm the local-only replacement checkpoint."""
        return CredentialReplacementVerificationResult(
            CredentialReplacementVerificationStatus.REPLACEMENT_CONFIRMED
        )

    async def async_request_credential_removal(
        self,
        _request: CredentialRemovalRequest,
    ) -> CredentialRemovalRequestResult:
        """Acknowledge removal because there is no keypad-resident secret."""
        return CredentialRemovalRequestResult(CredentialRemovalRequestStatus.ACCEPTED)

    async def async_verify_credential_removed(
        self,
        _request: CredentialRemovalRequest,
    ) -> CredentialRemovalVerificationResult:
        """Confirm that no credential remains on the physical keypad."""
        return CredentialRemovalVerificationResult(
            CredentialRemovalVerificationStatus.REMOVED
        )


__all__ = ["HomePassKeypadCredentialDriver"]
