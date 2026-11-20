"""The shared song cache and each person's library of saved songs, with their videos."""

import logging
import sqlite3
import time
from collections.abc import Iterable

from pydantic import TypeAdapter, ValidationError

from lyrx.database import connect
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


def find_song(song_id: int) -> SongVersionsResponse | None:
    """The cached song, its last-opened time updated; None if not cached or its row is broken.

    A database that cannot be read counts as "not cached".
    """
    try:
        return read_cached_song(song_id)
    except sqlite3.Error:
        logger.warning("library_unavailable")
        return None


def read_cached_song(song_id: int) -> SongVersionsResponse | None:
    with connect() as connection:
        row = connection.execute(
            "SELECT id, track, artist, album, duration_seconds, lines_json FROM songs WHERE id = ?",
            (song_id,),
        ).fetchone()
        if row is None:
            return None
        cached = to_cached_song(row)
        if cached is None:
            connection.execute("DELETE FROM songs WHERE id = ?", (song_id,))
            return None
        connection.execute(
            "UPDATE songs SET last_opened_at = ? WHERE id = ?", (time.time(), song_id)
        )
        return cached


def to_cached_song(row: tuple[int, str, str, str, int, str]) -> SongVersionsResponse | None:
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


def with_library_entry(reply: SongVersionsResponse, user_id: int) -> SongVersionsResponse:
    """The reply with this person's saved mark and video; their last-opened time updated."""
    with connect() as connection:
        row = connection.execute(
            "SELECT video_id, offset_ms FROM library_entries WHERE user_id = ? AND song_id = ?",
            (user_id, reply.song.id),
        ).fetchone()
        if row is None:
            return reply.model_copy(update={"saved": False, "playback": Playback()})
        connection.execute(
            "UPDATE library_entries SET last_opened_at = ? WHERE user_id = ? AND song_id = ?",
            (time.time(), user_id, reply.song.id),
        )
    return reply.model_copy(update={"saved": True, "playback": to_playback(*row)})


def to_playback(video_id: str | None, offset_ms: int) -> Playback:
    """The saved video and nudge; a value that fails the checks is dropped, not the song."""
    try:
        return Playback.model_validate({"videoId": video_id, "offsetMs": offset_ms})
    except ValidationError:
        return Playback()


def save_playback(user_id: int, song_id: int, playback: Playback) -> bool:
    """Keeps a saved song's video and nudge; False when it is not in this person's library."""
    with connect() as connection:
        cursor = connection.execute(
            "UPDATE library_entries SET video_id = ?, offset_ms = ?"
            " WHERE user_id = ? AND song_id = ?",
            (playback.video_id, playback.offset_ms, user_id, song_id),
        )
        return cursor.rowcount > 0


def save_song_to_library(user_id: int, song_id: int, playback: Playback) -> bool:
    """Puts a cached song in this person's library with its video and nudge; False when not
    cached. Saving it again replaces the video and nudge."""
    now = time.time()
    with connect() as connection:
        cursor = connection.execute(
            "INSERT INTO library_entries (user_id, song_id, video_id, offset_ms, saved_at,"
            " last_opened_at) SELECT ?, id, ?, ?, ?, ? FROM songs WHERE id = ?"
            " ON CONFLICT (user_id, song_id) DO UPDATE SET video_id = excluded.video_id,"
            " offset_ms = excluded.offset_ms",
            (user_id, playback.video_id, playback.offset_ms, now, now, song_id),
        )
        return cursor.rowcount > 0


def unsave_song(user_id: int, song_id: int) -> bool:
    """Takes a song out of this person's library with its video; it stays cached."""
    with connect() as connection:
        cursor = connection.execute(
            "DELETE FROM library_entries WHERE user_id = ? AND song_id = ?", (user_id, song_id)
        )
        return cursor.rowcount > 0


def replace_lines(song_id: int, lines: list[VersionLine]) -> None:
    """Stores a cached song's lines again, after missing lines were filled in."""
    with connect() as connection:
        connection.execute(
            "UPDATE songs SET lines_json = ? WHERE id = ?",
            (LINES_ADAPTER.dump_json(lines).decode(), song_id),
        )


def cache_song(reply: SongVersionsResponse) -> None:
    """Caches the song and its lines, replacing an earlier copy; both times are now.

    Library rows are separate, so a new copy keeps everyone's saved mark and video.
    """
    song = reply.song
    now = time.time()
    with connect() as connection:
        connection.execute(
            "INSERT INTO songs (id, track, artist, album, duration_seconds, lines_json,"
            " cached_at, last_opened_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
            " ON CONFLICT(id) DO UPDATE SET track = excluded.track, artist = excluded.artist,"
            " album = excluded.album, duration_seconds = excluded.duration_seconds,"
            " lines_json = excluded.lines_json, cached_at = excluded.cached_at,"
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


def list_songs(user_id: int) -> list[SavedSong]:
    """This person's saved songs without their lines, most recently opened first."""
    with connect() as connection:
        rows = connection.execute(
            "SELECT s.id, s.track, s.artist, s.album, s.duration_seconds, e.video_id,"
            " e.offset_ms, e.last_opened_at FROM library_entries e JOIN songs s"
            " ON s.id = e.song_id WHERE e.user_id = ?"
            " ORDER BY e.last_opened_at DESC, s.id DESC",
            (user_id,),
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


def list_recent_songs(limit: int, user_id: int | None) -> list[RecentSong]:
    """Cached songs opened by anyone, most recent first, without their lines.

    A video shows only when it is this person's own; a guest never sees one.
    """
    with connect() as connection:
        rows = connection.execute(
            "SELECT s.id, s.track, s.artist, s.album, s.duration_seconds, e.video_id"
            " FROM songs s LEFT JOIN library_entries e ON e.song_id = s.id AND e.user_id = ?"
            " ORDER BY s.last_opened_at DESC, s.id DESC LIMIT ?",
            (user_id, limit),
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


def saved_ids(user_id: int, song_ids: Iterable[int]) -> set[int]:
    """Which of these song ids are in this person's library; none if the database can't be read."""
    wanted = list(song_ids)
    if not wanted:
        return set()
    placeholders = ", ".join("?" for _ in wanted)
    try:
        with connect() as connection:
            rows = connection.execute(
                # Only "?" placeholders are formatted in; the ids go in as parameters.
                "SELECT song_id FROM library_entries WHERE user_id = ?"
                f" AND song_id IN ({placeholders})",
                [user_id, *wanted],
            ).fetchall()
    except sqlite3.Error:
        logger.warning("library_unavailable")
        return set()
    return {song_id for (song_id,) in rows}
