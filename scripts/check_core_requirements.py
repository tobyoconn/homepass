"""Reject integration requirements that override Home Assistant Core dependencies."""

from collections.abc import Iterable
from importlib.metadata import requires, version
import json
from pathlib import Path

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name


def core_owned_requirements(runtime: Iterable[str], core: Iterable[str]) -> set[str]:
    """Find active requirements whose versions must be managed by Core."""

    def active_names(values: Iterable[str]) -> set[str]:
        requirements = (Requirement(value) for value in values)
        return {
            canonicalize_name(requirement.name)
            for requirement in requirements
            if requirement.marker is None or requirement.marker.evaluate({"extra": ""})
        }

    return active_names(runtime) & active_names(core)


def check_core_requirements(root: Path) -> None:
    """Check against the installed Core version, not a hard-coded package list."""
    manifest = json.loads((root / "custom_components/homepass/manifest.json").read_text())
    conflicts = core_owned_requirements(manifest["requirements"], requires("homeassistant") or [])
    if conflicts:
        raise RuntimeError(
            "Remove requirements already supplied by Home Assistant Core: "
            + ", ".join(sorted(conflicts))
        )
    print(f"Dependency ownership passed for Home Assistant {version('homeassistant')}", flush=True)


if __name__ == "__main__":
    check_core_requirements(Path(__file__).resolve().parents[1])
