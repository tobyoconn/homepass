# ADR 0002: Credential vault key management

- Status: Proposed
- Date: 2026-07-15

## Context

HomePASS must retain recoverable PINs so an administrator can remind an authorized person of a PIN. Hashing alone is therefore insufficient.

## Decision required

Select a key-management and backup model before PIN persistence is implemented. Candidate designs must be evaluated against config-directory theft, backup portability, disaster recovery, unattended restart and key rotation.

## Temporary rule

No real PIN may be persisted by `0.1.0-dev0`.
