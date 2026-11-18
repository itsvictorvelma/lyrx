"""Tests for splitting the paste into lines, reading the paste, and Japanese detection."""

import pytest

from lyrx.errors import ApiError
from lyrx.lines import has_japanese, read_paste, split_lines

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


# Empty input (spec 001 AC-5; spec 003 cleanup step 2: decided before cleanup)


@pytest.mark.parametrize("paste", ["", "   ", "\n\n\n", " \r\n\t\r \n", "\u3000\n "])
def test_ac5_empty_or_whitespace_paste_is_empty_input(paste: str) -> None:
    with pytest.raises(ApiError) as caught:
        read_paste(paste)

    assert caught.value.code == "empty_input"
    assert caught.value.status == 400


# Reading the paste: the cleaned lines, with no size limits (spec 003, AC-23 to AC-34)


def test_spec003_ac23_read_paste_returns_the_cleaned_lines() -> None:
    paste = "君の声が 키미노 코에가 너의 목소리가 " + "遠くまでひびく 토오쿠마데 " * 30

    assert read_paste(paste) == ["君の声が"] + ["遠くまでひびく"] * 30


def test_spec003_ac24_read_paste_leaves_a_normal_paste_as_split() -> None:
    paste = "君の声が\n遠く ひびく\n\n星が  ながれる\nWe sing tonight"

    assert read_paste(paste) == split_lines(paste)


def test_spec003_ac25_read_paste_normalizes_to_nfc_before_cleaning() -> None:
    assert read_paste("君か\u3099いる 너의") == ["君がいる"]


def test_spec003_ac26_read_paste_trims_leading_whitespace() -> None:
    assert read_paste("  君の声が\u3000\n\t遠く") == ["君の声が", "遠く"]


def test_spec003_ac25_read_paste_removes_text_through_the_shared_removal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The paste route calls `lyric_cleanup.remove_unwanted_characters`, the one shared removal."""
    # Imported here so the rest of this file still runs while the module does not exist.
    from lyrx import lyric_cleanup

    seen_lines: list[str] = []
    real_removal = lyric_cleanup.remove_unwanted_characters

    def recording_removal(line: str) -> str:
        seen_lines.append(line)
        return real_removal(line)

    monkeypatch.setattr(lyric_cleanup, "remove_unwanted_characters", recording_removal)

    lines = read_paste("君の声が 너의\n\n遠く")

    assert lines == ["君の声が", "", "遠く"]
    assert "君の声が 너의" in seen_lines


@pytest.mark.parametrize(
    ("paste", "expected"),
    [
        ("ゆめ" * 150, ["ゆめ" * 150]),
        ("か" * 250 + " " + "そら", ["か" * 250, "そら"]),
        ("君の声が\n키미노 코에가\n" + "か" * 201, ["君の声が", "か" * 201]),
        (
            "\r\n\r\n星がながれる\r\n\r\n\r\n\r\n" + "か" * 201 + "   ",
            ["星がながれる", "", "か" * 201],
        ),
    ],
    ids=["no-split-point", "long-piece", "after-korean-line", "after-blank-lines"],
)
def test_spec003_ac32_line_over_the_split_length_is_kept_not_refused(
    paste: str, expected: list[str]
) -> None:
    assert read_paste(paste) == expected


@pytest.mark.parametrize(
    ("paste", "expected"),
    [
        ("\n".join(["うたう " + "노래" * 20] * 120), ["うたう"] * 120),
        ("\n".join(["うた", "노래"] * 201), ["うた"] * 201),
        (("うた " * 201).rstrip(), ["うた"] * 201),
        ("ゆめ" * 2501, ["ゆめ" * 2501]),
        ("\n".join(["うた"] * 1000), ["うた"] * 1000),
    ],
    ids=["5399-characters", "402-alternating-lines", "201-words", "5002-characters", "1000-lines"],
)
def test_spec003_ac33_there_are_no_limits_on_characters_or_lines(
    paste: str, expected: list[str]
) -> None:
    assert read_paste(paste) == expected


@pytest.mark.parametrize(
    "paste",
    ["키미노 코에가\n너의 목소리가", "꿈" * 10000, "\u200b"],
    ids=["korean-lines", "long-korean-line", "zero-width-only"],
)
def test_spec003_ac34_paste_that_cleans_to_nothing_is_not_empty_input(paste: str) -> None:
    """Not `empty_input`: the pipeline then refuses it as `no_japanese`."""
    assert read_paste(paste) == []


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


def test_spec003_ac43_kanji_outside_the_basic_plane_is_japanese() -> None:
    """U+20B9F, a CJK Extension B kanji; AC-43's unknown-word example uses it."""
    assert has_japanese("\U00020b9f") is True
