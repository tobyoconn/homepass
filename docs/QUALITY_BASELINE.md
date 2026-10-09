# Quality baseline

This file records the pre-publication validation baseline established on 26 August 2026.
It is intentionally free of installation, property, device, network, credential, and personal data.

## Mandatory CI

Every push and pull request runs these independent jobs:

- the complete pytest suite;
- real startup, panel, ping, unload and reload checks in the latest official Home Assistant
  stable and beta containers, using Core's dependency installer without test-fixture bypasses;
- Ruff correctness checks;
- a strict mypy ratchet over the security-critical vault, authorization, and schedule core;
- Hassfest;
- the separate repository-privacy and Gitleaks workflows.

Validation also runs daily so upstream releases are checked without a HomePASS code change.
The release workflow reuses validation and security checks on the tagged source and waits for
them to succeed before publishing. A generic dependency-ownership check rejects requirements
already supplied by the installed Core version. Regression tests include the duplicate
cryptography requirement responsible for the October 2026 startup outage.
Core API deprecation reports attributed to HomePASS fail the startup check, providing an
early warning before the deprecated API is removed.

The Ruff gate initially enables `E9`, `F63`, `F7`, and `F82`. These rules reject syntax
errors, invalid control flow, undefined names, and related correctness defects.

## Recorded legacy style debt

A full `ruff check .` with the broader historical rule set reported 552 findings. Ruff identified
299 safe automatic fixes; after applying those fixes and formatting in a disposable audit copy,
303 findings remained, overwhelmingly type-checking import-placement rules. A formatting check
reported 34 files requiring formatting before the disposable copy was normalized.

Those mechanical changes were not copied into the release branch because moving runtime imports
behind `TYPE_CHECKING` can change Home Assistant integration behavior and requires review. Broader
Ruff rules and `ruff format --check` should be enabled incrementally as focused cleanup pull
requests reach zero findings.

## Python and mypy baseline

HomePASS unit-test validation targets Python 3.14 and the fixed Home Assistant test line selected
by `requirements-dev.txt`. Current compatibility is checked separately with floating stable/beta
images, which supply their own Python runtime. Core owns shared dependencies such as cryptography;
HomePASS must not override their versions in its integration manifest or validation requirements.

A full strict mypy audit over `custom_components/homepass` and `tests` reported 155 errors in
27 files. Most test findings are missing annotations or intentionally loose mock types. Production
findings are concentrated in Home Assistant API typing, optional-value narrowing, and repository
model boundaries. This debt is recorded rather than hidden.

Mandatory CI runs strict mypy first over the security-critical vault, authorization, and schedule
core. That clean scope is a ratchet: it must not regress and should expand as focused cleanup pull
requests remove the recorded debt. Only untyped third-party modules are excluded from import
analysis.

Do not add a blanket `ignore_errors`, reduce strictness, or expand third-party exclusions to hide
HomePASS errors. New exclusions require a narrow explanation and review.
