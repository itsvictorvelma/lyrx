"""Tests for lines.py: lyrics into trimmed lines, and each line's start time (spec 012)."""

import pytest

from subbed.lyrics.lines import read_lyrics, read_timed_lines, start_times


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


# Start times (spec 012). Invented lines.

LINES = ["夜の月", "星の歌", "", "風の声"]
SYNCED = "[00:01.00] 夜の月\n[00:04.50] 星の歌\n[00:09.00]\n[00:10.25] 風の声\n"


def test_ac1_timed_lines_that_match_give_every_lyric_line_its_start() -> None:
    assert start_times(LINES, SYNCED) == [1000, 4500, None, 10250]


@pytest.mark.parametrize(
    "synced",
    [
        None,
        "",
        "[00:01.00] 夜の月\n[00:04.50] 別の歌\n[00:10.25] 風の声",
        "[00:01.00] 夜の月\n[00:10.25] 風の声",
        "[00:05.00] 夜の月\n[00:04.50] 星の歌\n[00:10.25] 風の声",
        "夜の月\n星の歌\n風の声",
    ],
    ids=["none", "empty", "different-text", "missing-line", "time-goes-back", "no-tags"],
)
def test_ac2_timings_that_do_not_fit_give_no_line_a_start(synced: str | None) -> None:
    assert start_times(LINES, synced) == [None, None, None, None]


@pytest.mark.parametrize(
    ("tag", "milliseconds"),
    [("[1:02]", 62000), ("[01:02.5]", 62500), ("[01:02.50]", 62500), ("[01:02.500]", 62500)],
)
def test_ac3_every_tag_form_parses(tag: str, milliseconds: int) -> None:
    assert read_timed_lines(f"{tag} 夜の月") == [(milliseconds, "夜の月")]


@pytest.mark.parametrize("line", ["[1:2] 夜", "[aa:02.00] 夜", "[01:60.00] 夜", "夜 [01:02.00]"])
def test_ac3_a_malformed_or_misplaced_tag_is_skipped(line: str) -> None:
    assert read_timed_lines(line) == []
