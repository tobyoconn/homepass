# HomePASS Development Setup for macOS

| Field | Value |
| --- | --- |
| Status | Active |
| Version | 1.1 |
| Owner | HomePASS contributors |
| Last updated | 2026-10-09 |

This guide creates an isolated local environment for developing and testing HomePASS. Do
not use a production Home Assistant configuration or real access credentials for development.

## 1. Install macOS prerequisites

Install the Xcode Command Line Tools and [Homebrew](https://brew.sh/):

```bash
xcode-select --install
```

After Homebrew is available, install Python and the native tools commonly needed by Home
Assistant dependencies:

```bash
brew update
brew install python3 autoconf ffmpeg cmake make
```

Some Python packages contain Rust extensions. Install Rust only if dependency installation
reports that `rustc` or `cargo` is missing:

```bash
brew install rust
```

HomePASS requires Python 3.14 or later. Current Home Assistant development may require a
newer patch release, so confirm the requirement in the
[Home Assistant development-environment guide](https://developers.home-assistant.io/docs/development_environment/)
before creating the environment:

```bash
python3 --version
```

If Homebrew installed multiple Python versions, invoke the executable for the required
version explicitly in the following steps.

## 2. Create a virtual environment

From the HomePASS repository root, create the environment outside the repository so it
cannot be committed accidentally:

```bash
python3 -m venv "$HOME/.venvs/homepass"
source "$HOME/.venvs/homepass/bin/activate"
python -m pip install --upgrade pip setuptools wheel
```

Activate it in each new terminal session:

```bash
source "$HOME/.venvs/homepass/bin/activate"
```

Verify that `python` and `pip` resolve inside the environment:

```bash
which python
python --version
python -m pip --version
```

## 3. Install Home Assistant and development tools

Install the repository's pinned validation environment:

```bash
python -m pip install -r requirements-dev.txt
python -m pip install pre-commit
```

`pytest-homeassistant-custom-component` supplies Home Assistant's test fixtures for custom
integrations, including the `hass` fixture used by HomePASS tests. Its pinned version selects
the unit-test Home Assistant version. This reproducible baseline is separate from the current
stable/beta startup checks below; do not treat a passing pinned suite as proof of compatibility
with a newer Core release. Do not add a separate pin for Core-owned dependencies.

Confirm the installation:

```bash
hass --version
pytest --version
ruff --version
pre-commit --version
```

## 4. Run the test suite

Run all tests from the repository root:

```bash
python -m pytest
```

Run a focused file while developing:

```bash
python -m pytest tests/test_config_flow.py -vv
```

The default pytest paths and options are defined in `pyproject.toml`.

## 5. Run Ruff

Check lint rules and formatting without changing files:

```bash
ruff check .
ruff format --check .
```

Apply safe lint fixes and formatting when intended:

```bash
ruff check . --fix
ruff format .
```

HomePASS targets Python 3.14 and a 100-character line length. Home Assistant also uses Ruff
for formatting; see its [style guidelines](https://developers.home-assistant.io/docs/development_guidelines/).

## 6. Configure pre-commit

HomePASS includes local privacy and Gitleaks hooks. Install and run them with:

```bash
pre-commit install
pre-commit run --all-files
```

The first run downloads the pinned Gitleaks hook. See
[`docs/REPOSITORY_PRIVACY.md`](docs/REPOSITORY_PRIVACY.md) for the data-handling policy, direct
scanner commands, and safe false-positive handling.

## 7. Run hassfest

Hassfest validates Home Assistant integration metadata, translations, and service schemas.
Install and start [Docker Desktop for Mac](https://docs.docker.com/desktop/setup/install/mac-install/),
then verify Docker is available:

```bash
docker version
```

From the repository root, run the official hassfest image:

```bash
docker run --rm \
  -v "$PWD:/github/workspace" \
  ghcr.io/home-assistant/hassfest:latest
```

The first run downloads the image. Keep Docker Desktop running while hassfest executes.
Home Assistant documents hassfest validation for custom integrations in its
[developer guidance](https://developers.home-assistant.io/blog/2020/04/16/hassfest/).

## 8. Start a disposable Home Assistant instance

First run the same real-startup compatibility check used by CI:

```bash
docker run --rm --pull always --entrypoint python \
  -v "$PWD:/work:ro" -w /work \
  ghcr.io/home-assistant/home-assistant:stable scripts/check_ha_compatibility.py
docker run --rm --pull always --entrypoint python \
  -v "$PWD:/work:ro" -w /work \
  ghcr.io/home-assistant/home-assistant:beta scripts/check_ha_compatibility.py
```

These checks use the image's Python and Home Assistant versions, including the real dependency
installer and constraints. The repository is mounted read-only; configuration and vault data
are temporary and synthetic. No ports, host devices, production configuration, or credentials
are passed through. The logs record the exact Core and cryptography versions tested.

For interactive development:

Use a separate configuration directory and link the working integration into it:

```bash
export HOMEPASS_HA_CONFIG="$HOME/.homeassistant-homepass-dev"
mkdir -p "$HOMEPASS_HA_CONFIG/custom_components"
ln -sfn \
  "$PWD/custom_components/homepass" \
  "$HOMEPASS_HA_CONFIG/custom_components/homepass"
hass -c "$HOMEPASS_HA_CONFIG"
```

Open `http://localhost:8123`, complete the temporary Home Assistant onboarding, and add
HomePASS from **Settings → Devices & services**. Stop the server with `Control-C`.

On macOS, Home Assistant may require Bluetooth permission for the terminal application. USB
and other host hardware can also behave differently in containerized environments.

## 9. Before opening a pull request

Run the complete local check set:

```bash
python -m pytest
ruff check .
ruff format --check .
python3 scripts/check_repository_privacy.py
pre-commit run --all-files
docker run --rm -v "$PWD:/github/workspace" ghcr.io/home-assistant/hassfest:latest
```

Review the [Home Assistant development checklist](https://developers.home-assistant.io/docs/development_checklist/)
for any additional requirements relevant to the change.

## Troubleshooting

- Recreate the virtual environment after changing Python versions.
- Confirm the environment is active if `pytest`, `ruff`, or `hass` is not found.
- Install Rust if a package must compile `cryptography`, `orjson`, or another Rust extension.
- Update `pip`, `setuptools`, and `wheel` before investigating native build failures.
- Check Docker Desktop file-sharing permissions if hassfest cannot read the repository.
