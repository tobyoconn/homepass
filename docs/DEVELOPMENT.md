# HomePASS Development Guide

| Field | Value |
| --- | --- |
| Status | Draft |
| Version | 0.1 |
| Owner | HomePASS contributors |
| Last updated | 2026-07-15 |

## Prerequisites

- Python 3.13 or later.
- A Home Assistant development or test environment for integration testing.

Environment bootstrap and supported Home Assistant versions are **TBD**.

## Development workflow

1. Keep domain behavior vendor-neutral and dependencies directed inward.
2. Add or update tests with behavior changes.
3. Record consequential architectural choices in `docs/adr`.
4. Run the repository's configured tests, linting, and type checks before review.

Exact environment setup and command aliases are **TBD**.

## Quality expectations

- Preserve strict typing and the configured formatting conventions.
- Keep secrets out of state, logs, diagnostics, fixtures, and notifications.
- Cover drivers with contract tests and persistence changes with migration tests.
- Keep user-facing strings translatable through Home Assistant conventions.

## Pull requests

Contribution, review, release, and compatibility policies are **TBD**. Until defined, keep
changes focused and document user-visible or architectural impact.
