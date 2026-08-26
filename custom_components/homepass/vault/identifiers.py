"""Strongly typed credential-vault identifiers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Self
from uuid import UUID, uuid4


@dataclass(frozen=True, slots=True)
class VaultCredentialId:
    """Identify one encrypted credential without using raw strings."""

    value: UUID

    def __post_init__(self) -> None:
        """Validate the identifier value."""
        if not isinstance(self.value, UUID):
            raise TypeError("VaultCredentialId value must be a UUID")

    @classmethod
    def new(cls) -> Self:
        """Generate a cryptographically random credential identifier."""
        return cls(uuid4())

    @classmethod
    def from_string(cls, value: str) -> Self:
        """Parse a serialized identifier without reflecting malformed input."""
        if not isinstance(value, str):
            raise TypeError("VaultCredentialId must be a UUID string")
        try:
            return cls(UUID(value))
        except ValueError as err:
            raise ValueError("VaultCredentialId must be a valid UUID") from err

    def __str__(self) -> str:
        """Return the canonical UUID representation."""
        return str(self.value)


@dataclass(frozen=True, slots=True)
class StagedSecretHandle:
    """Opaque reference to one encrypted staged secret."""

    value: UUID

    def __post_init__(self) -> None:
        """Validate the opaque handle value."""
        if not isinstance(self.value, UUID):
            raise TypeError("StagedSecretHandle value must be a UUID")

    @classmethod
    def new(cls) -> Self:
        """Generate a cryptographically random opaque handle."""
        return cls(uuid4())

    @classmethod
    def from_string(cls, value: str) -> Self:
        """Parse a serialized handle without reflecting malformed input."""
        if not isinstance(value, str):
            raise TypeError("StagedSecretHandle must be a UUID string")
        try:
            return cls(UUID(value))
        except ValueError as err:
            raise ValueError("StagedSecretHandle must be a valid UUID") from err

    def __str__(self) -> str:
        """Return the opaque UUID representation."""
        return str(self.value)
