"""Open a song: from an LRCLIB id to the song's lines in four versions."""

from collections.abc import Sequence

import httpx2

from lyrx import lrclib
from lyrx.errors import ApiError
from lyrx.four_versions import make_four_versions
from lyrx.lines import read_lyrics
from lyrx.looks_japanese import looks_japanese
from lyrx.schemas import LrclibRecord, Song, SongTranslation, VersionLine
from lyrx.translators import ReadyTranslator


def open_song(
    record_id: int,
    translators: Sequence[ReadyTranslator],
    lrclib_client: httpx2.Client,
) -> tuple[Song, list[str], list[VersionLine], SongTranslation]:
    """The song, its cleaned lines (for the log), its versions, and the translation result."""
    record = lrclib.get_record(record_id, lrclib_client)
    lines = read_lyrics(record.plain_lyrics or "") if not record.instrumental else []
    if not looks_japanese(lines):
        raise ApiError("song_not_japanese")
    versions, translation = make_four_versions(lines, translators)
    return to_song(record), lines, versions, translation


def to_song(record: LrclibRecord) -> Song:
    return Song(
        id=record.id,
        track=record.track_name,
        artist=record.artist_name,
        album=record.album_name or "",
        duration_seconds=round(record.duration),
    )
