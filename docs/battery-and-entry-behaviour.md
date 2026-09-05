# Battery health and entry behaviour

## Battery indicators

The dashboard places up to three upright battery indicators above the existing door status
symbol. The door artwork, online marker and NFC marker are unchanged. The order is lock,
contact sensor, then accessory. Only batteries exposed by Home Assistant are included; the
same battery source is never repeated. If several associated accessories have separate
batteries, the accessory position represents the most urgent reading, with entity identity
as the deterministic tie-breaker. Door details retain the individual readings.

Fill rounds to the nearest 10%. Green means above 30%, yellow means 11–30%, and red means
0–10%. A known battery without a usable reading is grey. Binary low-battery sensors show
status without inventing a percentage. There are no visible dashboard labels, percentage
text, tooltips or separate battery click targets; accessible text describes each reading.
The backend sends the same threshold values used by Activity and notifications to the panel.

Monitoring retains its quiet startup baseline and escalation-only notifications. Attribute
batteries now participate in monitoring as well as display. The persistent dashboard reading
makes an already-low battery visible after a restart without generating repeated pushes.

## Open Door

Home Assistant's `LockEntityFeature.OPEN` is the capability boundary. Provider branding never
creates Open support. HomePASS keeps three separate concepts:

- `supports_open`: live Home Assistant capability, refreshed with entity state.
- `open_enabled`: durable administrator permission, false for legacy doors.
- `entry_action`: `unlock` or `open`, used for HomePASS-dispatched PIN and NFC entry.

Open-capable doors require an explicit administrator decision during enrollment. Nuki's
paired local Bluetooth adapter can read `auto_unlatch` from its configuration to recommend
an entry action. The adapter reads only, caches the sanitized recommendation for five minutes,
and discards raw configuration. If the setting is unavailable, the administrator chooses.
Provider configuration is advisory and never enables Open without confirmation.

Existing doors retain Lock/Unlock until an administrator opens **Door behaviour**, chooses
controls and entry action, confirms, and saves. Disabling Open requires entry to use Unlock.
If live Open capability disappears, an Open entry request fails instead of silently sending
an insufficient Unlock command. Garage and strike control profiles retain their behaviour.

For manual app control, an enabled lock presents explicit **Unlock** and **Open Door** choices
on each operation, followed by the existing slide confirmation. Open dispatches `lock.open`.
An `unlocked` state does not confirm latch retraction: confirmation waits for the lock's
`open` state. Activity records latch release separately from a contact sensor reporting that
the door physically opened, retaining HomePASS command/credential attribution.

Nuki's native keypad and fingerprint reader execute on the lock itself, without asking
HomePASS to dispatch an entry command. Their locking action remains a Nuki app setting.
Onboarding explains this boundary; HomePASS does not rewrite unrelated Nuki hardware settings.
HomePASS-associated keypads and NFC use the confirmed HomePASS entry action automatically.

## Validation

Run the complete Python suite, frontend behaviour tests, Ruff lint, the strict mypy targets
in `.github/workflows/validate.yml`, and the repository privacy and Gitleaks checks. HACS and
hassfest run in GitHub Actions. Frontend tests run with Node 22 or later:

```sh
node --test tests/frontend/*.test.cjs
```

Use synthetic devices for visual checks. Do not test against a live lock or deploy a release
until validation is clean.
