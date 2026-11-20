"""The song cache and the library: one SQLite file of opened songs; `saved` marks the library."""

import logging
import sqlite3
import time
from collections.abc import Iterable, Iterator
from contextlib import closing, contextmanager

from pydantic import TypeAdapter, ValidationError

from lyrx import config
from lyrx.schemas import (
    Playback,
    RecentSong,
    SavedSong,
    Song,
    SongVersionsResponse,
    VersionLine,
)

logger = logging.getLogger(__name__)

LINES_ADAPTER = TypeAdapter(list[VersionLine])

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS saved_songs (
    id INTEGER PRIMARY KEY,
    track TEXT NOT NULL,
    artist TEXT NOT NULL,
    album TEXT NOT NULL,
    duration_seconds INTEGER NOT NULL,
    lines_json TEXT NOT NULL,
    saved_at REAL NOT NULL,
    last_opened_at REAL NOT NULL,
    video_id TEXT,
    offset_ms INTEGER NOT NULL DEFAULT 0,
    saved INTEGER NOT NULL DEFAULT 1
)
"""
# Columns added after the first release, with their definitions, for older library files.
# `saved` defaults to 1 so every song in an older library stays in the library.
ADDED_COLUMNS = {
    "video_id": "TEXT",
    "offset_ms": "INTEGER NOT NULL DEFAULT 0",
    "saved": "INTEGER NOT NULL DEFAULT 1",
}


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    """A connection to the file at `config.DATABASE_PATH`, created with its folder if missing.

    The `with` block is one transaction: committed when it ends, rolled back on an error.
    """
    config.DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(config.DATABASE_PATH)) as connection, connection:
        connection.execute(CREATE_TABLE)
        add_missing_columns(connection)
        yield connection


def add_missing_columns(connection: sqlite3.Connection) -> None:
    """Brings a library made by an older Lyrx up to date; existing rows get the defaults."""
    present = {row[1] for row in connection.execute("PRAGMA table_info(saved_songs)")}
    for name, definition in ADDED_COLUMNS.items():
        if name not in present:
            # Only names and definitions from ADDED_COLUMNS above are formatted in.
            connection.execute(f"ALTER TABLE saved_songs ADD COLUMN {name} {definition}")


def find_song(song_id: int) -> SongVersionsResponse | None:
    """The cached song, its last-opened time updated; None if not cached or its row is broken."""
    with connect() as connection:
        row = connection.execute(
            "SELECT id, track, artist, album, duration_seconds, lines_json, video_id, offset_ms,"
            " saved FROM saved_songs WHERE id = ?",
            (song_id,),
        ).fetchone()
        if row is None:
            return None
        saved = to_saved_song(row)
        if saved is None:
            connection.execute("DELETE FROM saved_songs WHERE id = ?", (song_id,))
            return None
        connection.execute(
            "UPDATE saved_songs SET last_opened_at = ? WHERE id = ?", (time.time(), song_id)
        )
        return saved


def to_saved_song(
    row: tuple[int, str, str, str, int, str, str | None, int, int],
) -> SongVersionsResponse | None:
    """The row as a reply, after the same checks as any untrusted data."""
    song_id, track, artist, album, duration_seconds, lines_json, video_id, offset_ms, saved = row
    try:
        lines = LINES_ADAPTER.validate_json(lines_json)
        song = Song(
            id=song_id,
            track=track,
            artist=artist,
            album=album,
            duration_seconds=duration_seconds,
        )
    except ValidationError:
        return None
    if [line.index for line in lines] != list(range(len(lines))):
        return None
    return SongVersionsResponse(
        song=song, lines=lines, playback=to_playback(video_id, offset_ms), saved=saved == 1
    )


def to_playback(video_id: str | None, offset_ms: int) -> Playback:
    """The saved video and nudge; a value that fails the checks is dropped, not the song."""
    try:
        return Playback.model_validate({"videoId": video_id, "offsetMs": offset_ms})
    except ValidationError:
        return Playback()


def save_playback(song_id: int, playback: Playback) -> bool:
    """Keeps a saved song's video and nudge; False when the song is not in the library."""
    with connect() as connection:
        cursor = connection.execute(
            "UPDATE saved_songs SET video_id = ?, offset_ms = ? WHERE id = ? AND saved = 1",
            (playback.video_id, playback.offset_ms, song_id),
        )
        return cursor.rowcount > 0


def save_song_to_library(song_id: int, playback: Playback) -> bool:
    """Puts a cached song in the library with its video and nudge; False when not cached."""
    with connect() as connection:
        cursor = connection.execute(
            "UPDATE saved_songs SET saved = 1, video_id = ?, offset_ms = ? WHERE id = ?",
            (playback.video_id, playback.offset_ms, song_id),
        )
        return cursor.rowcount > 0


def unsave_song(song_id: int) -> bool:
    """Takes a song out of the library, dropping its video and nudge; it stays cached."""
    with connect() as connection:
        cursor = connection.execute(
            "UPDATE saved_songs SET saved = 0, video_id = NULL, offset_ms = 0"
            " WHERE id = ? AND saved = 1",
            (song_id,),
        )
        return cursor.rowcount > 0


def replace_lines(song_id: int, lines: list[VersionLine]) -> None:
    """Stores a cached song's lines again, after missing lines were filled in."""
    with connect() as connection:
        connection.execute(
            "UPDATE saved_songs SET lines_json = ? WHERE id = ?",
            (LINES_ADAPTER.dump_json(lines).decode(), song_id),
        )


def cache_song(reply: SongVersionsResponse) -> None:
    """Caches the song and its lines, replacing an earlier copy; both times are now.

    A new song is not in the library (`saved = 0`); a new copy keeps `saved`, video, and nudge.
    """
    song = reply.song
    now = time.time()
    with connect() as connection:
        connection.execute(
            "INSERT INTO saved_songs (id, track, artist, album, duration_seconds, lines_json,"
            " saved_at, last_opened_at, saved) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)"
            " ON CONFLICT(id) DO UPDATE SET track = excluded.track, artist = excluded.artist,"
            " album = excluded.album, duration_seconds = excluded.duration_seconds,"
            " lines_json = excluded.lines_json, saved_at = excluded.saved_at,"
            " last_opened_at = excluded.last_opened_at",
            (
                song.id,
                song.track,
                song.artist,
                song.album,
                song.duration_seconds,
                LINES_ADAPTER.dump_json(reply.lines).decode(),
                now,
                now,
            ),
        )


def list_songs() -> list[SavedSong]:
    """Every song in the library without its lines, most recently opened first."""
    with connect() as connection:
        rows = connection.execute(
            "SELECT id, track, artist, album, duration_seconds, video_id, offset_ms,"
            " last_opened_at FROM saved_songs WHERE saved = 1"
            " ORDER BY last_opened_at DESC, id DESC"
        ).fetchall()
    songs = []
    for song_id, track, artist, album, duration, video_id, offset_ms, opened_at in rows:
        playback = to_playback(video_id, offset_ms)
        songs.append(
            SavedSong(
                id=song_id,
                track=track,
                artist=artist,
                album=album,
                duration_seconds=duration,
                video_id=playback.video_id,
                offset_ms=playback.offset_ms,
                last_opened_at=round(opened_at * 1000),
            )
        )
    return songs


def list_recent_songs(limit: int) -> list[RecentSong]:
    """Cached songs, saved or not, most recently opened first, without their lines."""
    with connect() as connection:
        rows = connection.execute(
            "SELECT id, track, artist, album, duration_seconds, video_id FROM saved_songs"
            " ORDER BY last_opened_at DESC, id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [
        RecentSong(
            id=song_id,
            track=track,
            artist=artist,
            album=album,
            duration_seconds=duration,
            video_id=to_playback(video_id, 0).video_id,
        )
        for song_id, track, artist, album, duration, video_id in rows
    ]


def find_song_or_none(song_id: int) -> SongVersionsResponse | None:
    """Like `find_song`, but a database that cannot be read counts as "not cached"."""
    try:
        return find_song(song_id)
    except sqlite3.Error:
        logger.warning("library_unavailable")
        return None


def saved_ids_or_none(song_ids: Iterable[int]) -> set[int]:
    """Like `saved_ids`, but a database that cannot be read counts as "none saved"."""
    try:
        return saved_ids(song_ids)
    except sqlite3.Error:
        logger.warning("library_unavailable")
        return set()


def saved_ids(song_ids: Iterable[int]) -> set[int]:
    """Which of these song ids are in the library."""
    wanted = list(song_ids)
    if not wanted:
        return set()
    placeholders = ", ".join("?" for _ in wanted)
    with connect() as connection:
        rows = connection.execute(
            # Only "?" placeholders are formatted in; the ids go in as parameters.
            f"SELECT id FROM saved_songs WHERE saved = 1 AND id IN ({placeholders})",
            wanted,
        ).fetchall()
    return {song_id for (song_id,) in rows}
