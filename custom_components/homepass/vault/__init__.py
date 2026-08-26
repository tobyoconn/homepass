"""HomePASS Standard Mode credential vault.

Plaintext is accepted and returned only through the public ``CredentialVaultProtocol``.
Encryption and storage details remain private to this package.
"""

from .errors import (
    VaultAuthenticationError,
    VaultCorruptDataError,
    VaultCredentialNotFoundError,
    VaultDuplicateStageError,
    VaultError,
    VaultInvalidStagedSecretHandleError,
    VaultNotInitializedError,
    VaultPromotionError,
    VaultStagedSecretMissingError,
    VaultStalePromotionError,
    VaultUnavailableError,
    VaultUnsupportedKeyVersionError,
    VaultUnsupportedSchemaVersionError,
)
from .identifiers import StagedSecretHandle, VaultCredentialId
from .models import (
    AccessMethod,
    CredentialMetadata,
    CredentialMetadataData,
    VaultPromotionReceipt,
    VaultStatus,
)
from .protocol import CredentialVaultProtocol

__all__ = [
    "AccessMethod",
    "CredentialMetadata",
    "CredentialMetadataData",
    "CredentialVaultProtocol",
    "StagedSecretHandle",
    "VaultAuthenticationError",
    "VaultCorruptDataError",
    "VaultCredentialNotFoundError",
    "VaultDuplicateStageError",
    "VaultError",
    "VaultInvalidStagedSecretHandleError",
    "VaultNotInitializedError",
    "VaultPromotionReceipt",
    "VaultPromotionError",
    "VaultStagedSecretMissingError",
    "VaultStalePromotionError",
    "VaultStatus",
    "VaultCredentialId",
    "VaultUnavailableError",
    "VaultUnsupportedSchemaVersionError",
    "VaultUnsupportedKeyVersionError",
]
