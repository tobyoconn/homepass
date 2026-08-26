# Architecture

HomePASS uses a layered architecture:

1. **Domain:** people, credentials, properties, access grants and schedules.
2. **Application:** use cases and transaction orchestration.
3. **Ports:** repositories, credential vaults, clocks, audit sinks and lock drivers.
4. **Adapters:** Home Assistant storage, Z-Wave JS, Zigbee, Matter and future vendors.
5. **Presentation:** Home Assistant config flows, actions, entities and panel UI.

Dependencies point inward. Vendor adapters may import Home Assistant APIs; domain models should not.

## Transaction rule

Metadata describing a physical credential assignment is committed only after the device operation succeeds. Reconciliation detects drift without silently adopting unknown lock state as authoritative.

## Stable identifiers

People and future records use UUIDs. Lock slot numbers are adapter data, never identity.
