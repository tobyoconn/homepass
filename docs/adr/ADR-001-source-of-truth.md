# ADR-001: HomePASS Source of Truth

| Field | Value |
| --- | --- |
| Status | Accepted |
| Version | 1.0 |
| Owner | HomePASS contributors |
| Last updated | 2026-07-15 |

## Context

Access state can exist both in HomePASS persistence and on physical locks. Without a clear
authority, synchronization could silently grant or remove access.

## Decision

HomePASS is the source of truth for its people, permissions, schedules, and desired device
state. Physical lock state is observed external state. Reconciliation reports differences
and must not silently adopt unknown device state as authoritative.

## Consequences

- Device drift must be visible and recoverable.
- Device changes must not implicitly rewrite HomePASS access intent.
- Conflict handling and operator recovery workflows require future specification.
