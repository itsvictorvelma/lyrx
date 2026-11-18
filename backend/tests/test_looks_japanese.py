"""Tests for looks_japanese.py: a quarter of the lines with kana makes lyrics Japanese."""

import pytest

from lyrx.looks_japanese import looks_japanese


@pytest.mark.parametrize(
    ("lines", "expected"),
    [
        (["君の声が", "", "We sing", "all night", "long"], True),
        (["君の声", "We sing", "all night", "long", "and on"], False),
        (["我爱你", "天空很蓝"], False),
        (["kimi no koe ga"], False),
        ([], False),
    ],
    ids=["one-in-four", "kanji-only-line", "chinese", "romaji-only", "empty"],
)
def test_looks_japanese(lines: list[str], expected: bool) -> None:
    assert looks_japanese(lines) is expected
