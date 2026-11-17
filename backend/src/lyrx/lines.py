"""Splits the paste into lines, checks the size limits, and detects Japanese text."""

import unicodedata

from lyrx import config
from lyrx.errors import ApiError, size_limit_details
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
    before trimming, lines after it.
    """
    if not lines:
        raise ApiError("empty_input")
    if count_characters(paste) > config.MAX_CHARACTERS:
        raise ApiError("input_too_large", details=size_limit_details())
    if len(lines) > config.MAX_LINES:
        raise ApiError("input_too_large", details=size_limit_details())
    if any(len(line) > config.MAX_LINE_CHARACTERS for line in lines):
        raise ApiError("input_too_large", details=size_limit_details())


def has_japanese(text: str) -> bool:
    return any(is_kana(character) or is_kanji(character) for character in text)
