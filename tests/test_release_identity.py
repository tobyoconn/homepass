"""Prevent release metadata from diverging from About and NFC cache identity."""

import json
from importlib.metadata import requires
from pathlib import Path
import tomllib

from packaging.requirements import Requirement

from custom_components.homepass.const import VERSION


def test_release_versions_match_runtime_identity() -> None:
    """A released package must advertise one version everywhere it is consumed."""
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads((root / "custom_components/homepass/manifest.json").read_text())
    project = tomllib.loads((root / "pyproject.toml").read_text())
    assert VERSION == manifest["version"] == project["project"]["version"]


def test_crypto_requirement_is_owned_by_home_assistant() -> None:
    """Never override Core's crypto dependency in runtime or validation installs."""
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads((root / "custom_components/homepass/manifest.json").read_text())
    core = {Requirement(value).name for value in requires("homeassistant") or []}
    runtime = {Requirement(value).name for value in manifest["requirements"]}
    development = {
        Requirement(line)
        for line in (root / "requirements-dev.txt").read_text().splitlines()
        if line.strip() and not line.startswith("#")
    }
    assert "cryptography" in core
    assert "cryptography" not in runtime
    assert "cryptography" not in {value.name for value in development}
