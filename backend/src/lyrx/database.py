"""The one SQLite file: its connection, every table, and the upgrade of an older file."""

import sqlite3
from collections.abc import Iterator
from contextlib import closing, contextmanager

from lyrx import config

CREATE_TABLES = (
    # The shared song cache: every song anyone opened, with its lines.
    """CREATE TABLE IF NOT EXISTS songs (
        id INTEGER PRIMARY KEY,
        track TEXT NOT NULL,
        artist TEXT NOT NULL,
        album TEXT NOT NULL,
        duration_seconds INTEGER NOT NULL,
        lines_json TEXT NOT NULL,
        cached_at REAL NOT NULL,
        last_opened_at REAL NOT NULL
    )""",
    # One row per song a person saved. `user_id` is NULL only for songs saved before accounts.
    """CREATE TABLE IF NOT EXISTS library_entries (
        user_id INTEGER,
        song_id INTEGER NOT NULL,
        video_id TEXT,
        offset_ms INTEGER NOT NULL DEFAULT 0,
        saved_at REAL NOT NULL,
        last_opened_at REAL NOT NULL,
        UNIQUE (user_id, song_id)
    )""",
    """CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        username TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        created_at REAL NOT NULL
    )""",
    # Only the SHA-256 hash of each session token is kept, never the token.
    """CREATE TABLE IF NOT EXISTS sessions (
        token_hash TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL,
        expires_at REAL NOT NULL
    )""",
    # How many times `who` did `kind` in the window that starts at `window_start`.
    """CREATE TABLE IF NOT EXISTS request_counts (
        kind TEXT NOT NULL,
        who TEXT NOT NULL,
        window_start INTEGER NOT NULL,
        count INTEGER NOT NULL,
        PRIMARY KEY (kind, who, window_start)
    )""",
)

# Columns the old `saved_songs` table gained over time, for files made before them.
OLD_ADDED_COLUMNS = {
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
        for statement in CREATE_TABLES:
            connection.execute(statement)
        upgrade_saved_songs(connection)
        yield connection


def upgrade_saved_songs(connection: sqlite3.Connection) -> None:
    """Moves a file from before accounts to the new tables, once.

    Every old song goes to the cache; the saved ones become library rows with no owner, which
    the first account created claims.
    """
    if not has_saved_songs(connection):
        return
    # Takes the write lock, then looks again: another request may have just upgraded the file.
    connection.execute("BEGIN IMMEDIATE")
    present = {row[1] for row in connection.execute("PRAGMA table_info(saved_songs)")}
    if not present:
        return
    for name, definition in OLD_ADDED_COLUMNS.items():
        if name not in present:
            # Only names and definitions from OLD_ADDED_COLUMNS above are formatted in.
            connection.execute(f"ALTER TABLE saved_songs ADD COLUMN {name} {definition}")
    connection.execute(
        "INSERT OR IGNORE INTO songs (id, track, artist, album, duration_seconds, lines_json,"
        " cached_at, last_opened_at) SELECT id, track, artist, album, duration_seconds,"
        " lines_json, saved_at, last_opened_at FROM saved_songs"
    )
    connection.execute(
        "INSERT INTO library_entries (user_id, song_id, video_id, offset_ms, saved_at,"
        " last_opened_at) SELECT NULL, id, video_id, offset_ms, saved_at, last_opened_at"
        " FROM saved_songs WHERE saved = 1"
    )
    connection.execute("DROP TABLE saved_songs")


def has_saved_songs(connection: sqlite3.Connection) -> bool:
    row = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'saved_songs'"
    ).fetchone()
    return row is not None
