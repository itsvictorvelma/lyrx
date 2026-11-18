"""The shared pipeline: from cleaned lines to every line in its four versions."""

import httpx2

from lyrx.chunks import request_in_chunks
from lyrx.schemas import GeminiVersions, VersionLine


def make_four_versions(
    lines: list[str], api_key: str, client: httpx2.Client
) -> tuple[list[VersionLine], GeminiVersions]:
    """Every line in order with Gemini's versions, and Gemini's result for the log.

    Blank lines are not sent and stay blank in every version.
    """
    sent_lines = [(index, line) for index, line in enumerate(lines) if line]
    versions = request_in_chunks(sent_lines, api_key, client)
    return [make_line(index, line, versions) for index, line in enumerate(lines)], versions


def make_line(index: int, original: str, versions: GeminiVersions) -> VersionLine:
    """A sent line from Gemini's checked versions; a blank line stays blank."""
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
