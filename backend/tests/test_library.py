"""Tests for saved songs (spec 009 AC-1 to AC-9): the library file and the routes that use it."""

import logging
import sqlite3
from pathlib import Path

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


def open_song(client: TestClient, song_id: int = 101) -> dict[str, object]:
    response = client.post(SONG_VERSIONS_PATH, json={"id": song_id})
    assert response.status_code == 200, response.text
    body: dict[str, object] = response.json()
    return body


def open_new_song(
    client: TestClient, fake_lrclib: FakeLrclib, fake_gemini: FakeGemini, song_id: int = 101
) -> dict[str, object]:
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
    assert set(songs[0]) == {"id", "track", "artist", "album", "durationSeconds"}


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
