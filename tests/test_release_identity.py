"""Prevent release metadata from diverging from About and NFC cache identity."""

import json
from pathlib import Path
import tomllib

from custom_components.homepass.const import VERSION


def test_release_versions_match_runtime_identity() -> None:
    """A released package must advertise one version everywhere it is consumed."""
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads((root / "custom_components/homepass/manifest.json").read_text())
    project = tomllib.loads((root / "pyproject.toml").read_text())
    assert VERSION == manifest["version"] == project["project"]["version"]
