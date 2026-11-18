"""Open a song: from an LRCLIB id to every lyric line in its four versions."""

from collections.abc import Sequence

import httpx2

from lyrx.errors import ApiError
from lyrx.lyrics import lrclib
from lyrx.lyrics.japanese import looks_japanese
from lyrx.lyrics.lines import read_lyrics, start_times
from lyrx.lyrics.lrclib import LrclibRecord
from lyrx.schemas import Song, VersionLine
from lyrx.translation.chain import ReadyTranslator
from lyrx.translation.chunks import request_in_chunks
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
    return to_song(record), lines, versions, translation


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


def to_song(record: LrclibRecord) -> Song:
    return Song(
        id=record.id,
        track=record.track_name,
        artist=record.artist_name,
        album=record.album_name or "",
        duration_seconds=round(record.duration),
    )
