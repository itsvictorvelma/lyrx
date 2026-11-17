"""Cleans lyrics line by line: removes unwanted characters and repairs lost line breaks."""

import re
import unicodedata

from lyrx import config

ZERO_WIDTH_CHARACTERS = frozenset("\u200b\u200c\u200d\u2060\ufeff")
HANGUL_RANGES = (
    (0x1100, 0x11FF),  # Hangul Jamo
    (0x3130, 0x318F),  # Hangul Compatibility Jamo
    (0xA960, 0xA97F),  # Hangul Jamo Extended-A
    (0xAC00, 0xD7AF),  # Hangul Syllables
    (0xD7B0, 0xD7FF),  # Hangul Jamo Extended-B
    (0xFFA0, 0xFFDC),  # half-width Hangul
)
CLOSING_BRACKET_FOR = {
    "(": ")",
    "\uff08": "\uff09",
    "[": "]",
    "\uff3b": "\uff3d",
    "「": "」",
    "【": "】",
}
BRACKETS = frozenset(CLOSING_BRACKET_FOR) | frozenset(CLOSING_BRACKET_FOR.values())

# Each pattern is a single character class: the regex engine never backtracks, so time is linear.
COLLAPSIBLE_SPACES = re.compile("[ \t\u00a0]+")
SPLIT_WHITESPACE = re.compile("[ \t\u00a0\u3000]+")
AFTER_SENTENCE_END = re.compile("(?<=[。\uff01\uff1f!?])(?=[^。\uff01\uff1f!?])")


def remove_unwanted_characters(line: str) -> str:
    """The line without zero-width characters, Hangul, and brackets left holding no text."""
    kept = [character for character in line if not is_unwanted(character)]
    return remove_empty_brackets(kept)


def is_unwanted(character: str) -> bool:
    code_point = ord(character)
    if character in ZERO_WIDTH_CHARACTERS:
        return True
    return any(first <= code_point <= last for first, last in HANGUL_RANGES)


def remove_empty_brackets(characters: list[str]) -> str:
    """Drops each bracket pair holding only whitespace or punctuation, in one pass.

    `open_at` is where the latest opening bracket sits in `kept` while everything after it
    is whitespace or punctuation; any other character clears it. Each character is added
    and deleted at most once, so the pass stays linear.
    """
    kept: list[str] = []
    open_at: int | None = None
    for character in characters:
        if character in CLOSING_BRACKET_FOR:
            open_at = len(kept)
        elif open_at is not None and character == CLOSING_BRACKET_FOR[kept[open_at]]:
            del kept[open_at:]
            open_at = None
            continue
        elif character in BRACKETS or not is_blank_or_punctuation(character):
            open_at = None
        kept.append(character)
    return "".join(kept)


def is_blank_or_punctuation(character: str) -> bool:
    return character.isspace() or unicodedata.category(character).startswith("P")


def clean_lines(lines: list[str]) -> list[str]:
    """Each line cleaned and long lines split; blank lines kept once, never at the ends."""
    cleaned: list[str] = []
    for line in lines:
        if line == "":
            cleaned.append(line)
            continue
        cleaned.extend(split_long_line(clean_line(line)))
    return tidy_blank_lines(cleaned)


def clean_line(line: str) -> str:
    """Removes unwanted characters; spaces collapse only where something was removed."""
    removed = remove_unwanted_characters(line)
    if removed != line:
        removed = COLLAPSIBLE_SPACES.sub(" ", removed)
    return removed.strip()


def split_long_line(line: str) -> list[str]:
    """A line over the split length cut at whitespace, then pieces still too long cut after
    sentence-ending marks. An empty line gives no pieces."""
    if len(line) <= config.CLEANUP_SPLIT_LENGTH:
        return [line] if line else []
    pieces: list[str] = []
    for piece in SPLIT_WHITESPACE.split(line):
        if len(piece) > config.CLEANUP_SPLIT_LENGTH:
            pieces.extend(AFTER_SENTENCE_END.split(piece))
        else:
            pieces.append(piece)
    return [piece.strip() for piece in pieces if piece.strip()]


def tidy_blank_lines(lines: list[str]) -> list[str]:
    """Drops blank lines at both ends and collapses each run of blank lines to one."""
    tidy: list[str] = []
    for line in lines:
        if line == "" and (not tidy or tidy[-1] == ""):
            continue
        tidy.append(line)
    if tidy and tidy[-1] == "":
        tidy.pop()
    return tidy
