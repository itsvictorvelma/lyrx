"""Tests for lines.py: LRCLIB's plain lyrics into trimmed lines, one blank line between verses."""

import pytest

from lyrx.lyrics.lines import read_lyrics


def test_every_kind_of_line_ending_is_one_line_break() -> None:
    assert read_lyrics("夜の月\r\n星の歌\r風の声\n空") == ["夜の月", "星の歌", "風の声", "空"]


def test_each_line_is_trimmed_and_spaces_inside_are_kept() -> None:
    assert read_lyrics("  君の 声が  \n\u3000遠く ひびく\t") == ["君の 声が", "遠く ひびく"]


def test_blank_runs_become_one_and_blank_lines_at_the_ends_are_dropped() -> None:
    lyrics = "\n \n夜の月\n\n\n  \n星の歌\n\n風の声\n\n"
    assert read_lyrics(lyrics) == ["夜の月", "", "星の歌", "", "風の声"]


def test_decomposed_kana_is_composed() -> None:
    assert read_lyrics("\u304b\u3099") == ["\u304c"]


@pytest.mark.parametrize("lyrics", ["", "   ", "\n\n", " \r\n\t\r \n", "\u3000\n "])
def test_empty_or_blank_lyrics_give_no_lines(lyrics: str) -> None:
    assert read_lyrics(lyrics) == []
