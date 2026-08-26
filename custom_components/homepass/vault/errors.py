"""PIN-safe errors for credential-vault contracts."""


class VaultError(Exception):
    """Base exception for credential-vault failures."""

    message = "Credential vault operation failed"

    def __init__(self) -> None:
        """Initialize the exception with a fixed, non-secret message."""
        super().__init__(self.message)


class VaultNotInitializedError(VaultError):
    """Raised when an operation requires an initialized vault."""

    message = "Credential vault is not initialized"


class VaultUnavailableError(VaultError):
    """Raised when the vault cannot safely perform operations."""

    message = "Credential vault is unavailable"


class VaultCorruptDataError(VaultError):
    """Raised when vault data is malformed or fails integrity checks."""

    message = "Credential vault data is corrupt"


class VaultAuthenticationError(VaultError):
    """Raised when vault authentication fails."""

    message = "Credential vault authentication failed"


class VaultUnsupportedSchemaVersionError(VaultError):
    """Raised when stored data uses an unsupported schema version."""

    message = "Credential vault schema version is unsupported"


class VaultUnsupportedKeyVersionError(VaultError):
    """Raised when no matching root-key version is available."""

    message = "Credential vault key version is unsupported"


class VaultCredentialNotFoundError(VaultError):
    """Raised when an encrypted credential envelope does not exist."""

    message = "Encrypted credential was not found"


class VaultInvalidStagedSecretHandleError(VaultError):
    """Raised when a staged-secret handle has an invalid type."""

    message = "Staged credential handle is invalid"


class VaultStagedSecretMissingError(VaultError):
    """Raised when an opaque staged-secret handle no longer exists."""

    message = "Staged credential was not found"


class VaultDuplicateStageError(VaultError):
    """Raised when a credential already has one staged replacement."""

    message = "A staged replacement already exists"


class VaultStalePromotionError(VaultError):
    """Raised when authoritative credential state changed after staging."""

    message = "Staged credential promotion is stale"


class VaultPromotionError(VaultError):
    """Raised when an atomic staged-secret promotion cannot be persisted."""

    message = "Staged credential promotion failed"


__all__ = [
    "VaultAuthenticationError",
    "VaultCorruptDataError",
    "VaultCredentialNotFoundError",
    "VaultDuplicateStageError",
    "VaultError",
    "VaultInvalidStagedSecretHandleError",
    "VaultNotInitializedError",
    "VaultPromotionError",
    "VaultStagedSecretMissingError",
    "VaultStalePromotionError",
    "VaultUnavailableError",
    "VaultUnsupportedSchemaVersionError",
    "VaultUnsupportedKeyVersionError",
]
