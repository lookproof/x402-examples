"""Keep the files the release workflow checks consistent, so a release does not fail late."""

from __future__ import annotations

import re
from pathlib import Path

from security_txt_check import __version__

ROOT = Path(__file__).parent.parent


def test_version_is_semver() -> None:
    assert re.fullmatch(r"\d+\.\d+\.\d+", __version__)


def test_changelog_has_current_version() -> None:
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert re.search(rf"^## {re.escape(__version__)} ", changelog, re.M), "add a CHANGELOG.md entry"


def test_release_files_present() -> None:
    for name in ("action.yml", "README.md", "LICENSE", "CHANGELOG.md", ".github/workflows/release.yml"):
        assert (ROOT / name).is_file(), name


def test_workflow_actions_are_pinned() -> None:
    """Third-party actions run with our permissions, so pin them to a commit."""
    files = [ROOT / "action.yml", *sorted((ROOT / ".github" / "workflows").glob("*.yml"))]
    seen = 0
    for path in files:
        for ref in re.findall(r"^\s*-?\s*uses:\s*(\S+)", path.read_text(encoding="utf-8"), re.M):
            if ref.startswith("./"):
                continue
            seen += 1
            assert re.search(r"@[0-9a-f]{40}$", ref), f"{path.name}: {ref} is not pinned to a commit SHA"
    assert seen > 5
