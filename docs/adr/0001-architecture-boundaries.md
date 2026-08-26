# ADR 0001: Layered architecture and driver boundary

- Status: Accepted
- Date: 2026-07-15

## Decision

Core HomePASS concepts are vendor-neutral. Physical devices are accessed through capability-based driver interfaces. Slot numbers and service-specific payloads remain inside adapters.

## Consequences

New vendors can be added without changing person or permission models. Drivers require contract tests. Some vendor-specific features may remain unavailable until represented as explicit optional capabilities.
