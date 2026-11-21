"""Tests that removed things stay gone: the Claude pipeline (008) and the old app name (028)."""

import importlib.util
import re
import subprocess

import pytest

from subbed.config import REPO_ROOT

REMOVED = [
    "anthropic",
    "fugashi",
    "unidic_lite",
    "subbed.claude",
    "subbed.prompt",
    "subbed.hiragana",
    "subbed.readings",
    "subbed.romaji",
    "subbed.japanese_analyzer",
]

# Built from two parts so this file does not match itself.
OLD_APP_NAME = "ly" + "rx"
# Numbered specs record past decisions under the old name and stay as written.
SPEC_FOLDER = re.compile(r"^specs/\d{3}-")


@pytest.mark.parametrize("module", REMOVED)
def test_ac12_removed_module_is_not_installed(module: str) -> None:
    assert importlib.util.find_spec(module) is None


def tracked_files() -> list[str]:
    listing = subprocess.run(
        ["git", "ls-files"], cwd=REPO_ROOT, capture_output=True, text=True, check=True
    )
    return [path for path in listing.stdout.splitlines() if not SPEC_FOLDER.match(path)]


def mentions_old_name(path: str) -> bool:
    if OLD_APP_NAME in path.lower():
        return True
    file = REPO_ROOT / path
    if not file.is_file():
        return False
    content = file.read_bytes()
    is_binary = b"\0" in content
    return not is_binary and OLD_APP_NAME.encode() in content.lower()


def test_spec028_ac1_old_app_name_is_gone() -> None:
    assert [path for path in tracked_files() if mentions_old_name(path)] == []
