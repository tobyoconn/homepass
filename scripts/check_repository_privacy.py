#!/usr/bin/env python3
"""Reject installation-specific artifacts and identifiers from HomePASS commits."""

from __future__ import annotations

import argparse
import ipaddress
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence


SYNTHETIC_PINS = frozenset(
    {
        "0000",
        "000000",
        "012345",
        "111111",
        "123456",
        "222222",
        "2468",
        "292929",
        "34567",
        "345670",
        "654321",
    }
)
SYNTHETIC_MACS = frozenset(
    {
        "00:11:22:33:44:55",
        "02:00:00:00:00:00",
        "AA:BB:CC:DD:EE:FF",
    }
)
SYNTHETIC_LABEL_WORDS = frozenset(
    {
        "demo",
        "example",
        "fixture",
        "homepass",
        "sample",
        "synthetic",
        "test",
    }
)

TEXT_EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@([A-Z0-9.-]+\.[A-Z]{2,})\b", re.IGNORECASE)
TEXT_IPV4 = re.compile(r"(?<![\w.])(?:\d{1,3}\.){3}\d{1,3}(?![\w.])")
TEXT_MAC = re.compile(r"\b(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}\b")
TEXT_NABU_HOST = re.compile(r"\b[a-z0-9]{12,}\.ui\.nabu\.casa\b", re.IGNORECASE)
TEXT_NUKI_NAME = re.compile(r"\bNuki_([0-9A-Fa-f]{6,})\b")
TEXT_HA_ID = re.compile(
    r"\b(?:config_entry_id|device_registry_id|entity_registry_id|ha_device_id|"
    r"ha_config_entry_id)\b[^\n]{0,80}\b(?:[0-9a-f]{32}|"
    r"[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12})\b",
    re.IGNORECASE,
)
TEXT_NFC_SECRET = re.compile(
    r"\b(?:nfc_uid|tag_uid|nfc_key|enrollment_secret|credential_secret)\b"
    r"[^\n]{0,40}[\"']([A-Za-z0-9+/=_:-]{12,})[\"']",
    re.IGNORECASE,
)
TEXT_PIN = re.compile(
    r"\b(?:pin|security_pin|entry_code)\b[^\n]{0,40}?(?:[\"'](\d{4,8})[\"']|(?<!\d)(\d{4,8})(?!\d))",
    re.IGNORECASE,
)
TEXT_CONTEXT_LABEL = re.compile(
    r"\b(?:property_name|site_name|deployment_name|installation_name|home_name|"
    r"owner_name|resident_name|person_name)\b\s*(?:=|:)\s*[\"']([^\"']+)[\"']",
    re.IGNORECASE,
)

EXAMPLE_EMAIL_DOMAINS = frozenset(
    {"example.com", "example.net", "example.org", "users.noreply.github.com"}
)
SENSITIVE_BASENAMES = frozenset(
    {
        ".env",
        "core.config_entries",
        "core.device_registry",
        "core.entity_registry",
        "credentials.json",
        "home-assistant.log",
        "home-assistant_v2.db",
        "known_devices.yaml",
        "secrets.yaml",
        "tokens.json",
    }
)
SENSITIVE_DIRS = frozenset(
    {
        ".deploy",
        ".homepass",
        ".storage",
        "deployment-records",
        "deployment-profiles",
        "deployments",
        "local-profiles",
        "local-state",
        "logs",
        "profiles",
    }
)
SENSITIVE_ROOT_FILES = frozenset(
    {
        ".ha_version",
        "automations.yaml",
        "configuration.yaml",
        "scenes.yaml",
        "scripts.yaml",
    }
)
SENSITIVE_SUFFIXES = (
    ".cer",
    ".credential",
    ".credentials",
    ".crt",
    ".der",
    ".gototags",
    ".jks",
    ".key",
    ".keystore",
    ".log",
    ".p12",
    ".pem",
    ".pfx",
)


@dataclass(frozen=True, slots=True)
class Finding:
    path: str
    rule: str
    line: int | None = None

    def render(self) -> str:
        location = self.path if self.line is None else f"{self.path}:{self.line}"
        return f"{location}: [{self.rule}] private or installation-specific data is prohibited"


def _is_private_ipv4(value: str) -> bool:
    try:
        address = ipaddress.ip_address(value)
    except ValueError:
        return False
    return isinstance(address, ipaddress.IPv4Address) and address.is_private


def _is_synthetic_label(value: str) -> bool:
    words = {word.casefold() for word in re.findall(r"[A-Za-z]+", value)}
    return bool(words & SYNTHETIC_LABEL_WORDS)


def _path_findings(path: str) -> list[Finding]:
    normalized = path.replace("\\", "/")
    parts = normalized.casefold().split("/")
    basename = parts[-1]
    findings: list[Finding] = []

    if any(part in SENSITIVE_DIRS for part in parts[:-1]):
        findings.append(Finding(path, "private-directory"))
    if basename in SENSITIVE_BASENAMES:
        findings.append(Finding(path, "sensitive-file"))
    if len(parts) == 1 and basename in SENSITIVE_ROOT_FILES:
        findings.append(Finding(path, "home-assistant-configuration"))
    if basename.startswith(".env.") and basename != ".env.example":
        findings.append(Finding(path, "environment-file"))
    if basename.startswith(("credentials.", "secrets.", "tokens.")):
        findings.append(Finding(path, "credential-file"))
    if basename.endswith(SENSITIVE_SUFFIXES):
        findings.append(Finding(path, "credential-or-runtime-file"))
    if basename.startswith(("home-assistant.log", "home-assistant_v2.db")):
        findings.append(Finding(path, "home-assistant-runtime"))
    return findings


def scan_text(path: str, text: str, private_terms: Sequence[str] = ()) -> list[Finding]:
    findings: list[Finding] = []
    normalized_terms = tuple(term.casefold() for term in private_terms if term.strip())

    for line_number, line in enumerate(text.splitlines(), start=1):
        for match in TEXT_IPV4.finditer(line):
            if _is_private_ipv4(match.group(0)):
                findings.append(Finding(path, "private-ipv4", line_number))
                break

        if TEXT_NABU_HOST.search(line):
            findings.append(Finding(path, "deployment-hostname", line_number))

        for match in TEXT_EMAIL.finditer(line):
            if match.group(1).casefold() not in EXAMPLE_EMAIL_DOMAINS:
                findings.append(Finding(path, "personal-email", line_number))
                break

        for match in TEXT_MAC.finditer(line):
            if match.group(0).upper() not in SYNTHETIC_MACS:
                findings.append(Finding(path, "hardware-identifier", line_number))
                break

        for match in TEXT_NUKI_NAME.finditer(line):
            if match.group(1).upper() not in {"00000000", "DEADBEEF"}:
                findings.append(Finding(path, "nuki-identifier", line_number))
                break

        if TEXT_HA_ID.search(line):
            findings.append(Finding(path, "home-assistant-registry-id", line_number))

        if TEXT_NFC_SECRET.search(line):
            findings.append(Finding(path, "nfc-secret-or-uid", line_number))

        pin_match = TEXT_PIN.search(line)
        if pin_match:
            pin = pin_match.group(1) or pin_match.group(2)
            if pin not in SYNTHETIC_PINS:
                findings.append(Finding(path, "literal-pin", line_number))

        label_match = TEXT_CONTEXT_LABEL.search(line)
        if label_match and not _is_synthetic_label(label_match.group(1)):
            findings.append(Finding(path, "production-label", line_number))

        folded_line = line.casefold()
        if any(term in folded_line for term in normalized_terms):
            findings.append(Finding(path, "local-private-term", line_number))

    return findings


def scan_paths(
    root: Path, paths: Iterable[str], private_terms: Sequence[str] = ()
) -> list[Finding]:
    findings: list[Finding] = []
    for path in sorted(set(paths)):
        findings.extend(_path_findings(path))
        candidate = root / path
        try:
            data = candidate.read_bytes()
        except OSError:
            continue
        if b"\0" in data:
            continue
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            continue
        findings.extend(scan_text(path, text, private_terms))
    return findings


def _git_tracked_files(root: Path) -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "-z", "--cached"],
        cwd=root,
        check=True,
        capture_output=True,
    )
    return [item.decode("utf-8") for item in result.stdout.split(b"\0") if item]


def _load_private_terms(root: Path, configured_path: str | None) -> list[str]:
    terms_path = Path(configured_path) if configured_path else root / ".homepass/privacy-terms.txt"
    if not terms_path.is_absolute():
        terms_path = root / terms_path
    if not terms_path.exists():
        return []
    return [
        line.strip()
        for line in terms_path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--private-terms",
        help="optional ignored local file containing one private label or hostname per line",
    )
    args = parser.parse_args(argv)
    root = args.root.resolve()

    try:
        paths = _git_tracked_files(root)
    except (OSError, subprocess.CalledProcessError) as err:
        print(f"HomePASS privacy check could not list tracked files: {err}", file=sys.stderr)
        return 2

    findings = scan_paths(root, paths, _load_private_terms(root, args.private_terms))
    if findings:
        print("HomePASS repository privacy check failed:", file=sys.stderr)
        for finding in findings:
            print(f"  {finding.render()}", file=sys.stderr)
        print(
            "Replace live values with synthetic fixtures; never allowlist a real secret "
            "or identifier.",
            file=sys.stderr,
        )
        return 1

    print(f"HomePASS repository privacy check passed ({len(paths)} tracked files scanned).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
