"""Presentation-safe application service for HomePASS release identity."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict

from homeassistant.const import __version__ as HOME_ASSISTANT_VERSION

from ..const import STORAGE_SCHEMA_VERSION, VERSION
from .property_settings import PropertySettingsService

_GIT_COMMIT_PATTERN = re.compile(r"[0-9a-f]{40}")


def developer_git_commit(repository_root: Path | None = None) -> str | None:
    """Read a commit only when HomePASS is running from a Git source checkout."""
    root = (repository_root or Path(__file__).resolve().parents[3]).resolve()
    if not (root / "pyproject.toml").is_file():
        return None
    git_directory = root / ".git"
    try:
        if git_directory.is_file():
            marker = git_directory.read_text(encoding="utf-8").strip()
            if not marker.startswith("gitdir: "):
                return None
            candidate = Path(marker.removeprefix("gitdir: "))
            git_directory = candidate if candidate.is_absolute() else root / candidate
        head = (git_directory / "HEAD").read_text(encoding="utf-8").strip()
        if head.startswith("ref: "):
            head = (git_directory / head.removeprefix("ref: ")).read_text(encoding="utf-8").strip()
        return head if _GIT_COMMIT_PATTERN.fullmatch(head) else None
    except OSError:
        return None


class AboutPresentationData(TypedDict):
    """Homeowner-safe release and installation identity."""

    product_name: str
    tagline: str
    version: str
    property_name: str
    home_assistant_version: str
    database_schema_version: int
    created_by: str
    copyright: str
    git_commit: str | None


@dataclass(frozen=True, slots=True)
class AboutView:
    """Immutable About presentation."""

    property_name: str
    git_commit: str | None = None

    def to_dict(self) -> AboutPresentationData:
        """Return the dedicated About action payload."""
        return {
            "product_name": "HomePASS",
            "tagline": "Secure Access Management for Home Assistant",
            "version": VERSION,
            "property_name": self.property_name,
            "home_assistant_version": HOME_ASSISTANT_VERSION,
            "database_schema_version": STORAGE_SCHEMA_VERSION,
            "created_by": "HomePASS Contributors",
            "copyright": "© 2026 HomePASS Contributors",
            "git_commit": self.git_commit[:8] if self.git_commit else None,
        }


class AboutService:
    """Load release identity and the current homeowner-owned Property Name."""

    def __init__(
        self,
        property_settings: PropertySettingsService,
        *,
        git_commit: str | None = None,
    ) -> None:
        self._property_settings = property_settings
        self._git_commit = (
            git_commit if git_commit and _GIT_COMMIT_PATTERN.fullmatch(git_commit) else None
        )

    async def load(self) -> AboutView:
        """Return one presentation-safe About view."""
        property_view = await self._property_settings.load()
        return AboutView(property_view.settings.property_name, self._git_commit)


__all__ = [
    "AboutPresentationData",
    "AboutService",
    "AboutView",
    "developer_git_commit",
]
