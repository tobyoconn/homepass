# Quality baseline

This file records the pre-publication validation baseline established on 26 August 2026.
It is intentionally free of installation, property, device, network, credential, and personal data.

## Mandatory CI

Every push and pull request runs these independent jobs:

- the complete pytest suite;
- Ruff correctness checks;
- a strict mypy ratchet over the security-critical vault, authorization, and schedule core;
- Hassfest;
- the separate repository-privacy and Gitleaks workflows.

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

HomePASS validation targets Python 3.14 and the corresponding current Home Assistant test line.
This matches the integration's current runtime dependency set; the older Python 3.13 Home Assistant
line pins an incompatible cryptography version.

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
