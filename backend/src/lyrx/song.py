"""Open a song: from an LRCLIB id to every lyric line in its four versions."""

from collections.abc import Sequence

import httpx2

from lyrx.errors import ApiError
from lyrx.lyrics import lrclib
from lyrx.lyrics.japanese import looks_japanese
from lyrx.lyrics.lines import read_lyrics, start_times
from lyrx.schemas import Song, VersionLine
from lyrx.translation.chain import ReadyTranslator
from lyrx.translation.chunks import MISSING, request_in_chunks
from lyrx.translation.results import SongTranslation


def open_song(
    record_id: int,
    translators: Sequence[ReadyTranslator],
    lrclib_client: httpx2.Client,
) -> tuple[Song, list[str], list[VersionLine], SongTranslation]:
    """The song, its lines (for the log), every line's versions, and the translation result.

    Blank lines are not sent to the translators and stay blank in every version.
    """
    record = lrclib.get_record(record_id, lrclib_client)
    lines = read_lyrics(record.plain_lyrics or "") if not record.instrumental else []
    if not looks_japanese(lines):
        raise ApiError("song_not_japanese")
    sent_lines = [(index, line) for index, line in enumerate(lines) if line]
    translation = request_in_chunks(sent_lines, translators)
    starts = start_times(lines, record.synced_lyrics)
    versions = [
        make_line(index, line, translation, start)
        for index, (line, start) in enumerate(zip(lines, starts, strict=True))
    ]
    return lrclib.to_song(record), lines, versions, translation


def make_line(
    index: int, original: str, translation: SongTranslation, start_ms: int | None
) -> VersionLine:
    """A sent line from its checked versions and its start time; a blank line stays blank."""
    if not original:
        return VersionLine(index=index, original="", hiragana="", romaji="", english="")
    line = translation.lines[index]
    return VersionLine(
        index=index,
        original=original,
        hiragana=line.hiragana,
        romaji=line.romaji,
        english=line.english,
        start_ms=start_ms,
    )


def missing_lines(versions: Sequence[VersionLine]) -> list[VersionLine]:
    """Lines with text but no versions: the translators could not do them yet."""
    return [
        line
        for line in versions
        if line.original and not (line.hiragana or line.romaji or line.english)
    ]


def fill_missing_lines(
    versions: Sequence[VersionLine], translators: Sequence[ReadyTranslator]
) -> tuple[list[VersionLine], SongTranslation]:
    """The lines with any missing ones that now pass filled in, and the translation result.

    Only the missing lines are sent, with the whole song as context. A line that was already
    done is never replaced; a line that fails again stays missing.
    """
    wanted = [(line.index, line.original) for line in missing_lines(versions)]
    whole_song = [(line.index, line.original) for line in versions if line.original]
    translation = request_in_chunks(wanted, translators, whole_song)
    filled = [
        line
        if translation.lines.get(line.index, MISSING) == MISSING
        else make_line(line.index, line.original, translation, line.start_ms)
        for line in versions
    ]
    return filled, translation
