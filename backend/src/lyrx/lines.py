"""Splits the paste into lines, checks the size limits, and detects Japanese text."""

import unicodedata

from lyrx import config
from lyrx.errors import (
    ApiError,
    line_too_long_error,
    too_many_characters_error,
    too_many_lines_error,
)
from lyrx.kana import is_kana, is_kanji
from lyrx.schemas import Paste


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


def read_paste(lyrics: str) -> Paste:
    """The paste in NFC, so decomposed kana (か + U+3099) behaves like が, then split into lines."""
    text = unicodedata.normalize("NFC", lyrics)
    return Paste(text=text, lines=split_lines(text))


def count_characters(paste: str) -> int:
    """Counts the raw paste with each line ending as one character, before any trimming."""
    return len(normalize_line_endings(paste))


def check_limits(paste: str, lines: list[str]) -> None:
    """Refuses an empty paste, then one over the character, line, or line-length limit.

    `paste` is the raw text and `lines` is `split_lines(paste)`: characters are counted
    before trimming, lines after it, and line lengths on the lines as typed so the error can
    name the line number the learner sees.
    """
    if not lines:
        raise ApiError("empty_input")
    character_count = count_characters(paste)
    if character_count > config.MAX_CHARACTERS:
        raise too_many_characters_error(character_count)
    if len(lines) > config.MAX_LINES:
        raise too_many_lines_error(len(lines))
    long_line = find_first_long_line(paste)
    if long_line is not None:
        line_number, line_length = long_line
        raise line_too_long_error(line_number, line_length)


def find_first_long_line(paste: str) -> tuple[int, int] | None:
    """The 1-based number and length of the first line over the line-length limit, if any.

    Lines are numbered as typed, blank ones included; trailing whitespace is not measured,
    as in `split_lines`.
    """
    for line_number, raw_line in enumerate(normalize_line_endings(paste).split("\n"), start=1):
        line_length = len(raw_line.rstrip())
        if line_length > config.MAX_LINE_CHARACTERS:
            return line_number, line_length
    return None


def has_japanese(text: str) -> bool:
    return any(is_kana(character) or is_kanji(character) for character in text)
