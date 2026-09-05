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
3. Merge the tested changes.
4. Create and push a matching tag such as `v1.16.5`.
5. The release workflow verifies that the tag matches the manifest and publishes the GitHub
   release used by HACS.

Published version tags are immutable. Fixes are released under a new version.

See [Architecture](docs/architecture.md), [Security](docs/security.md), and
[Roadmap](ROADMAP.md).
