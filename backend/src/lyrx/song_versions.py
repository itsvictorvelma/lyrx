"""Open a song: from an LRCLIB id to the song's lines in four versions."""

import httpx2

from lyrx import lrclib
from lyrx.errors import ApiError
from lyrx.four_versions import make_four_versions
from lyrx.lines import read_lyrics
from lyrx.looks_japanese import looks_japanese
from lyrx.schemas import GeminiVersions, LrclibRecord, Song, VersionLine


def open_song(
    record_id: int,
    api_key: str,
    lrclib_transport: httpx2.BaseTransport,
    gemini_transport: httpx2.BaseTransport,
) -> tuple[Song, list[str], list[VersionLine], GeminiVersions]:
    """The song, its cleaned lines (for the log), its versions, and Gemini's result."""
    record = lrclib.get_record(record_id, lrclib_transport)
    lines = read_lyrics(record.plain_lyrics or "") if not record.instrumental else []
    if not looks_japanese(lines):
        raise ApiError("song_not_japanese")
    versions, gemini_result = make_four_versions(lines, api_key, gemini_transport)
    return to_song(record), lines, versions, gemini_result


def to_song(record: LrclibRecord) -> Song:
    return Song(
        id=record.id,
        track=record.track_name,
        artist=record.artist_name,
        album=record.album_name or "",
        duration_seconds=round(record.duration),
    )
