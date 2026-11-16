"""Tests for splitting the paste into lines, the size limits, and Japanese detection."""

import pytest
from pastes import LIMIT_DETAILS, japanese_line, paste_of_characters, paste_of_lines

from lyrx.errors import ApiError
from lyrx.lines import check_limits, has_japanese, split_lines


def assert_within_limits(paste: str) -> None:
    check_limits(paste, split_lines(paste))


def assert_refused(paste: str, expected_code: str) -> ApiError:
    with pytest.raises(ApiError) as caught:
        check_limits(paste, split_lines(paste))
    assert caught.value.code == expected_code
    return caught.value


# Splitting (AC-1)


def test_ac1_split_normalizes_endings_trims_and_collapses_blank_runs() -> None:
    paste = "\r\n\r\n君の声が  \r\n\r\n\r\n遠く ひびく\r\n\r\n"

    assert split_lines(paste) == ["君の声が", "", "遠く ひびく"]


def test_ac1_lone_carriage_return_is_one_line_break() -> None:
    assert split_lines("夜の月\r風の音\rほしぞら") == ["夜の月", "風の音", "ほしぞら"]


def test_ac1_carriage_return_newline_is_one_line_break_not_two() -> None:
    assert split_lines("夜の月\r\n風の音") == ["夜の月", "風の音"]


def test_ac1_trailing_whitespace_is_removed_and_leading_whitespace_is_kept() -> None:
    assert split_lines("  夜の月\t \n\t風の 音\u3000") == ["  夜の月", "\t風の 音"]


def test_ac1_leading_whitespace_survives_dropping_blank_lines_at_the_start() -> None:
    assert split_lines("\n \n  ほしが ひかる") == ["  ほしが ひかる"]


def test_ac1_spaces_inside_a_line_are_kept() -> None:
    assert split_lines("きみ  と   ぼく") == ["きみ  と   ぼく"]


def test_ac1_single_blank_line_inside_the_text_is_kept() -> None:
    assert split_lines("夜の月\n\n風の音") == ["夜の月", "", "風の音"]


def test_ac1_whitespace_only_lines_count_as_blank_in_a_run() -> None:
    assert split_lines("夜の月\n   \n\t\n\u3000\n風の音") == ["夜の月", "", "風の音"]


def test_ac1_each_blank_run_collapses_separately() -> None:
    paste = "一つ目\n\n\n二つ目\n\n\n\n三つ目"

    assert split_lines(paste) == ["一つ目", "", "二つ目", "", "三つ目"]


@pytest.mark.parametrize("paste", ["", "   ", "\n\n", " \r\n\t\r \n", "\u3000\n "])
def test_ac1_empty_or_whitespace_paste_splits_into_no_lines(paste: str) -> None:
    assert split_lines(paste) == []


# Empty input (AC-5)


@pytest.mark.parametrize("paste", ["", "   ", "\n\n\n", " \r\n\t\r \n", "\u3000\n "])
def test_ac5_empty_or_whitespace_paste_is_empty_input(paste: str) -> None:
    error = assert_refused(paste, "empty_input")

    assert error.status == 400


# Character limit (AC-6)


def test_ac6_paste_of_exactly_5000_characters_is_within_limits() -> None:
    paste = paste_of_characters(5000)
    assert len(paste) == 5000

    assert_within_limits(paste)


def test_ac6_paste_of_5001_characters_is_input_too_large() -> None:
    paste = paste_of_characters(5001)
    assert len(paste) == 5001

    error = assert_refused(paste, "input_too_large")

    assert error.status == 413
    assert error.details == LIMIT_DETAILS


def test_ac6_carriage_return_newline_counts_as_one_character() -> None:
    paste = paste_of_characters(5000, line_ending="\r\n")
    assert len(paste) > 5000
    assert len(paste.replace("\r\n", "\n")) == 5000

    assert_within_limits(paste)


def test_ac6_characters_are_counted_before_trailing_whitespace_is_removed() -> None:
    # Each line ends in a space that splitting removes; the limit counts it anyway.
    paste = "\n".join(japanese_line(49) + " " for _ in range(100))
    assert len(paste) == 5099
    assert len("\n".join(split_lines(paste))) < 5000

    assert_refused(paste, "input_too_large")


def test_ac6_characters_are_counted_before_blank_lines_are_dropped() -> None:
    paste = paste_of_characters(4990) + "\n" * 11
    assert len(paste) == 5001

    assert_refused(paste, "input_too_large")


# Line limit (AC-7)


def test_ac7_paste_of_exactly_200_lines_is_within_limits() -> None:
    assert_within_limits(paste_of_lines(200))


def test_ac7_paste_of_201_lines_is_input_too_large() -> None:
    error = assert_refused(paste_of_lines(201), "input_too_large")

    assert error.status == 413
    assert error.details == LIMIT_DETAILS


def test_ac7_lines_are_counted_after_blank_lines_are_dropped_and_collapsed() -> None:
    first_half = paste_of_lines(100)
    second_half = paste_of_lines(99)
    paste = "\n\n\n" + first_half + "\n\n\n\n\n" + second_half + "\n\n\n\n"
    assert len(split_lines(paste)) == 200

    assert_within_limits(paste)


def test_ac7_carriage_return_newline_endings_do_not_double_the_line_count() -> None:
    assert_within_limits(paste_of_lines(200, line_ending="\r\n"))


def test_ac7_a_blank_line_inside_the_text_counts_toward_the_limit() -> None:
    paste = paste_of_lines(100) + "\n\n" + paste_of_lines(100)
    assert len(split_lines(paste)) == 201

    assert_refused(paste, "input_too_large")


def test_ac7_limit_details_hold_only_the_two_limits() -> None:
    error = assert_refused(paste_of_lines(201), "input_too_large")

    assert error.details is not None
    assert set(error.details) == {"maxCharacters", "maxLines"}


# Japanese detection (AC-8)


@pytest.mark.parametrize(
    "text",
    [
        "ひかる",
        "ココロ",
        "空",
        "々",
        "ー",
        "We 歌う tonight",
        "  ほし",
        "2人で",
    ],
)
def test_ac8_text_with_hiragana_katakana_or_kanji_has_japanese(text: str) -> None:
    assert has_japanese(text) is True


@pytest.mark.parametrize(
    "text",
    [
        "",
        "We sing tonight",
        "123 !?",
        "、。「」\uff01\uff1f",
        "\u3000",
        "\uff21\uff22\uff23",
        "하늘",
        "café",
    ],
)
def test_ac8_text_without_hiragana_katakana_or_kanji_has_no_japanese(text: str) -> None:
    assert has_japanese(text) is False


@pytest.mark.parametrize(
    "text",
    [
        "\u309d",  # hiragana iteration mark
        "\u309e",  # voiced hiragana iteration mark
        "\u30fd",  # katakana iteration mark
        "\u30fe",  # voiced katakana iteration mark
        "\u3006",  # shime
        "\u3400",  # first CJK Extension A ideograph
        "\u4dbf",  # last CJK Extension A ideograph
        "\uf900",  # first CJK Compatibility Ideograph
        "\ufaff",  # last code point of the CJK Compatibility Ideographs block
    ],
)
def test_ac8_iteration_marks_shime_and_extra_ideograph_blocks_have_japanese(text: str) -> None:
    assert has_japanese(text) is True
