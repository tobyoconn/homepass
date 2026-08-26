# HomePASS Project Charter

| Field | Value |
| --- | --- |
| Status | Draft |
| Version | 0.1 |
| Owner | HomePASS contributors |
| Last updated | 2026-07-15 |

## Purpose

HomePASS provides people-first, vendor-independent residential access management for
Home Assistant.

## Goals

- Make people, permissions, and schedules the primary access-control concepts.
- Keep Home Assistant authoritative for HomePASS configuration and desired state.
- Support physical locks through capability-based drivers.
- Protect credentials throughout storage, operation, logging, and diagnostics.

## Initial scope

- A versioned registry for non-secret access metadata.
- Vendor-neutral domain and application boundaries.
- Driver contracts for future lock integrations.
- Home Assistant configuration and service surfaces.

## Out of scope

- Cloud-hosted access management.
- A replacement for Home Assistant authentication or user management.
- Support claims for devices without tested drivers.

## Governance

Architectural decisions are recorded in [`docs/adr`](adr/README.md). Release ownership,
support policy, and decision-making procedures are **TBD**.
