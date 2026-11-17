"""Turns one lyric line into its hiragana, word by word, using the Japanese analyzer."""

import unicodedata
from collections.abc import Callable
from dataclasses import dataclass

from lyrx import japanese_analyzer
from lyrx.japanese_analyzer import Word
from lyrx.kana import is_kana, is_kanji, to_hiragana
from lyrx.lines import has_japanese

PARTICLE = "助詞"
# Parts of speech that join the piece before them with no space.
JOINS_PIECE_BEFORE = frozenset({"助動詞", "接尾辞", "補助記号", "記号"})
# An opening bracket joins the piece after it instead.
OPENING_BRACKETS = frozenset("「『\uff08([【")  # \uff08 is the full-width (
PARTICLES_READ_WA_AND_E = frozenset({"は", "へ"})
# Small ke (ヶ, ヵ, in hiragana ゖ, ゕ) is read か or が, as in 三ヶ月 and 関ヶ原.
SMALL_KE = frozenset("\u3096\u3095")
SMALL_KE_READINGS = frozenset("かが")

Analyze = Callable[[str], list[Word]]


@dataclass(frozen=True)
class LineReading:
    """A line's hiragana, whether every kanji reading passed its checks, and which words
    (positions in `hiragana.split(" ")`) are the particles は and へ."""

    hiragana: str
    reading_verified: bool
    particle_word_indexes: frozenset[int]


@dataclass(frozen=True)
class Piece:
    """The hiragana of one word, and how it sits next to its neighbours."""

    text: str
    verified: bool
    joins_before: bool
    joins_after: bool
    is_particle_wa_or_e: bool


def read_line(line: str, analyze: Analyze = japanese_analyzer.analyze) -> LineReading:
    """The hiragana of a line; each whitespace-separated run is analyzed on its own."""
    pieces = [piece for run in line.split() for piece in pieces_of_run(run, analyze)]
    words = group_into_words(pieces)
    return LineReading(
        hiragana=" ".join("".join(piece.text for piece in word) for word in words),
        reading_verified=all(piece.verified for piece in pieces),
        particle_word_indexes=frozenset(
            index for index, word in enumerate(words) if is_particle_word(word)
        ),
    )


def pieces_of_run(run: str, analyze: Analyze) -> list[Piece]:
    """One piece per word; a run with no Japanese is one piece, kept as written."""
    if not has_japanese(run):
        return [piece_of_plain_run(run)]
    return [piece_of_word(word) for word in analyze(run)]


def piece_of_plain_run(run: str) -> Piece:
    """A run of only punctuation or symbols joins the piece before, or the piece after when
    it ends with an opening bracket; any other run stands alone."""
    if not all(unicodedata.category(character)[0] in "PS" for character in run):
        return Piece(run, True, False, False, False)
    opens = run[-1] in OPENING_BRACKETS
    return Piece(run, True, joins_before=not opens, joins_after=opens, is_particle_wa_or_e=False)


def piece_of_word(word: Word) -> Piece:
    text, verified = read_word(word)
    is_particle = word.part_of_speech == PARTICLE and not word.conjunctive
    return Piece(
        text=text,
        verified=verified,
        joins_before=joins_piece_before(word),
        joins_after=word.surface in OPENING_BRACKETS,
        is_particle_wa_or_e=is_particle and text in PARTICLES_READ_WA_AND_E,
    )


def joins_piece_before(word: Word) -> bool:
    """Auxiliary verbs, suffixes, conjunctive particles, and punctuation other than an
    opening bracket join the piece before them."""
    if word.surface in OPENING_BRACKETS:
        return False
    return word.part_of_speech in JOINS_PIECE_BEFORE or word.conjunctive


def read_word(word: Word) -> tuple[str, bool]:
    """A word's hiragana and whether it is verified.

    A word with no kanji is its own spelling in hiragana. A kanji word takes the dictionary
    reading, checked against its kana; with no usable reading it is kept as written.
    """
    if not any(is_kanji(character) for character in word.surface):
        return to_hiragana(word.surface), True
    # ponytail: a counter after a digit (人 in 2人) gets its own dictionary reading, which may
    # not be the one a singer uses (ふたり). Reading numbers with their counters would fix it.
    if not word.reading or not all(is_kana(character) for character in word.reading):
        return word.surface, False
    reading = to_hiragana(word.reading)
    return reading, keeps_outer_kana(to_hiragana(word.surface), reading)


def keeps_outer_kana(surface: str, reading: str) -> bool:
    """The kana at the start and end of the word also start and end its reading."""
    leading = leading_kana(surface)
    trailing = leading_kana(surface[::-1])[::-1]
    reading_end = reading[len(reading) - len(trailing) :]
    return same_kana(leading, reading[: len(leading)]) and same_kana(trailing, reading_end)


def same_kana(written: str, read: str) -> bool:
    """Equal kana, except that a small ke in the word matches か or が in the reading."""
    return len(written) == len(read) and all(
        word_kana == reading_kana or (word_kana in SMALL_KE and reading_kana in SMALL_KE_READINGS)
        for word_kana, reading_kana in zip(written, read, strict=True)
    )


def leading_kana(text: str) -> str:
    for index, character in enumerate(text):
        if not is_kana(character):
            return text[:index]
    return text


def group_into_words(pieces: list[Piece]) -> list[list[Piece]]:
    """Groups pieces into the space-separated words of the hiragana."""
    words: list[list[Piece]] = []
    for index, piece in enumerate(pieces):
        joins_previous = index > 0 and (piece.joins_before or pieces[index - 1].joins_after)
        if joins_previous:
            words[-1].append(piece)
        else:
            words.append([piece])
    return words


def is_particle_word(word: list[Piece]) -> bool:
    """A word whose only kana comes from one particle は or へ."""
    with_kana = [piece for piece in word if any(is_kana(character) for character in piece.text)]
    return len(with_kana) == 1 and with_kana[0].is_particle_wa_or_e
