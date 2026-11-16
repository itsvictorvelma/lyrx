"""Splits the paste into lines, checks the size limits, and detects Japanese text."""

from lyrx import config
from lyrx.errors import ApiError, size_limit_details

# Inclusive Unicode code point ranges, grouped by kind.

# Kana
HIRAGANA = (0x3041, 0x3096)  # ぁ .. ゖ
HIRAGANA_ITERATION_MARKS = (0x309D, 0x309E)  # ゝ ゞ
KATAKANA = (0x30A1, 0x30FA)  # ァ .. ヺ
KATAKANA_LONG_MARK = (0x30FC, 0x30FC)  # ー
KATAKANA_ITERATION_MARKS = (0x30FD, 0x30FE)  # ヽ ヾ
KANA_RANGES = (
    HIRAGANA,
    HIRAGANA_ITERATION_MARKS,
    KATAKANA,
    KATAKANA_LONG_MARK,
    KATAKANA_ITERATION_MARKS,
)

# Kanji
KANJI_REPEAT_MARK = (0x3005, 0x3005)  # 々
SHIME = (0x3006, 0x3006)  # 〆
CJK_EXTENSION_A = (0x3400, 0x4DBF)  # 㐀 .. end of the block
CJK_UNIFIED_IDEOGRAPHS = (0x4E00, 0x9FFF)  # 一 .. end of the block
CJK_COMPATIBILITY_IDEOGRAPHS = (0xF900, 0xFAFF)  # 豈 .. end of the block
KANJI_RANGES = (
    KANJI_REPEAT_MARK,
    SHIME,
    CJK_EXTENSION_A,
    CJK_UNIFIED_IDEOGRAPHS,
    CJK_COMPATIBILITY_IDEOGRAPHS,
)


def normalize_line_endings(paste: str) -> str:
    return paste.replace("\r\n", "\n").replace("\r", "\n")


def split_lines(paste: str) -> list[str]:
    """Trailing whitespace off, blank lines at the ends dropped, blank runs collapsed to one."""
    lines: list[str] = []
    for raw_line in normalize_line_endings(paste).split("\n"):
        line = raw_line.rstrip()
        if line == "" and (not lines or lines[-1] == ""):
            continue
        lines.append(line)
    if lines and lines[-1] == "":
        lines.pop()
    return lines


def count_characters(paste: str) -> int:
    """Counts the raw paste with each line ending as one character, before any trimming."""
    return len(normalize_line_endings(paste))


def check_limits(paste: str, lines: list[str]) -> None:
    """Refuses an empty paste, then one over the character limit, then one over the line limit.

    `paste` is the raw text and `lines` is `split_lines(paste)`: characters are counted
    before trimming, lines after it.
    """
    if not lines:
        raise ApiError("empty_input")
    if count_characters(paste) > config.MAX_CHARACTERS:
        raise ApiError("input_too_large", details=size_limit_details())
    if len(lines) > config.MAX_LINES:
        raise ApiError("input_too_large", details=size_limit_details())


def in_ranges(character: str, ranges: tuple[tuple[int, int], ...]) -> bool:
    return any(first <= ord(character) <= last for first, last in ranges)


def is_kana(character: str) -> bool:
    return in_ranges(character, KANA_RANGES)


def is_kanji(character: str) -> bool:
    return in_ranges(character, KANJI_RANGES)


def has_japanese(text: str) -> bool:
    return any(is_kana(character) or is_kanji(character) for character in text)
