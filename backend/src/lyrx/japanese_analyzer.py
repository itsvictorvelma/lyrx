"""Cuts a run of Japanese text into dictionary words with their part of speech and reading."""

import threading
from dataclasses import dataclass
from typing import Any

import fugashi

CONJUNCTIVE_PARTICLE = "接続助詞"
# Full-width digits (U+FF10 to U+FF19) become 0 to 9. Same length, one to one, so a
# word's position in the copy is its position in the run.
FULL_WIDTH_DIGITS_TO_ASCII = {0xFF10 + digit: ord("0") + digit for digit in range(10)}

# A MeCab tagger is not safe to share across threads; FastAPI runs routes in a threadpool.
tagger = fugashi.Tagger()
tagger_lock = threading.Lock()


@dataclass(frozen=True)
class Word:
    """One dictionary word as written in the run.

    `part_of_speech` is UniDic's pos1, `conjunctive` is true when pos2 is 接続助詞, and
    `reading` is UniDic's kana field (katakana), or None when the dictionary has none.
    """

    surface: str
    part_of_speech: str
    conjunctive: bool
    reading: str | None


def analyze(run: str) -> list[Word]:
    """The words of one run of text, each written exactly as in the run."""
    analysis_copy = run.translate(FULL_WIDTH_DIGITS_TO_ASCII)
    with tagger_lock:
        tagged = [tag_node(node) for node in tagger(analysis_copy)]
    return written_as_in_run(run, analysis_copy, tagged)


def tag_node(node: Any) -> Word:
    """Reads one fugashi node (untyped) into a Word while the tagger still owns it."""
    features = node.feature
    surface: str = node.surface
    part_of_speech: str = features.pos1
    reading: str | None = features.kana
    conjunctive = features.pos2 == CONJUNCTIVE_PARTICLE
    return Word(surface, part_of_speech, conjunctive, reading)


def written_as_in_run(run: str, analysis_copy: str, words: list[Word]) -> list[Word]:
    """Each word's surface taken from the original run at the word's position in the copy."""
    written: list[Word] = []
    position = 0
    for word in words:
        start = analysis_copy.find(word.surface, position)
        if start < 0:
            raise RuntimeError("analyzer word not found in its run")
        position = start + len(word.surface)
        written.append(
            Word(run[start:position], word.part_of_speech, word.conjunctive, word.reading)
        )
    return written
