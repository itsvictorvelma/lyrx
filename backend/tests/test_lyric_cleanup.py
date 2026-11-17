"""Tests for cleaning lyrics: the shared removal and the line cleanup (spec 003, AC-23 to AC-36)."""

import time

import pytest

from lyrx import config
from lyrx.lines import split_lines
from lyrx.lyric_cleanup import clean_lines, remove_unwanted_characters

# Escapes for characters ruff would flag as ambiguous, and for invisible ones.
FULL_WIDTH_SPACE = "\u3000"
NO_BREAK_SPACE = "\u00a0"
ZERO_WIDTH_SPACE = "\u200b"
FULL_WIDTH_EXCLAMATION = "\uff01"
FULL_WIDTH_QUESTION = "\uff1f"
FULL_WIDTH_OPEN = "\uff08"
FULL_WIDTH_CLOSE = "\uff09"

# A generous bound: a linear pass takes milliseconds, a quadratic one takes minutes.
LINEAR_TIME_LIMIT_SECONDS = 2.0


def clean(paste: str) -> list[str]:
    """The paste split as in spec 001, then cleaned."""
    return clean_lines(split_lines(paste))


# The AC-23 paste: three invented triples (Japanese, Hangul pronunciation, Korean translation).
AC23_TRIPLES = [
    ("君の声が聞こえる", "키미노 코에가 키코에루", "너의 목소리가 들려"),
    ("遠くまでひびく", "토오쿠마데 히비쿠", "멀리까지 울려"),
    ("星がながれる夜に", "호시가 나가레루 요루니", "별이 흐르는 밤에"),
]
AC23_PASTE = " ".join(item for _ in range(10) for triple in AC23_TRIPLES for item in triple)
AC23_LINES = [japanese for _ in range(10) for japanese, _, _ in AC23_TRIPLES]


def is_hangul(character: str) -> bool:
    code_point = ord(character)
    return any(
        first <= code_point <= last
        for first, last in [
            (0x1100, 0x11FF),
            (0x3130, 0x318F),
            (0xA960, 0xA97F),
            (0xAC00, 0xD7AF),
            (0xD7B0, 0xD7FF),
            (0xFFA0, 0xFFDC),
        ]
    )


# The shared removal: zero-width characters (AC-26)


@pytest.mark.parametrize("zero_width", ["\u200b", "\u200c", "\u200d", "\u2060", "\ufeff"])
def test_ac26_each_zero_width_character_is_removed(zero_width: str) -> None:
    assert remove_unwanted_characters(f"君{zero_width}の声") == "君の声"


@pytest.mark.parametrize("kept", ["\u200a", "\u200e", "\u2061"])
def test_ac26_neighbours_of_the_zero_width_characters_are_kept(kept: str) -> None:
    assert remove_unwanted_characters(f"君{kept}の声") == f"君{kept}の声"


# The shared removal: Hangul (AC-25)


@pytest.mark.parametrize(
    "hangul",
    [
        "\u1100",
        "\u11ff",
        "\u3130",
        "\u318f",
        "\ua960",
        "\ua97f",
        "가",
        "\ud7af",
        "\ud7b0",
        "\ud7ff",
        "\uffa0",
        "\uffdc",
    ],
    ids=lambda character: f"U+{ord(character):04X}",
)
def test_ac25_first_and_last_character_of_each_hangul_range_is_removed(hangul: str) -> None:
    assert remove_unwanted_characters(f"君{hangul}が") == "君が"


@pytest.mark.parametrize(
    "kept",
    ["\u10ff", "\u1200", "\u312f", "\u3190", "\ua95f", "\ua980", "\uabff", "\uff9f", "\uffe0"],
    ids=lambda character: f"U+{ord(character):04X}",
)
def test_ac25_characters_just_outside_the_hangul_ranges_are_kept(kept: str) -> None:
    assert remove_unwanted_characters(f"君{kept}が") == f"君{kept}が"


def test_ac25_removal_does_not_collapse_or_trim_spaces() -> None:
    """Collapsing and trimming are the cleanup's job (steps 3.2 and 3.3), not the removal's."""
    assert remove_unwanted_characters(" 星が 별이 ながれる ") == " 星が  ながれる "


def test_ac25_control_characters_are_not_removed_from_a_line() -> None:
    """Removing control characters stays in spec 002's candidate step."""
    assert remove_unwanted_characters("君\x07が") == "君\x07が"


# The shared removal: empty brackets (AC-25)

BRACKET_PAIRS = [
    ("(", ")"),
    (FULL_WIDTH_OPEN, FULL_WIDTH_CLOSE),
    ("[", "]"),
    ("\uff3b", "\uff3d"),
    ("「", "」"),
    ("【", "】"),
]
BRACKET_IDS = [
    "ascii-round",
    "full-width-round",
    "ascii-square",
    "full-width-square",
    "kagi",
    "lenticular",
]


@pytest.mark.parametrize(("opening", "closing"), BRACKET_PAIRS, ids=BRACKET_IDS)
def test_ac25_a_pair_left_empty_after_removing_hangul_is_removed(
    opening: str, closing: str
) -> None:
    assert remove_unwanted_characters(f"君の声が{opening}키미노{closing}遠く") == "君の声が遠く"


@pytest.mark.parametrize(("opening", "closing"), BRACKET_PAIRS, ids=BRACKET_IDS)
def test_ac25_a_pair_already_empty_in_the_paste_is_removed(opening: str, closing: str) -> None:
    assert remove_unwanted_characters(f"君{opening}{closing}が") == "君が"


@pytest.mark.parametrize(
    "inside",
    [
        " ",
        "\t",
        FULL_WIDTH_SPACE,
        " \t ",
        "、。",
        f"{FULL_WIDTH_EXCLAMATION}{FULL_WIDTH_QUESTION}",
        "...",
        "- ,",
    ],
)
def test_ac25_a_pair_holding_only_whitespace_or_punctuation_is_removed(inside: str) -> None:
    assert remove_unwanted_characters(f"君({inside})が") == "君が"


def test_ac25_brackets_around_hangul_and_spaces_are_removed() -> None:
    line = f"君の声が{FULL_WIDTH_OPEN}키미노 코에가{FULL_WIDTH_CLOSE}"

    assert remove_unwanted_characters(line) == "君の声が"


@pytest.mark.parametrize(
    "line",
    [
        f"君{FULL_WIDTH_OPEN}きみ{FULL_WIDTH_CLOSE}が",
        "君(la la)が",
        "君(1)が",
        "君(\u266a)が",
        "君(「)が",
        f"君({FULL_WIDTH_CLOSE}が",
        f"君{FULL_WIDTH_OPEN})が",
        "君(が",
        "君)が",
    ],
    ids=[
        "kana-inside",
        "latin-inside",
        "digit-inside",
        "symbol-inside",
        "other-bracket-inside",
        "mismatched-ascii-open",
        "mismatched-full-width-open",
        "unclosed",
        "unopened",
    ],
)
def test_ac25_brackets_that_hold_text_or_do_not_pair_are_kept(line: str) -> None:
    assert remove_unwanted_characters(line) == line


def test_ac25_bracket_with_text_left_after_removing_hangul_is_kept_as_is() -> None:
    line = f"{FULL_WIDTH_OPEN}키미 君{FULL_WIDTH_CLOSE}"

    assert remove_unwanted_characters(line) == f"{FULL_WIDTH_OPEN} 君{FULL_WIDTH_CLOSE}"


@pytest.mark.parametrize(
    "line",
    ["(" * 250_000, "(" * 125_000 + ")" * 125_000, "( " * 125_000, "(가" * 125_000 + ")"],
    ids=["unclosed-opens", "nested", "open-space-runs", "opens-with-hangul"],
)
def test_ac25_removal_runs_in_linear_time_on_a_line_at_the_body_cap(line: str) -> None:
    """Security: one pass, so a 256 KiB paste on one line is handled at once."""
    started = time.perf_counter()

    remove_unwanted_characters(line)

    assert time.perf_counter() - started < LINEAR_TIME_LIMIT_SECONDS


# The cleanup (AC-23 to AC-34)


def test_ac23_joined_paste_cleans_to_the_thirty_japanese_lines() -> None:
    lines = clean(AC23_PASTE)

    assert lines == AC23_LINES
    assert not any(is_hangul(character) for line in lines for character in line)


def test_ac24_normal_paste_is_unchanged() -> None:
    paste = "君の声が\n遠く ひびく\n\n星が  ながれる\nWe sing tonight"

    assert clean(paste) == ["君の声が", "遠く ひびく", "", "星が  ながれる", "We sing tonight"]
    assert clean(paste) == split_lines(paste)


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ("君の声が 너의 목소리가", "君の声が"),
        ("星が 별이 ながれる", "星が ながれる"),
        (f"君の声が{FULL_WIDTH_OPEN}키미노 코에가{FULL_WIDTH_CLOSE}", "君の声が"),
        ("君の声が【키미노】遠く", "君の声が遠く"),
        ("Oh 너의 君と", "Oh 君と"),
    ],
)
def test_ac25_hangul_inside_a_line_is_removed(line: str, expected: str) -> None:
    assert clean_lines([line]) == [expected]


def test_ac25_spaces_and_tabs_collapse_only_where_something_was_removed() -> None:
    assert clean_lines(["星が \t별이\t\t ながれる", "星が  ながれる"]) == [
        "星が ながれる",
        "星が  ながれる",
    ]


def test_ac25_full_width_spaces_are_not_collapsed() -> None:
    line = f"君の声が{FULL_WIDTH_SPACE}너의{FULL_WIDTH_SPACE}遠く"

    assert clean_lines([line]) == [f"君の声が{FULL_WIDTH_SPACE}{FULL_WIDTH_SPACE}遠く"]


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        (f"君{ZERO_WIDTH_SPACE}の声", "君の声"),
        (f"  君の声が{FULL_WIDTH_SPACE}", "君の声が"),
        (f"君の声が{FULL_WIDTH_SPACE}遠く", f"君の声が{FULL_WIDTH_SPACE}遠く"),
    ],
    ids=["zero-width", "line-ends", "full-width-space-inside"],
)
def test_ac26_zero_width_characters_and_line_ends(line: str, expected: str) -> None:
    assert clean_lines([line]) == [expected]


def test_ac26_leading_tab_and_space_are_trimmed_even_when_nothing_is_removed() -> None:
    assert clean_lines(["\t 遠く ひびく"]) == ["遠く ひびく"]


@pytest.mark.parametrize(
    "paste",
    [
        "君の声が\n\n遠くひびく",
        "君の声が\n키미노 코에가\n너의 목소리가\n\n遠くひびく",
        "君の声が\n\n키미노\n\n遠くひびく",
    ],
    ids=["blank-kept", "korean-lines-dropped", "blank-run-collapsed"],
)
def test_ac27_blank_lines_are_kept_once_and_korean_only_lines_dropped(paste: str) -> None:
    assert clean(paste) == ["君の声が", "", "遠くひびく"]


def test_ac27_blank_lines_left_at_the_ends_are_dropped() -> None:
    assert clean("키미노\n\n君の声が\n\n너의") == ["君の声が"]


def test_ac28_line_of_exactly_200_characters_with_spaces_is_not_split() -> None:
    line = "ゆめ " * 66 + "ゆめ"
    assert len(line) == 200

    assert clean_lines([line]) == [line]


def test_ac28_length_is_measured_after_removal() -> None:
    line = "ゆめ " * 59 + "ゆめ" + " " + "꿈" * 100
    assert len(line) == 280

    assert clean_lines([line]) == ["ゆめ " * 59 + "ゆめ"]


def test_ac29_long_line_is_split_at_every_whitespace_run() -> None:
    line = "か" * 120 + FULL_WIDTH_SPACE + "き" * 120 + "  \t " + "く" * 10

    assert clean_lines([line]) == ["か" * 120, "き" * 120, "く" * 10]


def test_ac29_long_line_with_no_japanese_is_split_at_its_spaces() -> None:
    latin_line = ("la " * 80).rstrip()
    assert len(latin_line) == 239

    assert clean_lines(["君の声が", latin_line]) == ["君の声が"] + ["la"] * 80


def test_ac29_short_pieces_between_whitespace_runs_become_lines() -> None:
    line = "か" * 150 + " き " + "く" * 60

    assert clean_lines([line]) == ["か" * 150, "き", "く" * 60]


def test_ac29_no_break_space_is_a_split_point() -> None:
    """User decision 2026-11-17: U+00A0 splits a long line like an ASCII space."""
    line = "か" * 120 + NO_BREAK_SPACE + "き" * 120

    assert clean_lines([line]) == ["か" * 120, "き" * 120]


def test_ac29_no_break_space_in_a_mixed_whitespace_run_is_one_split_point() -> None:
    line = "か" * 120 + f" {NO_BREAK_SPACE}\t{FULL_WIDTH_SPACE}" + "き" * 120

    assert clean_lines([line]) == ["か" * 120, "き" * 120]


def test_ac29_no_break_spaces_collapse_like_ascii_spaces_where_something_was_removed() -> None:
    """User decision 2026-11-17: U+00A0 is treated like an ASCII space when collapsing."""
    line = f"星が{NO_BREAK_SPACE}별이{NO_BREAK_SPACE} ながれる"

    assert clean_lines([line]) == ["星が ながれる"]


def test_ac29_no_break_space_is_kept_in_a_short_line_where_nothing_was_removed() -> None:
    line = f"星が{NO_BREAK_SPACE}{NO_BREAK_SPACE}ながれる"

    assert clean_lines([line]) == [line]


def test_ac29_no_break_space_at_the_line_ends_is_trimmed() -> None:
    assert clean_lines([f"{NO_BREAK_SPACE}星が{NO_BREAK_SPACE}"]) == ["星が"]


def test_ac30_long_line_with_no_whitespace_is_split_after_each_full_stop() -> None:
    line = "かぜがふく。" * 50
    assert len(line) == 300

    assert clean_lines([line]) == ["かぜがふく。"] * 50


@pytest.mark.parametrize(
    "marks",
    [
        f"{FULL_WIDTH_EXCLAMATION}{FULL_WIDTH_QUESTION}",
        "!",
        "?",
        FULL_WIDTH_QUESTION,
        "。。",
        "!?",
    ],
)
def test_ac30_a_run_of_sentence_ending_marks_splits_once_after_the_run(marks: str) -> None:
    line = "あめ" * 60 + marks + "あめ" * 60

    assert clean_lines([line]) == ["あめ" * 60 + marks, "あめ" * 60]


def test_ac30_piece_still_over_the_split_length_after_both_splits_stays_whole() -> None:
    assert clean_lines(["ゆめ" * 150]) == ["ゆめ" * 150]


def test_ac30_other_punctuation_is_not_a_split_point() -> None:
    line = "あめ" * 60 + "、" + "あめ" * 60

    assert clean_lines([line]) == [line]


def test_ac31_whitespace_first_then_marks_only_for_pieces_still_too_long() -> None:
    line = "か" * 150 + "。" + "か" * 150 + " " + "そら。そら"

    assert clean_lines([line]) == ["か" * 150 + "。", "か" * 150, "そら。そら"]


def test_ac31_lines_within_the_split_length_are_not_split_at_marks() -> None:
    assert clean_lines(["そら。そら!あめ"]) == ["そら。そら!あめ"]


def test_ac32_line_with_no_whitespace_or_marks_is_kept_whole() -> None:
    assert clean("ゆめ" * 150) == ["ゆめ" * 150]


def test_ac32_long_piece_after_the_whitespace_split_is_kept_whole() -> None:
    assert clean("か" * 250 + " " + "そら") == ["か" * 250, "そら"]


def test_ac32_long_line_after_a_dropped_korean_line_is_kept_whole() -> None:
    assert clean("君の声が\n키미노 코에가\n" + "か" * 201) == ["君の声が", "か" * 201]


def test_ac32_long_line_after_blank_lines_is_kept_whole_and_trimmed() -> None:
    paste = "\r\n\r\n星がながれる\r\n\r\n\r\n\r\n" + "か" * 201 + "   "

    assert clean(paste) == ["星がながれる", "", "か" * 201]


def test_ac33_korean_halves_are_removed_from_each_line() -> None:
    paste = "\n".join(["うたう " + "노래" * 20] * 120)

    assert clean(paste) == ["うたう"] * 120


def test_ac33_402_alternating_lines_clean_to_201_lines_with_no_line_limit() -> None:
    assert clean("\n".join(["うた", "노래"] * 201)) == ["うた"] * 201


def test_ac33_long_line_of_short_words_splits_into_one_line_per_word() -> None:
    assert clean(("うた " * 201).rstrip()) == ["うた"] * 201


def test_ac33_line_of_5002_characters_stays_one_line_with_no_character_limit() -> None:
    line = "ゆめ" * 2501
    assert len(line) == 5002

    assert clean(line) == [line]


def test_ac34_paste_of_only_korean_cleans_to_no_lines() -> None:
    assert clean("키미노 코에가\n너의 목소리가") == []
    assert clean("꿈" * 10000) == []
    assert clean(ZERO_WIDTH_SPACE) == []


def test_ac34_blank_line_from_splitting_is_not_dropped_by_the_cleanup_itself() -> None:
    """A blank line inside the lines stays blank (spec 001 AC-3); only the ends are tidied."""
    assert clean_lines(["君の声が", "", "遠く"]) == ["君の声が", "", "遠く"]


def test_ac29_splitting_a_long_line_runs_in_linear_time() -> None:
    """Security: a 256 KiB line of short words and marks is cleaned at once."""
    line = "か " * 60_000 + "か。" * 60_000
    started = time.perf_counter()

    clean_lines([line])

    assert time.perf_counter() - started < LINEAR_TIME_LIMIT_SECONDS


# Idempotence (AC-36)

AC36_PASTES = [
    AC23_PASTE,
    "君の声が\n遠く ひびく\n\n星が  ながれる\nWe sing tonight",
    "君の声が 너의 목소리가",
    "星が 별이 ながれる",
    f"君の声が{FULL_WIDTH_OPEN}키미노 코에가{FULL_WIDTH_CLOSE}",
    "君の声が【키미노】遠く",
    "Oh 너의 君と",
    f"君{ZERO_WIDTH_SPACE}の声",
    f"  君の声が{FULL_WIDTH_SPACE}",
    f"君の声が{FULL_WIDTH_SPACE}遠く",
    "君の声が\n\n遠くひびく",
    "君の声が\n키미노 코에가\n너의 목소리가\n\n遠くひびく",
    "君の声が\n\n키미노\n\n遠くひびく",
    "키미노\n\n君の声が\n\n너의",
    "ゆめ " * 66 + "ゆめ",
    "ゆめ " * 59 + "ゆめ" + " " + "꿈" * 100,
    "か" * 120 + FULL_WIDTH_SPACE + "き" * 120 + "  \t " + "く" * 10,
    "か" * 120 + NO_BREAK_SPACE + "き" * 120,
    "君の声が\n" + ("la " * 80).rstrip(),
    "かぜがふく。" * 50,
    "あめ" * 60 + f"{FULL_WIDTH_EXCLAMATION}{FULL_WIDTH_QUESTION}" + "あめ" * 60,
    "あめ" * 60 + "!" + "あめ" * 60,
    "か" * 150 + "。" + "か" * 150 + " " + "そら。そら",
    "ゆめ" * 150,
    "か" * 250 + " " + "そら",
    "君の声が\n키미노 코에가\n" + "か" * 201,
    "\r\n\r\n星がながれる\r\n\r\n\r\n\r\n" + "か" * 201 + "   ",
    "\n".join(["うたう " + "노래" * 20] * 120),
    "\n".join(["うた", "노래"] * 201),
    ("うた " * 201).rstrip(),
    "ゆめ" * 2501,
]


@pytest.mark.parametrize("paste", AC36_PASTES, ids=[f"paste-{n}" for n in range(len(AC36_PASTES))])
def test_ac36_cleaning_the_cleaned_lines_again_gives_the_same_lines(paste: str) -> None:
    cleaned = clean(paste)

    assert clean_lines(cleaned) == cleaned


# The split length is a setting (AGENTS.md: settings in one place)


def test_ac28_split_length_comes_from_config(monkeypatch: pytest.MonkeyPatch) -> None:
    """With the setting lowered to 10, an 11-character line is split; a 10-character one is not."""
    monkeypatch.setattr(config, "CLEANUP_SPLIT_LENGTH", 10)
    longer_line = "ゆめゆめ ゆめゆめゆめ"
    line_at_the_setting = "ゆめゆめ ゆめゆめゆ"
    assert len(longer_line) == 11
    assert len(line_at_the_setting) == 10

    assert clean_lines([longer_line]) == ["ゆめゆめ", "ゆめゆめゆめ"]
    assert clean_lines([line_at_the_setting]) == [line_at_the_setting]
