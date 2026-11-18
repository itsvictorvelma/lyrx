"""Saved songs: one SQLite file holding each opened song and its lines in four versions."""

import logging
import sqlite3
import time
from collections.abc import Iterable, Iterator
from contextlib import closing, contextmanager

from pydantic import TypeAdapter, ValidationError

from lyrx import config
from lyrx.schemas import Song, SongVersionsResponse, VersionLine

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
    last_opened_at REAL NOT NULL
)
"""


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    """A connection to the file at `config.DATABASE_PATH`, created with its folder if missing.

    The `with` block is one transaction: committed when it ends, rolled back on an error.
    """
    config.DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(config.DATABASE_PATH)) as connection, connection:
        connection.execute(CREATE_TABLE)
        yield connection


def find_song(song_id: int) -> SongVersionsResponse | None:
    """The saved song, its last-opened time updated; None if not saved or its row is broken."""
    with connect() as connection:
        row = connection.execute(
            "SELECT id, track, artist, album, duration_seconds, lines_json"
            " FROM saved_songs WHERE id = ?",
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


def to_saved_song(row: tuple[int, str, str, str, int, str]) -> SongVersionsResponse | None:
    """The row as a reply, after the same checks as any untrusted data."""
    song_id, track, artist, album, duration_seconds, lines_json = row
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
    return SongVersionsResponse(song=song, lines=lines)


def save_song(reply: SongVersionsResponse) -> None:
    """Saves the song and its lines, replacing an earlier copy; both times are now."""
    song = reply.song
    now = time.time()
    with connect() as connection:
        connection.execute(
            "INSERT INTO saved_songs (id, track, artist, album, duration_seconds, lines_json,"
            " saved_at, last_opened_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
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


def list_songs() -> list[Song]:
    """Every saved song without its lines, most recently opened first."""
    with connect() as connection:
        rows = connection.execute(
            "SELECT id, track, artist, album, duration_seconds FROM saved_songs"
            " ORDER BY last_opened_at DESC, id DESC"
        ).fetchall()
    return [
        Song(id=song_id, track=track, artist=artist, album=album, duration_seconds=duration)
        for song_id, track, artist, album, duration in rows
    ]


def remove_song(song_id: int) -> bool:
    """Whether a saved song was removed."""
    with connect() as connection:
        cursor = connection.execute("DELETE FROM saved_songs WHERE id = ?", (song_id,))
        return cursor.rowcount > 0


def find_song_or_none(song_id: int) -> SongVersionsResponse | None:
    """Like `find_song`, but a database that cannot be read counts as "not saved"."""
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
    """Which of these song ids are saved."""
    wanted = list(song_ids)
    if not wanted:
        return set()
    placeholders = ", ".join("?" for _ in wanted)
    with connect() as connection:
        rows = connection.execute(
            # Only "?" placeholders are formatted in; the ids go in as parameters.
            f"SELECT id FROM saved_songs WHERE id IN ({placeholders})",
            wanted,
        ).fetchall()
    return {song_id for (song_id,) in rows}
