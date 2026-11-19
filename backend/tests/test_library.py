"""Tests for saved songs (spec 009) and their saved playback (spec 012), with the routes."""

import logging
import sqlite3
import time
from contextlib import closing
from pathlib import Path
from typing import Any

import pytest
from conftest import REAL_DATABASE_PATH
from error_shape import assert_error_shape
from fake_gemini import FakeGemini, answer_with_placeholders, placeholder_versions, success
from fake_lrclib import FakeLrclib, json_reply, record
from fastapi.testclient import TestClient

from lyrx import config, library
from lyrx.app import SAVED_SONGS_PATH, SONG_SEARCH_PATH, SONG_VERSIONS_PATH

# The invented record's non-blank lines.
SENT = [0, 1, 3, 4]


def open_song(client: TestClient, song_id: int = 101) -> dict[str, Any]:
    response = client.post(SONG_VERSIONS_PATH, json={"id": song_id})
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


def open_new_song(
    client: TestClient, fake_lrclib: FakeLrclib, fake_gemini: FakeGemini, song_id: int = 101
) -> dict[str, Any]:
    fake_lrclib.script(json_reply(record(record_id=song_id, track=f"歌{song_id}")))
    fake_gemini.answer = answer_with_placeholders
    return open_song(client, song_id)


@pytest.mark.usefixtures("gemini_key")
def test_ac1_an_opened_song_is_saved_and_opens_again_with_no_outside_calls(
    client: TestClient, fake_lrclib: FakeLrclib, fake_gemini: FakeGemini
) -> None:
    first = open_new_song(client, fake_lrclib, fake_gemini)
    calls = (len(fake_lrclib.requests), len(fake_gemini.requests))

    again = open_song(client)

    assert (again["song"], again["lines"]) == (first["song"], first["lines"])
    assert (first["fromLibrary"], again["fromLibrary"]) == (False, True)
    assert (len(fake_lrclib.requests), len(fake_gemini.requests)) == calls


def test_ac2_a_saved_song_opens_with_no_key(
    client: TestClient,
    fake_lrclib: FakeLrclib,
    fake_gemini: FakeGemini,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(config.GEMINI_API_KEY_ENV_VAR, "fake-key")
    open_new_song(client, fake_lrclib, fake_gemini)
    monkeypatch.delenv(config.GEMINI_API_KEY_ENV_VAR)

    assert open_song(client)["song"] == {
        "id": 101,
        "track": "歌101",
        "artist": "ミナト",
        "album": "夜の窓",
        "durationSeconds": 214,
    }


@pytest.mark.usefixtures("gemini_key")
def test_ac3_a_song_with_a_missing_line_is_not_saved(
    client: TestClient, fake_lrclib: FakeLrclib, fake_gemini: FakeGemini
) -> None:
    incomplete = {index: placeholder_versions(index) for index in SENT if index != 1}
    fake_lrclib.script(json_reply(record()), json_reply(record()))
    fake_gemini.script(success(incomplete), success({}))

    open_song(client)

    assert library.find_song(101) is None
    fake_gemini.answer = answer_with_placeholders
    open_song(client)
    assert len(fake_lrclib.requests) == 2


@pytest.mark.usefixtures("gemini_key")
def test_ac4_the_list_is_most_recently_opened_first_without_lines(
    client: TestClient, fake_lrclib: FakeLrclib, fake_gemini: FakeGemini
) -> None:
    for song_id in (1, 2, 3):
        open_new_song(client, fake_lrclib, fake_gemini, song_id)
    open_song(client, 1)

    songs = client.get(SAVED_SONGS_PATH).json()["songs"]

    assert [song["id"] for song in songs] == [1, 3, 2]
    assert set(songs[0]) == {
        "id",
        "track",
        "artist",
        "album",
        "durationSeconds",
        "videoId",
        "lastOpenedAt",
    }


@pytest.mark.usefixtures("gemini_key")
def test_spec013_ac12_the_list_has_each_songs_video_and_last_opened_time(
    client: TestClient, fake_lrclib: FakeLrclib, fake_gemini: FakeGemini
) -> None:
    before_ms = time.time() * 1000
    for song_id in (1, 2):
        open_new_song(client, fake_lrclib, fake_gemini, song_id)
    client.put(f"{SAVED_SONGS_PATH}/1/playback", json={"videoId": "abcdefghijk", "offsetMs": 0})

    songs = {song["id"]: song for song in client.get(SAVED_SONGS_PATH).json()["songs"]}

    assert songs[1]["videoId"] == "abcdefghijk"
    assert songs[2]["videoId"] is None
    assert songs[2]["lastOpenedAt"] >= before_ms - 1000


@pytest.mark.usefixtures("gemini_key")
def test_ac5_remove_deletes_the_song_and_the_next_open_fetches_it_again(
    client: TestClient, fake_lrclib: FakeLrclib, fake_gemini: FakeGemini
) -> None:
    open_new_song(client, fake_lrclib, fake_gemini)

    response = client.delete(f"{SAVED_SONGS_PATH}/101")

    assert response.status_code == 204
    assert client.get(SAVED_SONGS_PATH).json()["songs"] == []
    open_new_song(client, fake_lrclib, fake_gemini)
    assert len(fake_lrclib.requests) == 2


def test_ac5_removing_an_unknown_song_is_not_found(client: TestClient) -> None:
    response = client.delete(f"{SAVED_SONGS_PATH}/999")

    assert response.status_code == 404
    assert_error_shape(response.json(), "song_not_found")


@pytest.mark.parametrize("bad_id", ["0", "-1", "abc", "1.5", "true"])
def test_ac5_a_bad_id_is_invalid_request(client: TestClient, bad_id: str) -> None:
    response = client.delete(f"{SAVED_SONGS_PATH}/{bad_id}")

    assert response.status_code == 400
    assert_error_shape(response.json(), "invalid_request")


@pytest.mark.usefixtures("gemini_key")
def test_ac6_search_results_say_which_songs_are_saved(
    client: TestClient, fake_lrclib: FakeLrclib, fake_gemini: FakeGemini
) -> None:
    open_new_song(client, fake_lrclib, fake_gemini, 7)
    fake_lrclib.script(json_reply([record(record_id=7, track="歌7"), record(record_id=8)]))

    results = client.post(SONG_SEARCH_PATH, json={"query": "歌"}).json()["results"]

    assert {result["id"]: result["saved"] for result in results} == {7: True, 8: False}


@pytest.mark.usefixtures("gemini_key")
def test_ac7_a_broken_saved_row_is_deleted_and_the_song_fetched_again(
    client: TestClient,
    fake_lrclib: FakeLrclib,
    fake_gemini: FakeGemini,
    temporary_database: Path,
) -> None:
    open_new_song(client, fake_lrclib, fake_gemini)
    with sqlite3.connect(temporary_database) as connection:
        connection.execute('UPDATE saved_songs SET lines_json = \'[{"index": "x"}]\'')

    open_new_song(client, fake_lrclib, fake_gemini)

    assert len(fake_lrclib.requests) == 2
    assert library.find_song(101) is not None


@pytest.mark.usefixtures("gemini_key")
def test_ac8_a_failed_save_still_returns_the_song_and_logs_save_failed(
    client: TestClient,
    fake_lrclib: FakeLrclib,
    fake_gemini: FakeGemini,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO)

    def failing_save(*_: object) -> None:
        raise sqlite3.OperationalError("disk full /secret/path")

    monkeypatch.setattr(library, "save_song", failing_save)

    open_new_song(client, fake_lrclib, fake_gemini)

    assert "save_failed=true" in caplog.text
    assert "/secret/path" not in caplog.text


def test_ac9_the_database_path_is_a_setting_and_its_folder_is_created(
    temporary_database: Path,
) -> None:
    assert not temporary_database.parent.exists()

    assert library.list_songs() == []

    assert temporary_database.exists()
    assert temporary_database == config.DATABASE_PATH


def test_the_real_database_path_is_in_the_gitignored_data_folder() -> None:
    assert REAL_DATABASE_PATH == config.REPO_ROOT / "data" / "lyrx.db"
    assert "*.db" in (config.REPO_ROOT / ".gitignore").read_text().splitlines()


@pytest.mark.parametrize("too_big", [2**63, 10**20])
def test_an_id_too_large_for_the_library_is_invalid_request(
    client: TestClient, too_big: int
) -> None:
    opened = client.post(SONG_VERSIONS_PATH, json={"id": too_big})
    removed = client.delete(f"{SAVED_SONGS_PATH}/{too_big}")

    for response in (opened, removed):
        assert response.status_code == 400
        assert_error_shape(response.json(), "invalid_request")


@pytest.mark.usefixtures("gemini_key")
def test_an_unreadable_library_falls_back_to_lrclib_and_search_still_works(
    client: TestClient,
    fake_lrclib: FakeLrclib,
    fake_gemini: FakeGemini,
    temporary_database: Path,
) -> None:
    temporary_database.parent.mkdir(parents=True)
    temporary_database.write_bytes(b"this is not a database file" * 100)
    fake_lrclib.script(json_reply([record()]))

    search = client.post(SONG_SEARCH_PATH, json={"query": "歌"})
    opened = open_new_song(client, fake_lrclib, fake_gemini)

    assert search.status_code == 200
    assert search.json()["results"][0]["saved"] is False
    assert opened["fromLibrary"] is False


@pytest.mark.usefixtures("gemini_key")
def test_the_log_says_whether_a_song_came_from_the_library(
    client: TestClient,
    fake_lrclib: FakeLrclib,
    fake_gemini: FakeGemini,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO)
    open_new_song(client, fake_lrclib, fake_gemini)
    open_song(client)

    lines = [r.getMessage() for r in caplog.records if r.name == "lyrx.server.request_log"]
    assert "from_library=false" in lines[0]
    assert "from_library=true" in lines[1]
    assert "歌101" not in caplog.text


def test_the_paste_route_is_gone(client: TestClient) -> None:
    response = client.post("/api/versions", json={"lyrics": "夜の月"})

    assert response.status_code == 404
    assert_error_shape(response.json(), "not_found")


# Playback (spec 012)

VIDEO_ID = "abcDEF12_-z"


@pytest.mark.usefixtures("gemini_key")
def test_spec012_ac4_playback_is_saved_and_comes_back_on_the_next_open(
    client: TestClient, fake_lrclib: FakeLrclib, fake_gemini: FakeGemini
) -> None:
    first = open_new_song(client, fake_lrclib, fake_gemini)

    response = client.put(
        f"{SAVED_SONGS_PATH}/101/playback", json={"videoId": VIDEO_ID, "offsetMs": -750}
    )

    assert first["playback"] == {"videoId": None, "offsetMs": 0}
    assert response.status_code == 204
    assert open_song(client)["playback"] == {"videoId": VIDEO_ID, "offsetMs": -750}


@pytest.mark.usefixtures("gemini_key")
def test_spec012_ac4_a_new_copy_of_a_song_keeps_its_playback(
    client: TestClient, fake_lrclib: FakeLrclib, fake_gemini: FakeGemini
) -> None:
    open_new_song(client, fake_lrclib, fake_gemini)
    client.put(f"{SAVED_SONGS_PATH}/101/playback", json={"videoId": VIDEO_ID, "offsetMs": 250})
    saved = library.find_song(101)
    assert saved is not None

    library.save_song(saved)

    assert open_song(client)["playback"] == {"videoId": VIDEO_ID, "offsetMs": 250}


@pytest.mark.usefixtures("gemini_key")
@pytest.mark.parametrize(
    "body",
    [
        {"videoId": "short", "offsetMs": 0},
        {"videoId": "abcDEF12_-z!", "offsetMs": 0},
        {"videoId": "<script>x</s", "offsetMs": 0},
        {"videoId": VIDEO_ID, "offsetMs": 30_001},
        {"videoId": VIDEO_ID, "offsetMs": -30_001},
        {"videoId": VIDEO_ID, "offsetMs": "0"},
        {"videoId": VIDEO_ID, "offsetMs": 1.5},
    ],
)
def test_spec012_ac5_a_bad_video_id_or_offset_is_invalid_request(
    client: TestClient, fake_lrclib: FakeLrclib, fake_gemini: FakeGemini, body: dict[str, object]
) -> None:
    open_new_song(client, fake_lrclib, fake_gemini)

    response = client.put(f"{SAVED_SONGS_PATH}/101/playback", json=body)

    assert response.status_code == 400
    assert_error_shape(response.json(), "invalid_request")


def test_spec012_ac5_playback_for_a_song_that_is_not_saved_is_not_found(client: TestClient) -> None:
    response = client.put(f"{SAVED_SONGS_PATH}/101/playback", json={"videoId": None, "offsetMs": 0})

    assert response.status_code == 404
    assert_error_shape(response.json(), "song_not_found")


@pytest.mark.usefixtures("gemini_key")
def test_spec012_ac6_a_library_from_before_playback_gains_the_columns_and_still_opens(
    client: TestClient,
    fake_lrclib: FakeLrclib,
    fake_gemini: FakeGemini,
    temporary_database: Path,
) -> None:
    temporary_database.parent.mkdir(parents=True)
    with closing(sqlite3.connect(temporary_database)) as connection, connection:
        connection.execute(
            "CREATE TABLE saved_songs (id INTEGER PRIMARY KEY, track TEXT NOT NULL,"
            " artist TEXT NOT NULL, album TEXT NOT NULL, duration_seconds INTEGER NOT NULL,"
            " lines_json TEXT NOT NULL, saved_at REAL NOT NULL, last_opened_at REAL NOT NULL)"
        )
        connection.execute(
            "INSERT INTO saved_songs VALUES (101, '歌', 'ミナト', '', 200,"
            ' \'[{"index": 0, "original": "夜", "hiragana": "よる",'
            ' "romaji": "yoru", "english": "Night"}]\', 1.0, 1.0)'
        )

    reply = open_song(client)

    assert reply["fromLibrary"] is True
    assert reply["lines"] == [
        {
            "index": 0,
            "original": "夜",
            "hiragana": "よる",
            "romaji": "yoru",
            "english": "Night",
            "startMs": None,
        }
    ]
    assert reply["playback"] == {"videoId": None, "offsetMs": 0}


@pytest.mark.usefixtures("gemini_key")
def test_a_saved_playback_that_fails_the_checks_is_dropped_but_the_song_opens(
    client: TestClient,
    fake_lrclib: FakeLrclib,
    fake_gemini: FakeGemini,
    temporary_database: Path,
) -> None:
    open_new_song(client, fake_lrclib, fake_gemini)
    with closing(sqlite3.connect(temporary_database)) as connection, connection:
        connection.execute("UPDATE saved_songs SET video_id = 'not an id', offset_ms = 99999999")

    assert open_song(client)["playback"] == {"videoId": None, "offsetMs": 0}


@pytest.mark.usefixtures("gemini_key")
def test_an_opened_song_with_timings_returns_and_saves_each_lines_start(
    client: TestClient, fake_lrclib: FakeLrclib, fake_gemini: FakeGemini
) -> None:
    synced = "[00:01.00] 君の声が聞こえる\n[00:05.00] 夜空に星が光る\n[00:12.00] We sing tonight\n"
    synced += "[00:20.50] また会える日まで"
    fake_lrclib.script(json_reply(record(synced=synced)))
    fake_gemini.answer = answer_with_placeholders

    first = open_song(client)

    assert [line["startMs"] for line in first["lines"]] == [1000, 5000, None, 12000, 20500]
    assert [line["startMs"] for line in open_song(client)["lines"]] == [
        1000,
        5000,
        None,
        12000,
        20500,
    ]
