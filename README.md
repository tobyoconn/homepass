# HomePASS

HomePASS is a people-first, vendor-independent residential access-management integration for Home Assistant.

> **Development status:** active Home Assistant custom-integration development. Back up your
> Home Assistant configuration before installing a new build.

## Principles

- Home Assistant is the source of truth.
- People, permissions and schedules are first-class objects.
- Physical locks are peripherals behind capability-based drivers.
- Secrets never appear in entity state, logs, diagnostics or notifications.
- Persistent schemas are versioned and migrated.

## Current capabilities

HomePASS manages Users, Doors, schedules, PIN access, secure NTAG424 DNA access, activity,
notifications, and recovery workflows. The Doors & Devices workspace separates a logical
Door from its controller and accessories. Supported accessories are paired in Home Assistant
first, then associated with a Door in HomePASS.

Frient KEPZB-110 support currently provides ZHA discovery, Door association, and a truthful
hardware-test state. PIN-event handling is enabled only after the physical keypad's real ZHA
events have been captured and verified.

## Installation with HACS

HomePASS is a Home Assistant custom integration and is installed through HACS rather than the
Home Assistant Apps page.

1. Install and configure [HACS](https://www.hacs.xyz/docs/use/).
2. In Home Assistant, open **HACS**.
3. Open the menu in the upper-right corner and select **Custom repositories**.
4. Enter `https://github.com/tobyoconn/homepass`.
5. Select **Integration** as the category and add the repository.
6. Open the HomePASS entry and select **Download**.
7. Restart Home Assistant.
8. Go to **Settings → Devices & services → Add integration**, search for **HomePASS**, and
   complete setup.

Each Home Assistant instance performs these steps independently.

## Updates

HACS checks the HomePASS GitHub releases and creates an update notification when a newer
version is available. On each Home Assistant instance:

1. Open the HomePASS update in HACS or **Settings → System → Updates**.
2. Review the release notes and create a backup.
3. Install the update.
4. Restart Home Assistant when requested.
5. Confirm that HomePASS loads and its dashboard opens normally.

Updating one Home Assistant instance does not update or depend on any other instance.

## Manual installation for development

Copy `custom_components/homepass` into `/config/custom_components/homepass`, restart Home
Assistant, then add **HomePASS** under **Settings → Devices & services**.

Manual development installations do not receive HACS-managed updates.

## Release process

1. Update the version in `custom_components/homepass/manifest.json`,
   `custom_components/homepass/const.py`, and `pyproject.toml` together.
2. Add the release notes to `CHANGELOG.md`.
3. Merge the tested changes to `main`.
4. The release workflow reruns validation and security checks on that exact commit, including
   real startup tests on the latest stable and beta Home Assistant images. When the version is
   new, it creates the matching tag and GitHub release used by HACS only after every required
   job passes and all version fields match. An already published version is left unchanged.

Pushing a version tag also uses the same gates. Publication rejects any existing unpublished
tag that points to a different commit from the one validated.

Published version tags are immutable. Fixes are released under a new version.

## Home Assistant compatibility

HomePASS must not pin libraries already supplied by Home Assistant Core. The 1.18.8 fix
removed a duplicate `cryptography` requirement that prevented startup after a Core update.
Current validation rejects any equivalent Core-owned requirement, even when its version
happens to match today.

The **Validate** workflow runs daily, on changes, and before publishing a release. In addition
to the pinned unit-test environment, it boots HomePASS inside the latest official Home Assistant
**stable** and **beta** containers, using the real dependency installer. It checks configuration,
startup, panel registration, a harmless ping, unload, and reload with synthetic data.
Core API deprecation reports about HomePASS also fail the check before their removal deadline.
Failed compatibility checks block automated release publication. Review scheduled failures in
[GitHub Actions](https://github.com/tobyoconn/homepass/actions/workflows/validate.yml) before
upgrading Home Assistant. Beta testing provides advance warning; it cannot cover every device,
provider, or future upstream change.

For property upgrades, create a backup, install available HomePASS fixes first, then update one
Home Assistant instance and verify its HomePASS dashboard, devices, and access methods before
updating the remaining instances. See [Development Setup](DEVELOPMENT_SETUP.md) to run the
same compatibility checks locally.

See [Architecture](docs/architecture.md), [Security](docs/security.md), and
[Roadmap](ROADMAP.md).
