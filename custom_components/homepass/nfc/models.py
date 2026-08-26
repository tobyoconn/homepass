"""Durable, non-secret NFC access records."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import re
from typing import Any, Self
from uuid import UUID


def utcnow() -> datetime:
    return datetime.now(UTC)


def _timestamp(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("NFC timestamps must be timezone-aware")
    return value.astimezone(UTC).isoformat()


def _parse_timestamp(value: object) -> datetime:
    parsed = datetime.fromisoformat(str(value))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("NFC timestamps must be timezone-aware")
    return parsed.astimezone(UTC)


def _strict_bool(value: object, field: str) -> bool:
    if type(value) is not bool:
        raise TypeError(f"{field} must be a boolean")
    return value


_URLSAFE = re.compile(r"^[A-Za-z0-9_-]+$")
_HEX = re.compile(r"^[0-9A-F]+$")


@dataclass(frozen=True, slots=True)
class NfcTag:
    """One NTAG 424 DNA mapped to one HomePASS Door.

    AES values are never stored here. The two IDs reference encrypted values in
    the existing HomePASS CredentialVault.
    """

    public_id: str
    uid_hex: str
    access_point_id: UUID
    meta_key_credential_id: str
    file_key_credential_id: str
    enabled: bool
    last_counter: int | None
    created_at: datetime
    admin_key_credential_id: str | None = None
    write_protected: bool = False

    def __post_init__(self) -> None:
        if not 16 <= len(self.public_id) <= 64 or _URLSAFE.fullmatch(self.public_id) is None:
            raise ValueError("NFC public ID is invalid")
        if len(self.uid_hex) != 14 or _HEX.fullmatch(self.uid_hex.upper()) is None:
            raise ValueError("NTAG 424 UID must contain 7 hexadecimal bytes")
        UUID(self.meta_key_credential_id)
        UUID(self.file_key_credential_id)
        if self.admin_key_credential_id is not None:
            UUID(self.admin_key_credential_id)
        if type(self.enabled) is not bool:
            raise TypeError("NFC tag enabled must be a boolean")
        if type(self.write_protected) is not bool:
            raise TypeError("NFC tag write-protected state must be a boolean")
        if self.last_counter is not None and not 0 <= self.last_counter <= 0xFFFFFF:
            raise ValueError("NTAG counter is outside its 24-bit range")
        _timestamp(self.created_at)

    def to_dict(self) -> dict[str, Any]:
        return {
            "public_id": self.public_id,
            "uid_hex": self.uid_hex.upper(),
            "access_point_id": str(self.access_point_id),
            "meta_key_credential_id": self.meta_key_credential_id,
            "file_key_credential_id": self.file_key_credential_id,
            "enabled": self.enabled,
            "last_counter": self.last_counter,
            "created_at": _timestamp(self.created_at),
            "admin_key_credential_id": self.admin_key_credential_id,
            "write_protected": self.write_protected,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            public_id=str(data["public_id"]),
            uid_hex=str(data["uid_hex"]).upper(),
            access_point_id=UUID(str(data["access_point_id"])),
            meta_key_credential_id=str(data["meta_key_credential_id"]),
            file_key_credential_id=str(data["file_key_credential_id"]),
            enabled=_strict_bool(data["enabled"], "NFC tag enabled"),
            last_counter=None if data.get("last_counter") is None else int(data["last_counter"]),
            created_at=_parse_timestamp(data["created_at"]),
            admin_key_credential_id=(
                None if data.get("admin_key_credential_id") is None
                else str(data["admin_key_credential_id"])
            ),
            write_protected=_strict_bool(
                data.get("write_protected", False), "NFC tag write-protected state"
            ),
        )


@dataclass(frozen=True, slots=True)
class NfcTestTag:
    """One revocable static NTAG216 test URL mapped to one HomePASS Door."""

    token_hash: str
    access_point_id: UUID
    enabled: bool
    expires_at: datetime
    created_at: datetime

    def __post_init__(self) -> None:
        if len(self.token_hash) != 64 or _HEX.fullmatch(self.token_hash.upper()) is None:
            raise ValueError("NFC test-tag token hash is invalid")
        if not isinstance(self.access_point_id, UUID):
            raise TypeError("NFC test-tag Door ID must be a UUID")
        if type(self.enabled) is not bool:
            raise TypeError("NFC test-tag enabled must be a boolean")
        created_at = _timestamp(self.created_at)
        expires_at = _timestamp(self.expires_at)
        if expires_at <= created_at:
            raise ValueError("NFC test-tag expiry must follow creation")

    @property
    def active(self) -> bool:
        return self.enabled and self.expires_at > utcnow()

    def to_dict(self) -> dict[str, Any]:
        return {
            "token_hash": self.token_hash,
            "access_point_id": str(self.access_point_id),
            "enabled": self.enabled,
            "expires_at": _timestamp(self.expires_at),
            "created_at": _timestamp(self.created_at),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            token_hash=str(data["token_hash"]),
            access_point_id=UUID(str(data["access_point_id"])),
            enabled=_strict_bool(data["enabled"], "NFC test-tag enabled"),
            expires_at=_parse_timestamp(data["expires_at"]),
            created_at=_parse_timestamp(data["created_at"]),
        )


@dataclass(frozen=True, slots=True)
class PasskeyCredential:
    """One device-passkey WebAuthn credential owned by a HomePASS User."""

    credential_id: str
    person_id: UUID
    public_key: str
    sign_count: int
    device_type: str
    backed_up: bool
    enabled: bool
    created_at: datetime

    def __post_init__(self) -> None:
        if not self.credential_id or _URLSAFE.fullmatch(self.credential_id) is None:
            raise ValueError("Passkey credential ID is invalid")
        if not self.public_key or _URLSAFE.fullmatch(self.public_key) is None:
            raise ValueError("Passkey public key is invalid")
        if type(self.sign_count) is not int or self.sign_count < 0:
            raise ValueError("Passkey sign count is invalid")
        if type(self.backed_up) is not bool or type(self.enabled) is not bool:
            raise TypeError("Passkey flags must be booleans")
        _timestamp(self.created_at)

    def to_dict(self) -> dict[str, Any]:
        return {
            "credential_id": self.credential_id,
            "person_id": str(self.person_id),
            "public_key": self.public_key,
            "sign_count": self.sign_count,
            "device_type": self.device_type,
            "backed_up": self.backed_up,
            "enabled": self.enabled,
            "created_at": _timestamp(self.created_at),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            credential_id=str(data["credential_id"]),
            person_id=UUID(str(data["person_id"])),
            public_key=str(data["public_key"]),
            sign_count=data["sign_count"],
            device_type=str(data["device_type"]),
            backed_up=_strict_bool(data["backed_up"], "Passkey backed_up"),
            enabled=_strict_bool(data["enabled"], "Passkey enabled"),
            created_at=_parse_timestamp(data["created_at"]),
        )


@dataclass(frozen=True, slots=True)
class NfcAccessGrant:
    """One explicit NFC-only Person-to-Door policy relationship."""

    person_id: UUID
    access_point_id: UUID
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.person_id, UUID):
            raise TypeError("NFC access grant Person ID must be a UUID")
        if not isinstance(self.access_point_id, UUID):
            raise TypeError("NFC access grant Door ID must be a UUID")
        _timestamp(self.created_at)
        _timestamp(self.updated_at)
        if self.updated_at < self.created_at:
            raise ValueError("NFC access grant update precedes creation")

    def to_dict(self) -> dict[str, Any]:
        return {
            "person_id": str(self.person_id),
            "access_point_id": str(self.access_point_id),
            "created_at": _timestamp(self.created_at),
            "updated_at": _timestamp(self.updated_at),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            person_id=UUID(str(data["person_id"])),
            access_point_id=UUID(str(data["access_point_id"])),
            created_at=_parse_timestamp(data["created_at"]),
            updated_at=_parse_timestamp(data["updated_at"]),
        )


@dataclass(frozen=True, slots=True)
class EnrollmentInvite:
    """A hashed, expiring, single-use passkey enrollment invitation."""

    token_hash: str
    person_id: UUID
    person_name: str
    expires_at: datetime
    used_at: datetime | None
    created_at: datetime

    def __post_init__(self) -> None:
        if len(self.token_hash) != 64 or _HEX.fullmatch(self.token_hash.upper()) is None:
            raise ValueError("Enrollment token hash is invalid")
        if not self.person_name.strip():
            raise ValueError("Enrollment Person name is empty")
        created_at = _timestamp(self.created_at)
        expires_at = _timestamp(self.expires_at)
        if expires_at <= created_at:
            raise ValueError("Enrollment expiry must follow creation")
        if self.used_at is not None:
            _timestamp(self.used_at)

    @property
    def active(self) -> bool:
        return self.used_at is None and self.expires_at > utcnow()

    def to_dict(self) -> dict[str, Any]:
        return {
            "token_hash": self.token_hash,
            "person_id": str(self.person_id),
            "person_name": self.person_name,
            "expires_at": _timestamp(self.expires_at),
            "used_at": None if self.used_at is None else _timestamp(self.used_at),
            "created_at": _timestamp(self.created_at),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        used_at = data.get("used_at")
        return cls(
            token_hash=str(data["token_hash"]),
            person_id=UUID(str(data["person_id"])),
            person_name=str(data["person_name"]),
            expires_at=_parse_timestamp(data["expires_at"]),
            used_at=None if used_at is None else _parse_timestamp(used_at),
            created_at=_parse_timestamp(data["created_at"]),
        )
