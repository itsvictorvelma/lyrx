"""Tests for the database file: its path, its folder, and the upgrade of an older file."""

import sqlite3
from contextlib import closing
from pathlib import Path

from conftest import REAL_DATABASE_PATH, sign_up
from error_shape import assert_error_shape
from fake_lrclib import FakeLrclib, json_reply, record
from fastapi.testclient import TestClient

from subbed import config
from subbed.app import SAVED_SONGS_PATH, SONG_SEARCH_PATH, SONG_VERSIONS_PATH
from subbed.database import connect

VIDEO_ID = "abcDEF12_-z"
ONE_LINE_JSON = (
    '[{"index": 0, "original": "夜", "hiragana": "よる", "romaji": "yoru", "english": "Night"}]'
)


def test_spec009_ac9_the_database_path_is_a_setting_and_its_folder_is_created(
    temporary_database: Path,
) -> None:
    assert not temporary_database.parent.exists()

    with connect():
        pass

    assert temporary_database.exists()
    assert temporary_database == config.DATABASE_PATH


def test_the_real_database_path_is_in_the_gitignored_data_folder() -> None:
    assert REAL_DATABASE_PATH == config.REPO_ROOT / "data" / "subbed.db"
    assert "*.db" in (config.REPO_ROOT / ".gitignore").read_text().splitlines()


def make_old_database(path: Path) -> None:
    """A file from before accounts: song 101 saved with a video, song 102 only cached."""
    path.parent.mkdir(parents=True)
    with closing(sqlite3.connect(path)) as connection, connection:
        connection.execute(
            "CREATE TABLE saved_songs (id INTEGER PRIMARY KEY, track TEXT NOT NULL,"
            " artist TEXT NOT NULL, album TEXT NOT NULL, duration_seconds INTEGER NOT NULL,"
            " lines_json TEXT NOT NULL, saved_at REAL NOT NULL, last_opened_at REAL NOT NULL,"
            " video_id TEXT, offset_ms INTEGER NOT NULL DEFAULT 0,"
            " saved INTEGER NOT NULL DEFAULT 1)"
        )
        for song_id, video_id, saved in ((101, VIDEO_ID, 1), (102, None, 0)):
            connection.execute(
                "INSERT INTO saved_songs VALUES"
                " (?, '歌', 'ミナト', '', 200, ?, 1.0, 1.0, ?, 250, ?)",
                (song_id, ONE_LINE_JSON, video_id, saved),
            )


def test_ac13_an_older_database_keeps_its_songs_and_the_first_account_gets_the_saved_ones(
    client: TestClient, temporary_database: Path
) -> None:
    make_old_database(temporary_database)

    sign_up(client, "first")

    songs = client.get(SAVED_SONGS_PATH).json()["songs"]
    assert [(song["id"], song["videoId"], song["offsetMs"]) for song in songs] == [
        (101, VIDEO_ID, 250)
    ]
    cached = client.post(SONG_VERSIONS_PATH, json={"id": 102}).json()
    assert (cached["fromLibrary"], cached["saved"]) == (True, False)
    assert cached["lines"][0]["hiragana"] == "よる"


def test_ac13_the_second_account_gets_none_of_the_older_saved_songs(
    client: TestClient, temporary_database: Path
) -> None:
    make_old_database(temporary_database)
    sign_up(client, "first")
    client.post("/api/account/sign-out")

    sign_up(client, "second")

    assert client.get(SAVED_SONGS_PATH).json()["songs"] == []


def test_ac13_a_file_from_before_playback_gains_the_columns_and_upgrades(
    client: TestClient, temporary_database: Path
) -> None:
    temporary_database.parent.mkdir(parents=True)
    with closing(sqlite3.connect(temporary_database)) as connection, connection:
        connection.execute(
            "CREATE TABLE saved_songs (id INTEGER PRIMARY KEY, track TEXT NOT NULL,"
            " artist TEXT NOT NULL, album TEXT NOT NULL, duration_seconds INTEGER NOT NULL,"
            " lines_json TEXT NOT NULL, saved_at REAL NOT NULL, last_opened_at REAL NOT NULL)"
        )
        connection.execute(
            "INSERT INTO saved_songs VALUES (101, '歌', 'ミナト', '', 200, ?, 1.0, 1.0)",
            (ONE_LINE_JSON,),
        )

    sign_up(client)

    reply = client.post(SONG_VERSIONS_PATH, json={"id": 101}).json()
    assert (reply["fromLibrary"], reply["saved"]) == (True, True)
    assert reply["playback"] == {"videoId": None, "offsetMs": 0}


def test_an_unreadable_file_still_lets_a_guest_search_but_no_new_song_starts(
    client: TestClient, fake_lrclib: FakeLrclib, temporary_database: Path
) -> None:
    """Without the database the daily caps cannot be counted, so new songs fail closed."""
    temporary_database.parent.mkdir(parents=True)
    temporary_database.write_bytes(b"this is not a database file" * 100)
    fake_lrclib.script(json_reply([record()]))

    search = client.post(SONG_SEARCH_PATH, json={"query": "歌"})
    opened = client.post(SONG_VERSIONS_PATH, json={"id": 101})

    assert search.status_code == 200
    assert search.json()["results"][0]["saved"] is False
    assert opened.status_code == 500
    assert_error_shape(opened.json(), "internal_error")
    assert len(fake_lrclib.requests) == 1
