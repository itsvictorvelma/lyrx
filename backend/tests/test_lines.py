"""Tests for splitting the paste into lines, the size limits, and Japanese detection."""

import pytest
from pastes import (
    japanese_line,
    limit_details,
    paste_of_characters,
    paste_of_lines,
)

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
    assert error.details == limit_details("maxCharacters", 5001)


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
    assert error.details == limit_details("maxLines", 201)


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


def test_ac45_ac48_limit_details_hold_the_three_limits_and_the_limit_hit() -> None:
    """AC-48 adds `limitHit` and `measured` to the three AC-45 limits; no `lineNumber` here."""
    error = assert_refused(paste_of_lines(201), "input_too_large")

    assert error.details is not None
    assert set(error.details) == {
        "maxCharacters",
        "maxLines",
        "maxLineCharacters",
        "limitHit",
        "measured",
    }


# Line length limit (AC-45)


def test_ac45_line_of_exactly_200_characters_is_within_limits() -> None:
    assert_within_limits(japanese_line(200))


def test_ac45_line_of_201_characters_is_input_too_large() -> None:
    error = assert_refused(japanese_line(201), "input_too_large")

    assert error.status == 413
    assert error.details == limit_details("maxLineCharacters", 201, line_number=1)


def test_ac45_one_long_line_among_short_ones_is_input_too_large() -> None:
    paste = paste_of_lines(10) + "\n" + japanese_line(201) + "\n" + paste_of_lines(10)

    assert_refused(paste, "input_too_large")


def test_ac45_line_length_is_measured_after_trailing_whitespace_is_removed() -> None:
    assert_within_limits(japanese_line(200) + "   \t")


def test_ac45_leading_whitespace_counts_toward_the_line_length() -> None:
    assert_refused("  " + japanese_line(199), "input_too_large")


def test_ac45_ac48_message_names_the_long_line_and_its_length() -> None:
    """Under AC-48 the line-length refusal names the line instead of listing all three limits."""
    error = assert_refused(japanese_line(201), "input_too_large")

    assert error.message == (
        "Line 1 is too long: 201 characters. The limit is 200 characters per line."
        " The lyrics may have lost their line breaks."
    )


# Which limit was hit (AC-48)


def test_ac48_1_character_limit_is_reported_first_with_its_measured_count() -> None:
    """5,002 characters on one line breaks two limits; only the character limit is reported."""
    paste = "ゆめ" * 2501
    assert len(paste) == 5002

    error = assert_refused(paste, "input_too_large")

    assert error.status == 413
    assert error.details == {
        "maxCharacters": 5000,
        "maxLines": 200,
        "maxLineCharacters": 200,
        "limitHit": "maxCharacters",
        "measured": 5002,
    }
    assert error.message == (
        "The lyrics are too long: 5,002 characters. The limit is 5,000 characters."
    )


def test_ac48_2_line_limit_reports_the_line_count() -> None:
    """201 short lines report `maxLines` with the line count and no line number."""
    paste = "\n".join(["うた"] * 201)

    error = assert_refused(paste, "input_too_large")

    assert error.status == 413
    assert error.details == limit_details("maxLines", 201)
    assert error.message == "The lyrics have too many lines: 201. The limit is 200 lines."


def test_ac48_3_line_length_limit_reports_the_line_number_and_its_length() -> None:
    """One 2,700-character line reports `maxLineCharacters`, its length, and line 1."""
    paste = "ゆめ" * 1350
    assert len(paste) == 2700

    error = assert_refused(paste, "input_too_large")

    assert error.status == 413
    assert error.details == limit_details("maxLineCharacters", 2700, line_number=1)
    assert error.message == (
        "Line 1 is too long: 2,700 characters. The limit is 200 characters per line."
        " The lyrics may have lost their line breaks."
    )


def test_ac48_4_line_number_counts_lines_as_typed_and_length_drops_trailing_spaces() -> None:
    """Blank lines count toward `lineNumber`, CRLF is one break, trailing spaces go unmeasured."""
    paste = "\r\n\r\n星がながれる\r\n\r\n\r\n\r\n" + "か" * 201 + "   "
    assert split_lines(paste).index("か" * 201) == 2

    error = assert_refused(paste, "input_too_large")

    assert error.details == limit_details("maxLineCharacters", 201, line_number=7)


def test_ac48_5_line_number_is_the_first_of_two_long_lines() -> None:
    """With two lines over the limit, the first one is reported."""
    paste = "夜の月\n" + "か" * 201 + "\n星\n" + "ゆ" * 250

    error = assert_refused(paste, "input_too_large")

    assert error.details == limit_details("maxLineCharacters", 201, line_number=2)


def test_ac48_measured_characters_count_the_raw_paste_like_the_limit_does() -> None:
    """`measured` counts trailing spaces and blank lines, as the 5,000 limit does."""
    paste = "\n".join(japanese_line(49) + " " for _ in range(100))
    assert len(paste) == 5099

    error = assert_refused(paste, "input_too_large")

    assert error.details == limit_details("maxCharacters", 5099)


def test_ac48_measured_characters_count_carriage_return_newline_once() -> None:
    """CRLF is one character in `measured`, as in the limit."""
    paste = paste_of_characters(5001, line_ending="\r\n")

    error = assert_refused(paste, "input_too_large")

    assert error.details == limit_details("maxCharacters", 5001)


def test_ac48_measured_lines_count_lines_after_splitting_like_the_limit_does() -> None:
    """`measured` counts lines after blank runs collapse and blank ends drop."""
    paste = "\n\n" + paste_of_lines(100) + "\n\n\n\n" + paste_of_lines(100) + "\n\n"
    assert len(split_lines(paste)) == 201

    error = assert_refused(paste, "input_too_large")

    assert error.details == limit_details("maxLines", 201)


def test_ac48_measured_line_length_counts_leading_whitespace() -> None:
    """Leading whitespace is part of the line, so it is part of the measured length."""
    error = assert_refused("夜の月\n  " + japanese_line(199), "input_too_large")

    assert error.details == limit_details("maxLineCharacters", 201, line_number=2)


@pytest.mark.parametrize(
    "paste",
    [
        "ゆめ" * 2501,
        "\n".join(["うた"] * 201),
        "ゆめ" * 1350,
        "\r\n\r\n星がながれる\r\n\r\n\r\n\r\n" + "か" * 201 + "   ",
    ],
)
def test_ac48_6_details_hold_only_the_listed_integers_and_the_limit_name(paste: str) -> None:
    """No text from the paste reaches `details` or the message: only integers and a limit name."""
    error = assert_refused(paste, "input_too_large")

    assert error.details is not None
    assert set(error.details) <= {
        "maxCharacters",
        "maxLines",
        "maxLineCharacters",
        "limitHit",
        "measured",
        "lineNumber",
    }
    assert error.details.get("limitHit") in {"maxCharacters", "maxLines", "maxLineCharacters"}
    for key, value in error.details.items():
        if key != "limitHit":
            assert type(value) is int
    assert not has_japanese(error.message)


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
def test_ac43_iteration_marks_shime_and_extra_ideograph_blocks_have_japanese(text: str) -> None:
    assert has_japanese(text) is True
