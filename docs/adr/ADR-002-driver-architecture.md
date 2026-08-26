# ADR-002: Driver Architecture

| Field | Value |
| --- | --- |
| Status | Accepted |
| Version | 1.0 |
| Owner | HomePASS contributors |
| Last updated | 2026-07-15 |

## Context

Lock vendors and protocols expose different capabilities, identifiers, and failure modes.
Allowing those details into the domain would couple access rules to individual devices.

## Decision

HomePASS accesses physical locks through vendor-neutral, capability-based driver contracts.
Protocol payloads, vendor APIs, and slot identifiers remain within adapter implementations.

## Consequences

- Domain and application behavior can remain independent of lock vendors.
- Drivers require contract tests for supported capabilities and failure behavior.
- Vendor-specific behavior is exposed only through explicit optional capabilities.
- Initial capability definitions and compatibility policy require future specification.

This decision complements [ADR 0001](0001-architecture-boundaries.md).
