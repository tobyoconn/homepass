"""Public plaintext-in-memory credential-vault contract."""

from collections.abc import Callable
from typing import Protocol, runtime_checkable

from .identifiers import StagedSecretHandle, VaultCredentialId
from .models import VaultPromotionReceipt, VaultStatus


@runtime_checkable
class CredentialVaultProtocol(Protocol):
    """Define the only interface available outside the vault subsystem."""

    @property
    def status(self) -> VaultStatus:
        """Return the current Standard Mode lifecycle status."""
        ...

    async def initialize(self) -> None:
        """Load or safely create Standard Mode vault state."""
        ...

    async def store(self, plaintext: str) -> VaultCredentialId:
        """Encrypt and persist one plaintext credential supplied in memory."""
        ...

    async def retrieve(
        self,
        credential_id: VaultCredentialId,
        *,
        trace: Callable[[str], None] | None = None,
    ) -> str:
        """Authenticate and return one plaintext credential in memory."""
        ...

    async def delete(self, credential_id: VaultCredentialId) -> None:
        """Delete one encrypted credential envelope."""
        ...

    async def exists(self, credential_id: VaultCredentialId) -> bool:
        """Return whether an encrypted credential envelope exists."""
        ...

    async def stage(
        self,
        credential_id: VaultCredentialId,
        plaintext: str,
    ) -> StagedSecretHandle:
        """Encrypt and stage a replacement without changing the credential."""
        ...

    async def retrieve_staged(self, handle: StagedSecretHandle) -> str:
        """Authenticate and return one staged plaintext only in memory."""
        ...

    async def promote(self, handle: StagedSecretHandle) -> VaultPromotionReceipt:
        """Atomically replace the authoritative secret with a staged secret."""
        ...

    async def discard(self, handle: StagedSecretHandle) -> None:
        """Idempotently discard one staged secret."""
        ...

    async def revision(self, credential_id: VaultCredentialId) -> int:
        """Return the non-secret revision of an authoritative credential."""
        ...

    async def promotion_receipt(self, handle: StagedSecretHandle) -> VaultPromotionReceipt | None:
        """Return non-secret evidence for an already-completed promotion."""
        ...
