"""Entity-targeted credential driver router."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from ..providers import AuthorizationSchedule
    from ..services.zwave_sync import (
        CreatedZWaveCredential,
        DriverCommandResult,
        VerificationStatus,
    )
    from .base import (
        CredentialRemovalRequest,
        CredentialRemovalRequestResult,
        CredentialRemovalVerificationResult,
        CredentialReplacementRequest,
        CredentialReplacementRequestResult,
        CredentialReplacementVerificationResult,
    )


class _CredentialDriver(Protocol):
    """Common numbered-credential surface used by HomePASS workflows."""

    async def provision_pin(
        self,
        lock_entity_id: str,
        pin: str,
        *,
        display_name: str | None = None,
        schedule: AuthorizationSchedule | None = None,
        enabled: bool = True,
    ) -> CreatedZWaveCredential: ...

    def validate_pin(self, lock_entity_id: str, pin: str) -> None: ...

    async def verify_pin(self, lock_entity_id: str, slot: int, pin: str) -> VerificationStatus: ...

    async def remove_pin(self, lock_entity_id: str, slot: int) -> bool: ...

    async def request_remove_pin(self, lock_entity_id: str, slot: int) -> DriverCommandResult: ...

    async def verify_pin_removed(self, lock_entity_id: str, slot: int) -> bool | None: ...

    def supports_pin_replacement(self, target_device: str) -> bool: ...

    def supports_exact_pin_readback(self, target_device: str) -> bool: ...

    async def async_request_credential_replacement(
        self, request: CredentialReplacementRequest
    ) -> CredentialReplacementRequestResult: ...

    async def async_verify_credential_replacement(
        self, request: CredentialReplacementRequest
    ) -> CredentialReplacementVerificationResult: ...

    async def async_request_credential_removal(
        self, request: CredentialRemovalRequest
    ) -> CredentialRemovalRequestResult: ...

    async def async_verify_credential_removed(
        self, request: CredentialRemovalRequest
    ) -> CredentialRemovalVerificationResult: ...


class AccessCredentialDriverRouter:
    """Route generic credential operations without vendor checks in application services."""

    def __init__(self, default_driver: _CredentialDriver) -> None:
        self._default_driver = default_driver
        self._target_drivers: dict[str, _CredentialDriver] = {}

    def register(self, target_device: str, driver: _CredentialDriver) -> None:
        if target_device in self._target_drivers:
            raise ValueError(f"Credential target {target_device!r} is already registered")
        self._target_drivers[target_device] = driver

    def _driver(self, target_device: str) -> _CredentialDriver:
        return self._target_drivers.get(target_device, self._default_driver)

    def validate_pin(self, lock_entity_id: str, pin: str) -> None:
        """Validate a PIN through the adapter selected for this exact target."""
        self._driver(lock_entity_id).validate_pin(lock_entity_id, pin)

    async def provision_pin(
        self,
        lock_entity_id: str,
        pin: str,
        *,
        display_name: str | None = None,
        schedule: AuthorizationSchedule | None = None,
        enabled: bool = True,
    ) -> CreatedZWaveCredential:
        return await self._driver(lock_entity_id).provision_pin(
            lock_entity_id,
            pin,
            display_name=display_name,
            schedule=schedule,
            enabled=enabled,
        )

    async def verify_pin(self, lock_entity_id: str, slot: int, pin: str) -> VerificationStatus:
        return await self._driver(lock_entity_id).verify_pin(lock_entity_id, slot, pin)

    async def remove_pin(self, lock_entity_id: str, slot: int) -> bool:
        return await self._driver(lock_entity_id).remove_pin(lock_entity_id, slot)

    async def request_remove_pin(self, lock_entity_id: str, slot: int) -> DriverCommandResult:
        return await self._driver(lock_entity_id).request_remove_pin(lock_entity_id, slot)

    async def verify_pin_removed(self, lock_entity_id: str, slot: int) -> bool | None:
        return await self._driver(lock_entity_id).verify_pin_removed(lock_entity_id, slot)

    def supports_pin_replacement(self, target_device: str) -> bool:
        return self._driver(target_device).supports_pin_replacement(target_device)

    def supports_exact_pin_readback(self, target_device: str) -> bool:
        return self._driver(target_device).supports_exact_pin_readback(target_device)

    async def async_request_credential_replacement(
        self, request: CredentialReplacementRequest
    ) -> CredentialReplacementRequestResult:
        return await self._driver(request.target_device).async_request_credential_replacement(
            request
        )

    async def async_verify_credential_replacement(
        self, request: CredentialReplacementRequest
    ) -> CredentialReplacementVerificationResult:
        return await self._driver(request.target_device).async_verify_credential_replacement(
            request
        )

    async def async_request_credential_removal(
        self, request: CredentialRemovalRequest
    ) -> CredentialRemovalRequestResult:
        return await self._driver(request.target_device).async_request_credential_removal(request)

    async def async_verify_credential_removed(
        self, request: CredentialRemovalRequest
    ) -> CredentialRemovalVerificationResult:
        return await self._driver(request.target_device).async_verify_credential_removed(request)
