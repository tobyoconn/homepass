# Changelog

## [1.17.4] - 2026-08-26

### Added

- Added battery levels for supported locks, door sensors and access devices using their
  standard Home Assistant battery entities.
- Added low and critically low battery Activity entries and notifications without
  generating alerts for normal battery readings during startup.

### Security

- Added automated Gitleaks and HomePASS-specific privacy checks in CI, with local
  pre-commit support and strengthened exclusions for runtime, deployment, credential,
  state and machine-specific files.

## [1.17.3] - 2026-08-25

### Fixed

- Refreshed User card summaries whenever the Users or Dashboard page is reopened, so
  completed asynchronous access removals cannot leave stale Door counts on screen.

## [1.17.2] - 2026-08-25

### Fixed

- Restored HomePASS startup when NFC is configured by wiring the Door command service to
  both the NFC capability check and the NFC command dispatcher.

## [1.17.1] - 2026-08-25

### Added

- Added secure Zigbee2MQTT keypad discovery and command handling alongside the existing
  ZHA keypad path.

### Fixed

- Restored storage schema 19 compatibility so installations that already manage a
  Zigbee2MQTT keypad can upgrade without rejecting their existing HomePASS data.
- Kept Yale/Z-Wave, Nuki Bluetooth/Matter, ZHA keypad and Zigbee2MQTT keypad services
  available from the same released integration.

## [1.17.0] - 2026-08-25

### Added

- Added a provider-adapter architecture so Yale/Z-Wave and Nuki locks can run from the
  same HomePASS installation, including mixed-provider properties.
- Added local Nuki keypad PIN, schedule and audit management over Home Assistant Bluetooth,
  while retaining Matter/Home Assistant for lock state and lock commands.
- Added Nuki fingerprint-association guidance, keypad-storage inspection, and safe review
  of keypad PINs created outside HomePASS.
- Added optional Home Assistant door/contact sensors and clearer combined door and lock
  status throughout the interface.

### Changed

- Door permissions and schedules can be prepared before a User has created a PIN or enrolled
  for NFC, and NFC enrollment no longer depends on an NFC-enabled Door.
- Setup pages for Doors, sensors, keypads, PINs, NFC, schedules and fingerprints are shorter,
  more consistent and focused on the current task.
- Provider synchronization now reports pending, confirmed and failed states and offers
  bounded retries and clearer Bluetooth diagnostics.

### Fixed

- Preserved Yale/Z-Wave PIN allocation, replacement, removal and verification behavior behind
  the provider boundary, with regression coverage for failed or delayed lock confirmation.
- Fixed access removal, PIN replacement, schedule preparation, NFC assignment and Nuki
  Bluetooth pairing/recovery edge cases.
- Added an explicit irreversible-action confirmation before deleting an unmanaged Nuki PIN.

### Security

- Nuki credentials and security PINs remain in Home Assistant's encrypted HomePASS vault or
  config-entry options and are not committed to source control.
- Destructive keypad operations identify the selected authorization without displaying PIN
  digits and require a separate permanent-deletion confirmation.

## [1.16.6] - 2026-08-15

### Security

- Replaced installation-specific examples and personal metadata with neutral test data.
- Added repository safeguards for local Home Assistant state, credentials, private keys,
  deployment profiles, and generated NFC provisioning files.
- Added automated dependency update checks and refreshed the private vulnerability
  reporting policy.

## [1.16.5] - 2026-08-14

- Prevented versioned HomePASS browser components from reusing an already-registered
  constructor, removing the duplicate-registration error and associated panel reload flicker.

## [1.16.4] - 2026-08-14

### Changed

- NFC door-access pages now state that access is limited to enrolled, authorized
  users and direct other visitors to contact the property owner for entry.

## [1.16.3] - 2026-08-14

### Fixed

- Keypad-backed roller doors now allocate a distinct logical credential slot for each
  user, preventing the second user's door-access assignment from failing.
- Door-access save errors identify the affected Door when possible and no longer imply
  that every failure is caused by a physical lock.

## [1.16.2] - 2026-08-14

### Changed

- NFC access pages for garage and roller doors now offer the action appropriate
  to the current position: open when closed and close when open.
- The selected action is bound to the 30-second NFC tap session so the passkey
  confirmation and physical command remain predictable.
- Ordinary lock and electric-strike NFC pages remain unlock-only.

## [1.16.1] - 2026-08-14

### Added

- The NFC setup screen now identifies NTAG424 DNA as the supported HomePASS tag,
  links to GoToTags Desktop, names an example compatible reader, and explains that
  other NTAG424-compatible writers can use the manual setup path.
- Administrators can choose key-protected re-writing or irreversible permanent
  locking before generating the ready-to-write GoToTags operation.
- Manual setup now displays the complete NDEF, application-key, file-access, SDM,
  and calculated offset configuration required by another compatible writer.

### Changed

- Reduced the automatic instructions to opening the downloaded GoToTags file,
  starting encoding, presenting the matching tag, and waiting for verification.

## [1.16.0] - 2026-08-14

### Added

- HomePASS now downloads a private, ready-to-write `.gototags` operation for each
  NTAG424 setup or rewrite-protection task. Double-clicking the file opens GoToTags
  with one READY row, Lock FALSE, verification enabled, and the correct tag keys.
- The direct operation is generated without GoToTags account, computer, reader,
  network, or previous write-history metadata.

### Changed

- Reduced the standard GoToTags workflow to download, double-click, verify READY,
  press Play, present the matching tag, and wait for VERIFIED. CSV and generic JSON
  remain available as advanced fallbacks.

## [1.15.2] - 2026-08-14

### Fixed

- Prepared NFC tags now offer the protection file for download again instead of allowing
  rewrite protection to be recorded without a verified GoToTags write.
- The final protection confirmation appears only after HomePASS generates the operation
  in the current browser session.

## [1.15.1] - 2026-08-14

### Changed

- Clarified keypad guidance for garage and roller-door controllers: either supported
  padlock button activates the controller's normal toggle behavior, while auxiliary
  keypad buttons remain ignored.

## [1.15.0] - 2026-08-14

### Added

- Live ZHA support for the Frient KEPZB-110 using its two padlock controls.
- HomePASS-managed PIN assignments for keypad-backed garage doors without attempting to
  program the garage controller itself.
- Automatic physical-test completion after the first authorized keypad operation.

### Changed

- Keypad setup guidance now tells administrators exactly how to assign a User and test the
  two supported buttons; house, night, emergency, and unsupported controls remain inert.
- Physical roller-door confirmation and Activity now preserve the authorized User and PIN
  attribution.

### Security

- Keypad PINs are compared only in memory against the encrypted HomePASS Vault and are never
  persisted or logged from ZHA events.
- Invalid attempts are rate-limited per keypad and fail closed when PIN identity or current
  Door authorization is ambiguous.

## [1.14.0] - 2026-08-13

### Added

- A new Doors & Devices workspace that keeps each logical Door separate from the
  Home Assistant controller and accessory devices used with it.
- HomePASS-managed accessory-device records, durable Door associations, and safe removal
  when a Door leaves HomePASS.
- Discovery and administrator setup for a Frient KEPZB-110 keypad paired through ZHA.
- Truthful `Awaiting hardware test` state so the keypad is not presented as operational
  until its real ZHA events have been observed and verified.

### Changed

- Loaded Doors and their associated devices as one interface update to avoid a second
  visible refresh on initial page load.
- Preserved a keypad's logical Door association while the Door controller is temporarily
  unavailable or offline.

### Security

- Kept Home Assistant device identifiers administrator-only and excluded them from managed
  device views.
- Defaulted emergency and unverified keypad functions to no action; no PIN-event listener is
  enabled until the physical keypad event format has been tested.

## [1.13.1] - 2026-08-13

- Replaced the ambiguous NFC protection confirmation with a clear “Record tag as
  protected” action that explains it records GoToTags' successful verification and
  does not write to the tag again.
- Batched Door dialog data refreshes so loading and NFC actions settle in one stable
  update instead of repeatedly rebuilding the dialog as separate requests finish.

## [1.13.0] - 2026-08-13

- Replaced ambiguous Door switches with explicit Lock, Unlock, Open, Close, Release,
  and Activate actions; security-sensitive operations now require slide confirmation.
- Made all HomePASS sections available from a fixed mobile navigation bar and added
  reduced-motion support.
- Consolidated User Door access presentation with PIN, NFC, and schedule context,
  plus clearer passkey enrollment summaries.
- Added notification presets and shortened Dashboard activity with a View all route.
- Rebuilt NTAG424 provisioning guidance around the verified GoToTags workflow with
  safe retry and recovery instructions.
- Reduced the Users page NFC summary loading from one request per User to one request
  for the full list.
- Hardened NFC repository writes so failed persistence cannot partially change live
  credential, tag, grant, invite, or audit state.

## [1.12.0] - 2026-08-12

### Added

- Recoverable NTAG424 rewrite protection using a unique HomePASS administrator key
  retained in the encrypted credential vault; NFC reads remain public while rewrites
  require that key.
- A per-tag protection conversion download and explicit administrator confirmation after
  GoToTags reports a green VERIFIED result.

### Changed

- Replaced the NFC-writing guidance with the exact GoToTags Desktop 4.37 workflow verified
  while provisioning the Front Door tag, including operation selection, chip choice,
  verification, import, reader timing, and success checks.
- New NTAG424 setup downloads now apply recoverable rewrite protection during their first
  successful encoding while retaining `Lock FALSE` and avoiding permanent read-only mode.

### Security

- Existing working tags can be converted without changing their Door URL or SDM keys, and
  HomePASS records protection only after the administrator confirms a verified write.
- A confirmed rewrite resets the server's remembered tap counter so the first post-write
  phone tap remains valid even if encoder behavior affects the physical counter.

## [1.10.0] - 2026-08-12

### Added

- NFC Door selection to the passkey-enrollment workflow, with compatible Doors that
  already have PIN access pre-selected for the administrator.

### Changed

- Consolidated PIN and NFC methods beside each Door in the User's main access list.
- Moved post-enrollment NFC Door editing into that consolidated list and removed the
  redundant Access Summary card and separate enrolled NFC Door list.

## [1.9.1] - 2026-08-12

- Added user-facing NFC Door assignment controls to the NFC enrollment card.
- Added sanitized enrolled-passkey device details to each User's Credential card.
- Added per-Door NFC tag UID/status listing and individual tag revocation.

All notable changes follow Keep a Changelog. Versions follow Semantic Versioning.

## [1.9.0] - 2026-08-12

### Added

- A per-tag GoToTags CSV download that can be imported into a Variable Encode NFC Tags
  operation, with the unique HomePASS URL, Key 1, Key 2, and verified NTAG424 SDM
  configuration already populated.
- The verified CC, NDEF, proprietary-file, and SDM profile in the software-neutral setup
  JSON for independent review and use with other compatible NFC encoders.

### Security

- Encoding guidance now identifies the exact physical UID intended for the one-row file,
  keeps permanent locking disabled, and requires a phone/passkey/physical-Door verification
  before the tag is installed.

## [1.8.1] - 2026-08-11

### Changed

- Successful passkey enrollment and NFC Door unlock pages now clearly confirm that the
  visitor can safely close the page or navigate away on every supported platform.

## [1.8.0] - 2026-08-11

### Added

- Apple, Android, and generic device presentation for NFC enrollment and unlock pages,
  including suitable passkey wording and icons without changing authorization behavior.
- A dedicated expired NFC-tap screen after 30 seconds that directs the visitor to tap
  the tag again and confirms that the old page can be closed safely.

### Security

- Reduced server-side NFC tap-session validity from two minutes to 30 seconds and aligned
  the WebAuthn authentication timeout, so the expired screen cannot continue an unlock.

## [1.7.3] - 2026-08-11

### Changed

- NFC unlock activity now identifies the authenticated HomePASS User and the NFC access
  method, for example “Alex unlocked Front Door Lock by NFC.”

### Security

- NFC-to-Door confirmation correlation carries only the HomePASS Person UUID and current
  display-name snapshot; passkey credentials and NFC tag secrets remain excluded.

## [1.7.2] - 2026-08-11

### Changed

- New passkeys now use “{Property Name} Doors” as their visible password-manager
  username, with “HomePASS Doors” as the fallback when Property Name is blank.
- Retained the individual HomePASS User name as WebAuthn display metadata for account
  distinction without using it as the primary saved-passkey label.

### Security

- Continued using the stable Person UUID as the opaque WebAuthn user handle for
  credential identity and authorization.

## [1.7.1] - 2026-08-11

### Changed

- New passkeys now show the HomePASS User's friendly name in password managers instead
  of exposing their internal UUID as the visible username.

### Security

- Kept the stable Person UUID as the opaque WebAuthn user handle used for credential
  identity and authorization; the friendly name is presentation metadata only.

## [1.7.0] - 2026-08-11

### Added

- Revocable seven-day NTAG216 test-tag URLs for exercising the complete enrolled-passkey
  and real Door-unlock experience before permanent NTAG424 DNA tags are available.
- Door NFC setup controls for creating, copying, opening, checking, and revoking an
  NTAG216 test URL.
- A visibly labelled NTAG216 test variant of the public HomePASS Door access page.

### Security

- Kept static NTAG216 test URLs isolated from NTAG424 SUN verification and stored only
  their hashes; every unlock still requires an enrolled passkey, current Door policy,
  live Door capability, and a non-expired, non-revoked test tag.

## [1.6.1] - 2026-08-11

### Changed

- Removed the redundant “Managed by HomePASS” label from Door management.
- Made each user in a Door's Current Access list open that user's management page.

## [1.6.0] - 2026-08-11

### Added

- Inline Door-name editing from the Door management title using compact edit, save, and
  cancel controls.
- A dedicated per-Door NFC tag setup screen opened from a concise management action.

### Changed

- Reordered Door management around status, frequent actions, access, and destructive
  administration to make better use of space.
- Replaced product-specific NFC writer instructions with software- and hardware-neutral
  provisioning guidance.
- Versioned the NFC provisioning component alongside the main panel to prevent stale
  browser-cached instructions after upgrades.

## [1.5.1] - 2026-08-09

### Changed

- Enlarged the HomePASS logo on public NFC pages and simplified the unlock prompt.
- Added a Face ID symbol to the clearer “Click here to unlock the door” action.
- Versioned public NFC page assets so interface updates bypass stale browser caches.

## [1.5.0] - 2026-08-09

### Added

- Administrator-managed friendly Door names, which remain independent from Home Assistant
  entity names and update existing NFC access pages automatically.
- HomePASS-branded public NFC access pages showing the current Property and Door names.
- NFC-enabled badges on dashboard Door graphics and the full Door status graphic on the
  Door management page.
- A safe, non-operational NFC unlock-page preview for visual review.

### Changed

- Managed Door responses now include non-secret enabled NFC tag status and counts.
- Aligned the repository package and integration versions at 1.5.0.

## [1.4.0] - 2026-08-09

### Added

- Complete HomePASS panel for people, doors, access schedules, activity, settings,
  synchronization status, and administrative workflows.
- Home Assistant access-point discovery and management for locks and door/cover entities.
- Z-Wave lock synchronization, credential replacement, recovery, and activity attribution.
- Encrypted credential vault with staged-secret handling and redacted diagnostics.
- Secure NTAG424 DNA access using SUN/SDM validation, anti-replay counters, WebAuthn
  enrollment, user enrollment status, and revocation.
- Per-door NTAG424 DNA provisioning workflow with URL and key copy controls, downloadable
  setup JSON, and GoToTags writing guidance.
- HomePASS branding, browser favicon, NFC iconography, and responsive interface assets.

### Changed

- Expanded the integration service and translation schemas for the deployed management,
  access-control, synchronization, notification, and NFC actions.
- Aligned the repository package and integration versions at 1.4.0.

### Security

- NFC tag keys are generated and stored through the credential vault; the provisioning UI
  warns administrators to protect and delete exported setup packages after use.
- NTAG216 tags are excluded from the secure door profile, which requires NTAG424 DNA.

## [Unreleased]

### Added

- Production-quality Home Assistant config flow with single-instance setup and entry
  lifecycle tests.
- `homepass.ping` service for verifying that the integration is loaded.
- Typed person domain model with stable UUID identity.
- Versioned metadata repository using Home Assistant storage.
- Create/delete person actions.
- Capability-based lock driver contract.
- Initial architecture and security ADRs.
- CI, linting and unit-test configuration.

### Changed

- Validate and normalize the instance name during UI configuration.
- Keep the config-entry lifecycle free of business-service registration.

### Security

- PIN persistence is deliberately disabled pending approval of the credential-vault
  key-management ADR.
