"""Tests for the hiragana-only reading check and the kana-kept comparison. Invented lines only."""

import time

import pytest

from lyrx.readings import reading_is_allowed, reading_keeps_kana, tidy_reading

# Rule 5, the hard check (AC-17): only hiragana, ー, single spaces, and characters in the original.


def test_ac17_plain_hiragana_reading_with_single_spaces_is_allowed() -> None:
    assert reading_is_allowed("君がいる", "きみ が いる")


def test_ac17_kanji_not_in_the_original_is_rejected() -> None:
    assert not reading_is_allowed("君がいる", "きみ が 居る")


def test_ac17_latin_letter_not_in_the_original_is_rejected() -> None:
    assert not reading_is_allowed("君がいる", "kimi が いる")


def test_ac17_kanji_that_is_in_the_original_passes_the_hard_check() -> None:
    """AC-17 rejects only a kanji 'that is not in the original line'."""
    assert reading_is_allowed("君がいる", "君 が いる")


@pytest.mark.parametrize(
    ("original", "reading"),
    [
        ("夢 Go", "ゆめ Go"),
        ("2人で", "2 ふたり で"),
        ("夢、Go!", "ゆめ、 Go!"),
        ("「空」", "「そら」"),
        ("空?", "そら?"),
    ],
)
def test_ac17_latin_digit_or_punctuation_in_the_original_is_allowed(
    original: str, reading: str
) -> None:
    assert reading_is_allowed(original, reading)


@pytest.mark.parametrize(
    ("original", "reading"),
    [
        ("人で", "2 ふたり で"),
        ("君がいる", "きみ が いる。"),
        ("君がいる", "きみ が いる!"),
    ],
)
def test_ac17_digit_or_punctuation_not_in_the_original_is_rejected(
    original: str, reading: str
) -> None:
    assert not reading_is_allowed(original, reading)


def test_ac17_long_mark_is_allowed_even_when_not_in_the_original() -> None:
    assert reading_is_allowed("光る", "ひかーる")


def test_ac17_small_kana_are_hiragana_and_allowed() -> None:
    assert reading_is_allowed("一緒", "いっしょ")


def test_ac17_katakana_not_in_the_original_is_rejected() -> None:
    assert not reading_is_allowed("君", "キミ")


def test_ac17_two_spaces_in_a_row_are_rejected() -> None:
    assert not reading_is_allowed("君がいる", "きみ  が いる")


def test_ac17_tab_not_in_the_original_is_rejected() -> None:
    assert not reading_is_allowed("君がいる", "きみ\tが いる")


def test_ac17_katakana_that_is_in_the_original_passes_the_hard_check() -> None:
    assert reading_is_allowed("ココロ", "ココロ")


@pytest.mark.parametrize(
    ("original", "reading"),
    [
        ("君がいる", " きみ が いる"),
        ("君がいる", "きみ が いる "),
        ("君がいる", "きみ\u3000が いる"),
    ],
)
def test_ac17_leading_trailing_or_full_width_space_is_rejected(original: str, reading: str) -> None:
    assert not reading_is_allowed(original, reading)


@pytest.mark.parametrize(
    ("original", "reading"),
    [
        ("君  が", "きみ  が"),
        (" 君が", " きみ が"),
        ("君が ", "きみ が "),
        ("君\tが", "きみ\tが"),
        ("君\u3000が", "きみ\u3000が"),
    ],
)
def test_ac17_whitespace_other_than_a_single_inner_space_is_rejected_even_if_in_the_original(
    original: str, reading: str
) -> None:
    assert not reading_is_allowed(original, reading)


@pytest.mark.parametrize("reading", ["ときゝ", "すゞ"])
def test_ac17_hiragana_iteration_marks_count_as_hiragana(reading: str) -> None:
    assert reading_is_allowed("時", reading)


# Tidying the reading before the checks (AC-17): NFC and ASCII spaces only.


def test_ac17_tidy_trims_and_collapses_ascii_spaces() -> None:
    assert tidy_reading("  きみ   が いる ") == "きみ が いる"


@pytest.mark.parametrize("reading", ["きみ\tが", "きみ\u3000が", "\tきみ", "きみ\u3000"])
def test_ac17_tidy_leaves_tabs_and_full_width_spaces_alone(reading: str) -> None:
    assert tidy_reading(reading) == reading


def test_ac17_tidy_normalizes_decomposed_kana_to_nfc() -> None:
    assert tidy_reading("\u304b\u3099") == "\u304c"


@pytest.mark.parametrize("reading", ["きみ が いる", "ココロ 君 Go!", ""])
def test_ac17_tidy_changes_nothing_else(reading: str) -> None:
    assert tidy_reading(reading) == reading


# Rule 6, kana kept (unit part of AC-18): a warning, so the function only answers yes or no.


def test_ac18_spec_example_reading_that_keeps_the_kana_passes() -> None:
    assert reading_keeps_kana("君がいる", "きみ が いる")


def test_ac18_spec_example_changed_kana_fails() -> None:
    assert not reading_keeps_kana("君がいる", "きみ が いた")


def test_ac18_spec_example_digit_missing_from_the_reading_fails() -> None:
    assert not reading_keeps_kana("2人で", "ふたり で")


def test_ac18_digit_kept_in_order_passes() -> None:
    assert reading_keeps_kana("2人で", "2 ふたり で")


@pytest.mark.parametrize(
    ("original", "reading"),
    [
        ("昨日の空", "きのう の そら"),
        ("星空", "ほしぞら"),
        ("君", "き"),
    ],
)
def test_ac18_a_kanji_run_maps_to_one_or_more_hiragana(original: str, reading: str) -> None:
    assert reading_keeps_kana(original, reading)


def test_ac18_a_kanji_run_must_not_match_zero_hiragana() -> None:
    assert not reading_keeps_kana("君がいる", "がいる")


def test_ac18_empty_reading_for_a_kanji_line_fails() -> None:
    assert not reading_keeps_kana("君", "")


def test_ac18_a_kanji_run_must_be_replaced_by_hiragana_not_katakana_or_latin() -> None:
    assert not reading_keeps_kana("君", "キミ")
    assert not reading_keeps_kana("君", "kimi")


def test_ac18_a_kanji_left_in_the_reading_fails() -> None:
    assert not reading_keeps_kana("君がいる", "君 が いる")


def test_ac19_katakana_left_in_the_reading_fails() -> None:
    assert not reading_keeps_kana("ココロ", "ココロ")


def test_ac18_a_kanji_run_may_include_long_marks_after_a_hiragana_letter() -> None:
    assert reading_keeps_kana("空", "そ\u30fc")
    assert reading_keeps_kana("空が", "そ\u30fc が")


def test_ac18_a_kanji_run_must_start_with_a_hiragana_letter() -> None:
    assert not reading_keeps_kana("空", "\u30fc")
    assert not reading_keeps_kana("空", "\u30fcそ")


def test_ac18_kana_between_kanji_runs_must_match_exactly() -> None:
    assert reading_keeps_kana("空と海", "そら と うみ")
    assert not reading_keeps_kana("空と海", "そら を うみ")


def test_ac18_kana_between_kanji_runs_must_keep_their_order() -> None:
    assert reading_keeps_kana("空とが海", "そら とが うみ")
    assert not reading_keeps_kana("空とが海", "そら がと うみ")


@pytest.mark.parametrize(
    ("original", "reading"),
    [
        ("時々", "ときどき"),
        ("人々の", "ひとびと の"),
    ],
)
def test_ac18_iteration_mark_is_part_of_the_kanji_run(original: str, reading: str) -> None:
    assert reading_keeps_kana(original, reading)


def test_ac18_iteration_mark_is_not_kept_as_a_character_of_its_own() -> None:
    assert not reading_keeps_kana("時々", "とき々")


def test_ac18_latin_and_punctuation_must_match_in_order() -> None:
    assert reading_keeps_kana("夢、Go!", "ゆめ、 Go!")
    assert not reading_keeps_kana("夢、Go!", "ゆめ Go!")
    assert not reading_keeps_kana("夢、Go!", "ゆめ、 Og!")
    assert not reading_keeps_kana("夢、Go", "ゆめ Go、")


def test_ac18_extra_characters_at_the_end_of_the_reading_fail() -> None:
    assert not reading_keeps_kana("君", "きみ!")


def test_ac18_missing_kana_at_the_end_of_the_reading_fails() -> None:
    assert not reading_keeps_kana("君がいる", "きみ が い")


@pytest.mark.parametrize(
    ("original", "reading"),
    [
        ("遠く ひびく", "とおく ひびく"),
        ("夜　の 空", "よる の そら"),
        ("\t君が", "きみ が"),
        ("君がいる", "きみがいる"),
    ],
)
def test_ac18_all_whitespace_is_removed_from_both_before_comparing(
    original: str, reading: str
) -> None:
    assert reading_keeps_kana(original, reading)


# Katakana in the original (AC-19)


def test_ac19_spec_example_katakana_in_the_original_is_compared_as_hiragana() -> None:
    assert reading_keeps_kana("ココロ 光る", "こころ ひかる")


def test_ac19_spec_example_passes_the_hard_check_too() -> None:
    assert reading_is_allowed("ココロ 光る", "こころ ひかる")


def test_ac19_changed_kana_from_katakana_fails() -> None:
    assert not reading_keeps_kana("ココロ 光る", "ここら ひかる")


def test_ac19_katakana_long_mark_stays_a_long_mark() -> None:
    assert reading_keeps_kana("メロディー", "めろでぃー")


# Lines with no kanji: the reading must equal the original after whitespace and katakana.


def test_ac18_all_kana_line_must_equal_the_original() -> None:
    assert reading_keeps_kana("ひかりの うた", "ひかり の うた")
    assert not reading_keeps_kana("ひかりの うた", "ひかり の うだ")
    assert not reading_keeps_kana("ひかりの うた", "ひかり の うたう")


def test_ac19_all_katakana_line_must_equal_its_hiragana() -> None:
    assert reading_keeps_kana("ナミダ", "なみだ")
    assert not reading_keeps_kana("ナミダ", "なみた")


# Regex metacharacters in the original are plain characters, never pattern syntax (AC-18).


@pytest.mark.parametrize(
    ("original", "reading"),
    [
        ("君.夢", "きみ. ゆめ"),
        ("君*", "きみ*"),
        ("君(", "きみ("),
        ("夢?", "ゆめ?"),
        ("空+", "そら+"),
        ("夢[", "ゆめ["),
        ("空\\", "そら\\"),
        ("夢.*(君)?+[", "ゆめ.*(きみ)?+["),
    ],
)
def test_ac18_metacharacters_in_the_original_match_themselves(original: str, reading: str) -> None:
    assert reading_keeps_kana(original, reading)


@pytest.mark.parametrize(
    ("original", "reading"),
    [
        ("君.夢", "きみx ゆめ"),
        ("君*", "きみ"),
        ("夢?", "ゆめ"),
        ("空+", "そら"),
        ("空+", "そら++"),
        ("夢[あ]", "ゆめ い"),
    ],
)
def test_ac18_metacharacters_in_the_original_are_not_pattern_syntax(
    original: str, reading: str
) -> None:
    assert not reading_keeps_kana(original, reading)


# Reading length bound (AC-46) and empty readings (AC-47), checked by the hard check.


def test_ac46_reading_of_exactly_six_times_the_original_is_allowed() -> None:
    assert reading_is_allowed("君", "きみきみきみ")


def test_ac46_reading_longer_than_six_times_the_original_is_rejected() -> None:
    assert not reading_is_allowed("君", "きみきみきみき")


def test_ac46_length_counts_spaces_in_the_reading() -> None:
    """Both readings have 7 hiragana; only the extra space puts the second over 6 x 2 = 12."""
    allowed = "きみ が き み が き"
    over_the_cap = "き み が き み が き"
    assert len(allowed) == 12
    assert len(over_the_cap) == 13

    assert reading_is_allowed("君が", allowed)
    assert not reading_is_allowed("君が", over_the_cap)


def test_ac46_original_is_measured_as_given_including_leading_whitespace() -> None:
    assert reading_is_allowed(" 君", "きみきみきみきみきみきみ")
    assert not reading_is_allowed(" 君", "きみきみきみきみきみきみき")


@pytest.mark.parametrize("original", ["君", "ひかり", "ココロ 光る"])
def test_ac47_empty_reading_for_a_japanese_line_is_rejected(original: str) -> None:
    assert not reading_is_allowed(original, "")


# Speed: the worst case inside the bounds (a 200-character line, a 1,200-character reading).

TIME_LIMIT_SECONDS = 2.0
LONGEST_LINE = 200
LONGEST_READING = 6 * LONGEST_LINE


def test_ac46_alternating_kana_and_kanji_line_with_the_longest_reading_is_quick() -> None:
    original = "あ光" * (LONGEST_LINE // 2)
    reading = ("あ" + "ひ" * 11) * (LONGEST_LINE // 2)
    assert len(original) == LONGEST_LINE
    assert len(reading) == LONGEST_READING
    assert reading_is_allowed(original, reading)

    started = time.perf_counter()
    result = reading_keeps_kana(original, reading)
    elapsed = time.perf_counter() - started

    assert result
    assert elapsed < TIME_LIMIT_SECONDS


def test_ac46_adversarial_reading_that_fails_at_the_end_is_refused_quickly() -> None:
    """Every split of the が run is a candidate, so a backtracking pattern would take forever."""
    original = "空が" * (LONGEST_LINE // 2)
    reading = "が" * (LONGEST_READING - 1) + "ん"
    assert reading_is_allowed(original, reading)

    started = time.perf_counter()
    result = reading_keeps_kana(original, reading)
    elapsed = time.perf_counter() - started

    assert not result
    assert elapsed < TIME_LIMIT_SECONDS
