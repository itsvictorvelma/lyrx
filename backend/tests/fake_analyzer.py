"""A fake Japanese analyzer: set words with set parts of speech and readings, and a call log.

`FakeAnalyzer` stands in for `lyrx.japanese_analyzer.analyze`. It is given, for each run of
text it may be asked about, the exact words to return. It records every run it was asked about,
so a test can check which runs reached the analyzer. A run it was not given fails the test.
"""

from lyrx.japanese_analyzer import Word
from lyrx.kana import to_hiragana

# UniDic part-of-speech names (pos1) used by the readings rules.
NOUN = "名詞"
PRONOUN = "代名詞"
VERB = "動詞"
PARTICLE = "助詞"
AUXILIARY_VERB = "助動詞"
SUFFIX = "接尾辞"
SUPPLEMENTARY_SYMBOL = "補助記号"
SYMBOL = "記号"


def to_katakana(text: str) -> str:
    """The katakana form of hiragana, as UniDic writes readings."""
    return "".join(
        chr(ord(character) + 0x60) if "ぁ" <= character <= "ゖ" else character for character in text
    )


def noun(surface: str, reading: str | None) -> Word:
    return Word(surface=surface, part_of_speech=NOUN, conjunctive=False, reading=reading)


def word(surface: str, part_of_speech: str, reading: str | None) -> Word:
    return Word(surface=surface, part_of_speech=part_of_speech, conjunctive=False, reading=reading)


def particle(surface: str, *, conjunctive: bool = False) -> Word:
    """A particle whose reading is its own kana, as UniDic gives it."""
    reading = to_katakana(to_hiragana(surface))
    return Word(surface=surface, part_of_speech=PARTICLE, conjunctive=conjunctive, reading=reading)


def symbol(surface: str) -> Word:
    """Punctuation or a bracket: UniDic gives it an empty reading."""
    return Word(surface=surface, part_of_speech=SUPPLEMENTARY_SYMBOL, conjunctive=False, reading="")


class UnscriptedRunError(AssertionError):
    """The code asked the fake about a run of text the test did not set up."""


class FakeAnalyzer:
    def __init__(self, words_by_run: dict[str, list[Word]]) -> None:
        self.words_by_run = words_by_run
        self.calls: list[str] = []

    def __call__(self, run: str) -> list[Word]:
        self.calls.append(run)
        if run not in self.words_by_run:
            raise UnscriptedRunError(f"no words set for run {run!r}")
        return list(self.words_by_run[run])
