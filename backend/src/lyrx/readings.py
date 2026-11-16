"""Checks Claude's hiragana reading of a line: the hard check and the kana-kept comparison."""

import unicodedata

from lyrx import config
from lyrx.kana import is_hiragana_letter, is_kanji, to_hiragana

ASCII_SPACE = " "
# The long mark ー and the iteration marks ゝ ゞ: a kanji run's reading may hold them
# after its first hiragana letter.
KANJI_READING_MARKS = "ーゝゞ"


def tidy_reading(reading: str) -> str:
    """NFC, then trims and collapses ASCII spaces. Tabs and full-width spaces are left alone."""
    words = unicodedata.normalize("NFC", reading).split(ASCII_SPACE)
    return ASCII_SPACE.join(word for word in words if word)


def is_reading_character(character: str) -> bool:
    """Hiragana letters, the iteration marks ゝ ゞ, and the long mark ー."""
    return is_hiragana_letter(character) or character in KANJI_READING_MARKS


def has_only_single_inner_spaces(reading: str) -> bool:
    return not (
        reading.startswith(ASCII_SPACE)
        or reading.endswith(ASCII_SPACE)
        or ASCII_SPACE * 2 in reading
    )


def is_allowed_character(character: str, original: str) -> bool:
    if character == ASCII_SPACE:
        return True
    if character.isspace():
        return False
    return is_reading_character(character) or character in original


def has_allowed_length(original: str, reading: str) -> bool:
    """Not empty for a non-empty line (AC-47), and at most 6 times the line's length (AC-46)."""
    if original and not reading:
        return False
    return len(reading) <= config.MAX_READING_LENGTH_FACTOR * len(original)


def reading_is_allowed(original: str, reading: str) -> bool:
    """Rule 5: hiragana, ー, single inner spaces, and other characters only if in the original.

    The length bound runs first, so the kana-kept comparison only ever sees bounded input.
    """
    return (
        has_allowed_length(original, reading)
        and has_only_single_inner_spaces(reading)
        and all(is_allowed_character(character, original) for character in reading)
    )


def remove_whitespace(text: str) -> str:
    return "".join(character for character in text if not character.isspace())


def split_into_tokens(original: str) -> list[str]:
    """Cuts the original into kanji runs (々 included) and single characters of everything else."""
    tokens: list[str] = []
    for character in original:
        if is_kanji(character) and tokens and is_kanji(tokens[-1][0]):
            tokens[-1] += character
        else:
            tokens.append(character)
    return tokens


def match_literal(token: str, reading: str, reachable: list[bool]) -> list[bool]:
    """A literal token moves every reachable position forward by one if the character matches."""
    after = [False] * len(reachable)
    for position in range(len(reading)):
        if reachable[position] and reading[position] == token:
            after[position + 1] = True
    return after


def match_kanji_run(reading: str, reachable: list[bool]) -> list[bool]:
    """A kanji run reads as a hiragana letter, then any reading characters, from a reachable spot.

    One left-to-right sweep: a stretch of reading characters becomes active at a reachable
    hiragana letter, and every position inside an active stretch can end the run.
    """
    after = [False] * len(reachable)
    active = False
    for position, character in enumerate(reading):
        if not is_reading_character(character):
            active = False
            continue
        if reachable[position] and is_hiragana_letter(character):
            active = True
        if active:
            after[position + 1] = True
    return after


def reading_keeps_kana(original: str, reading: str) -> bool:
    """Rule 6: the reading keeps every non-kanji character of the original, in order.

    Whitespace is removed from both and katakana in the original becomes hiragana. The
    matcher then walks the original's tokens one at a time, keeping `reachable[p]`: can
    the tokens so far match exactly `reading[:p]`? Each token turns that list into the next
    in one pass over the reading, so the cost is tokens times reading length: quadratic, with
    no regex and no backtracking. It stays bounded because a line is at most 200 characters
    (AC-45) and `reading_is_allowed` refuses a reading over 6 times its line (AC-46) first.
    The reading keeps the kana when `reachable[len(reading)]` is true at the end.
    """
    original = to_hiragana(remove_whitespace(original))
    reading = remove_whitespace(reading)
    reachable = [position == 0 for position in range(len(reading) + 1)]
    for token in split_into_tokens(original):
        if is_kanji(token[0]):
            reachable = match_kanji_run(reading, reachable)
        else:
            reachable = match_literal(token, reading, reachable)
    return reachable[len(reading)]
