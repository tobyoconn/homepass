# Security model

PINs are authentication secrets, not ordinary configuration.

## Invariants

- No PIN in entity state or attributes.
- No PIN in logs, traces, notifications, exceptions or diagnostics.
- No PIN in service responses.
- Administrative reveal must be explicit, authorized and audited.
- Metadata commits only after successful physical programming.

## Foundation decision

The metadata repository contains no credential plaintext or ciphertext. Credential storage will be introduced only after an approved key-management design.

Encrypting data while storing the decryption key beside it protects against casual inspection, but not against compromise of the Home Assistant configuration directory. The credential-vault ADR must define threat model, key lifecycle, backup/restore behavior, rotation, redaction tests and recovery before implementation.
