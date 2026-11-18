"""Splits lyrics into cleaned lines, and detects Japanese text."""

import unicodedata

from lyrx.errors import ApiError
from lyrx.kana import is_kana, is_kanji
from lyrx.lyric_cleanup import clean_lines, tidy_blank_lines


def normalize_line_endings(paste: str) -> str:
    return paste.replace("\r\n", "\n").replace("\r", "\n")


def split_lines(paste: str) -> list[str]:
    """Trailing whitespace off, blank lines at the ends dropped, blank runs collapsed to one."""
    return tidy_blank_lines([line.rstrip() for line in normalize_line_endings(paste).split("\n")])


def read_paste(lyrics: str) -> list[str]:
    """The paste split and cleaned. An empty paste is refused before cleanup."""
    if not split_lines(lyrics):
        raise ApiError("empty_input")
    return read_lyrics(lyrics)


def read_lyrics(lyrics: str) -> list[str]:
    """Lyrics in NFC, so decomposed kana (か + U+3099) behaves like が, split and cleaned."""
    lines = split_lines(unicodedata.normalize("NFC", lyrics))
    return clean_lines(lines) if lines else []


def has_japanese(text: str) -> bool:
    return any(is_kana(character) or is_kanji(character) for character in text)
