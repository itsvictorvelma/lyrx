"""The shared pipeline: from cleaned lines to every line in its four versions."""

from collections.abc import Sequence

from lyrx.chunks import request_in_chunks
from lyrx.schemas import SongTranslation, VersionLine
from lyrx.translators import ReadyTranslator


def make_four_versions(
    lines: list[str], translators: Sequence[ReadyTranslator]
) -> tuple[list[VersionLine], SongTranslation]:
    """Every line in order with its versions, and the translation result for the log.

    Blank lines are not sent and stay blank in every version.
    """
    sent_lines = [(index, line) for index, line in enumerate(lines) if line]
    versions = request_in_chunks(sent_lines, translators)
    return [make_line(index, line, versions) for index, line in enumerate(lines)], versions


def make_line(index: int, original: str, versions: SongTranslation) -> VersionLine:
    """A sent line from its checked versions; a blank line stays blank."""
    if not original:
        return VersionLine(index=index, original="", hiragana="", romaji="", english="")
    line = versions.lines[index]
    return VersionLine(
        index=index,
        original=original,
        hiragana=line.hiragana,
        romaji=line.romaji,
        english=line.english,
    )
