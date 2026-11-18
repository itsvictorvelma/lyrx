"""Tests for AC-12: the Claude pipeline and the local reading code are gone for good."""

import importlib.util

import pytest

REMOVED = [
    "anthropic",
    "fugashi",
    "unidic_lite",
    "lyrx.claude",
    "lyrx.prompt",
    "lyrx.hiragana",
    "lyrx.readings",
    "lyrx.romaji",
    "lyrx.japanese_analyzer",
    "lyrx.translation",
]


@pytest.mark.parametrize("module", REMOVED)
def test_ac12_removed_module_is_not_installed(module: str) -> None:
    assert importlib.util.find_spec(module) is None
