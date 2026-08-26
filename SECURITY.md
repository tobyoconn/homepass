# Security policy

## Reporting a vulnerability

Please do not report vulnerabilities in a public issue. Use GitHub's private
vulnerability reporting feature on the repository's **Security** page.

Include the affected HomePASS version, the Home Assistant version, a concise
description of the impact, and reproduction steps that do not contain real
credentials, keys, NFC identifiers, device identifiers, addresses, or personal
details.

## Supported versions

Security fixes are provided for the latest published HomePASS release. Upgrade to
the latest version before reporting an issue that may already have been corrected.

## Repository privacy

The developer policy for keeping installation data and secrets out of source control is in
[`docs/REPOSITORY_PRIVACY.md`](docs/REPOSITORY_PRIVACY.md). Real secrets must be rotated or revoked
if committed, even when the offending line is subsequently deleted.
