"""Tests for the repository-specific privacy scanner."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

SCRIPT_PATH = Path(__file__).parents[1] / "scripts/check_repository_privacy.py"
SPEC = importlib.util.spec_from_file_location("check_repository_privacy", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
PRIVACY = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = PRIVACY
SPEC.loader.exec_module(PRIVACY)


def _rules(text: str, path: str = "tests/fixture.json") -> set[str]:
    return {finding.rule for finding in PRIVACY.scan_text(path, text)}


def test_rejects_private_ip_and_remote_home_assistant_hostname() -> None:
    private_ip = "192." + "168.40.12"
    assert "private-ipv4" in _rules(f'host = "{private_ip}"')
    remote_host = "abcdefghijklmnop.ui." + "nabu.casa"
    assert "deployment-hostname" in _rules(f'origin = "https://{remote_host}"')


def test_rejects_live_looking_home_assistant_and_nuki_ids() -> None:
    registry_id = "0123456789abcdef" * 2
    assert "home-assistant-registry-id" in _rules(f'config_entry_id = "{registry_id}"')
    nuki_name = "Nuki_" + "12AB34CD"
    assert "nuki-identifier" in _rules(f'name = "{nuki_name}"')
    hardware_address = ":".join(("12", "34", "56", "78", "9A", "BC"))
    assert "hardware-identifier" in _rules(f'address = "{hardware_address}"')


def test_accepts_documented_synthetic_fixtures() -> None:
    findings = PRIVACY.scan_text(
        "tests/fixture.py",
        "\n".join(
            (
                'address = "AA:BB:CC:DD:EE:FF"',
                'security_pin = "123456"',
                'property_name = "Example Home"',
                'email = "resident@example.com"',
                'name = "Nuki_DEADBEEF"',
            )
        ),
    )
    assert findings == []


def test_rejects_sensitive_paths() -> None:
    assert PRIVACY._path_findings(".storage/core.config_entries")
    assert PRIVACY._path_findings("deployments/site/profile.yaml")
    assert PRIVACY._path_findings("profiles/production.yaml")
    assert PRIVACY._path_findings("configuration.yaml")
    assert PRIVACY._path_findings("secrets.yaml")
    assert PRIVACY._path_findings("logs/homepass.log")


def test_optional_local_terms_are_not_echoed() -> None:
    findings = PRIVACY.scan_text(
        "notes.txt", "This fixture names a protected residence.", ["protected residence"]
    )
    assert [finding.rule for finding in findings] == ["local-private-term"]
    assert "protected residence" not in findings[0].render()
