# Repository privacy and secret handling

HomePASS source, tests, documentation, issues, and pull requests must never contain data copied
from a real home or access-control installation. This includes names or personal email addresses;
property labels; internal addresses or deployment hostnames; Home Assistant registry identifiers;
lock, keypad, NFC, or other hardware identifiers; PINs; NFC keys or enrollment data; API keys,
passwords, bearer tokens, webhooks, credentials, logs, diagnostics, backups, or runtime state.

Use obviously synthetic fixtures such as `Example Home`, `resident@example.com`, documentation IP
addresses from the RFC 5737 ranges, and the synthetic identifiers already used by the tests. A
generic Home Assistant entity ID is acceptable when it is not copied from a live installation and
does not expose a person, address, or property.

## Where local data belongs

Keep deployment profiles, deployment records, logs, credentials, and private review terms outside
the repository. If a tool must write below the checkout, use the ignored `.homepass/` directory.
For example, private property labels and hostnames can be placed one per line in
`.homepass/privacy-terms.txt`; the privacy scanner reads that file locally without printing the
matched value. Home Assistant runtime data belongs in the instance configuration directory, never
in this repository.

## Run the checks locally

Run the HomePASS-specific check:

```bash
python3 scripts/check_repository_privacy.py
```

Run Gitleaks 8.30.1 or newer against the current tree and Git history:

```bash
gitleaks dir . --config .gitleaks.toml --redact
gitleaks git . --config .gitleaks.toml --redact
```

Developers using pre-commit can install both checks:

```bash
pre-commit install
pre-commit run --all-files
```

CI runs the HomePASS privacy policy and Gitleaks on every push and pull request, and on a weekly
schedule. A failure names the file, line, and rule while avoiding disclosure of the matched value.

## False positives and real exposures

First replace a suspicious test value with a clearly synthetic fixture. Do not add a real secret,
identifier, hostname, address, name, or property label to an allowlist. If a scanner exclusion is
unavoidable, constrain it to the exact synthetic fixture path and detector rule, explain why the
fixture is synthetic next to the exclusion, and have it reviewed.

Deleting a committed secret does not make it safe: it remains available in Git history and in
clones. Rotate or revoke any real secret immediately if it is ever committed, even if the file or
line is later deleted. Coordinate any separate history-remediation decision only after rotation;
do not treat history rewriting as a substitute for revocation.
