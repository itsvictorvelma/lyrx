"""Tests for the song cache and library (specs 009, 016) and saved playback (spec 012).

Every test here runs signed in; test_accounts covers guests and two people."""

import logging
import sqlite3
import time
from contextlib import closing
from pathlib import Path
from typing import Any

import pytest
from conftest import sign_up
from error_shape import assert_error_shape
from fake_gemini import (
    FakeGemini,
    answer_with_placeholders,
    context_indexes,
    placeholder_versions,
    sent_indexes,
    status,
    success,
)
from fake_lrclib import FakeLrclib, json_reply, record
from fastapi.testclient import TestClient

from subbed import config, library
from subbed.app import RECENT_SONGS_PATH, SAVED_SONGS_PATH, SONG_SEARCH_PATH, SONG_VERSIONS_PATH

# The invented record's non-blank lines.
SENT = [0, 1, 3, 4]
VIDEO_ID = "abcDEF12_-z"


@pytest.fixture(autouse=True)
def signed_in(client: TestClient) -> None:
    sign_up(client)


def user_id() -> int:
    """The id of the one account the fixture above created."""
    return 1


def open_song(client: TestClient, song_id: int = 101) -> dict[str, Any]:
    response = client.post(SONG_VERSIONS_PATH, json={"id": song_id})
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


def save(client: TestClient, song_id: int = 101, video_id: str | None = None) -> int:
    """Puts a cached song in the library; the reply's status."""
    body = {"videoId": video_id, "offsetMs": 0}
    return client.put(f"{SAVED_SONGS_PATH}/{song_id}/saved", json=body).status_code


def open_new_song(
    client: TestClient, fake_lrclib: FakeLrclib, fake_gemini: FakeGemini, song_id: int = 101
) -> dict[str, Any]:
    fake_lrclib.script(json_reply(record(record_id=song_id, track=f"歌{song_id}")))
    fake_gemini.answer = answer_with_placeholders
    return open_song(client, song_id)


@pytest.mark.usefixtures("gemini_key")
def test_ac1_an_opened_song_is_cached_and_opens_again_with_no_outside_calls(
    client: TestClient, fake_lrclib: FakeLrclib, fake_gemini: FakeGemini
) -> None:
    first = open_new_song(client, fake_lrclib, fake_gemini)
    calls = (len(fake_lrclib.requests), len(fake_gemini.requests))

    again = open_song(client)

    assert (again["song"], again["lines"]) == (first["song"], first["lines"])
    assert (first["fromLibrary"], again["fromLibrary"]) == (False, True)
    assert (len(fake_lrclib.requests), len(fake_gemini.requests)) == calls


def test_ac2_a_cached_song_opens_with_no_key(
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
def test_spec016_ac2_a_missing_line_is_cached_and_only_it_is_asked_again_on_reopen(
    client: TestClient, fake_lrclib: FakeLrclib, fake_gemini: FakeGemini
) -> None:
    incomplete = {index: placeholder_versions(index) for index in SENT if index != 1}
    fake_lrclib.script(json_reply(record()))
    fake_gemini.script(success(incomplete), success({}))
    first = open_song(client)
    assert first["lines"][1]["hiragana"] == ""

    fake_gemini.answer = answer_with_placeholders
    again = open_song(client)

    assert sent_indexes(fake_gemini.requests[-1]) == [1]
    assert context_indexes(fake_gemini.requests[-1]) == SENT
    assert len(fake_lrclib.requests) == 1
    assert again["lines"][1]["hiragana"] != ""
    assert again["lines"][0] == first["lines"][0]
    cached = library.find_song(101)
    assert cached is not None and cached.lines[1].hiragana != ""


@pytest.mark.usefixtures("gemini_key")
def test_spec016_ac3_a_busy_translator_on_reopen_still_opens_the_cached_song(
    client: TestClient,
    fake_lrclib: FakeLrclib,
    fake_gemini: FakeGemini,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO)
    incomplete = {index: placeholder_versions(index) for index in SENT if index != 1}
    fake_lrclib.script(json_reply(record()))
    fake_gemini.script(success(incomplete), success({}), status(429))
    open_song(client)

    again = open_song(client)

    assert again["lines"][1]["hiragana"] == ""
    assert "refill_failed=translation_rate_limited" in caplog.text


@pytest.mark.usefixtures("gemini_key")
def test_spec016_ac1_an_opened_song_is_not_in_the_library_until_saved(
    client: TestClient, fake_lrclib: FakeLrclib, fake_gemini: FakeGemini
) -> None:
    first = open_new_song(client, fake_lrclib, fake_gemini)

    assert first["saved"] is False
    assert client.get(SAVED_SONGS_PATH).json()["songs"] == []


@pytest.mark.usefixtures("gemini_key")
def test_spec016_ac4_saving_keeps_the_video_and_lists_the_song(
    client: TestClient, fake_lrclib: FakeLrclib, fake_gemini: FakeGemini
) -> None:
    open_new_song(client, fake_lrclib, fake_gemini)

    assert save(client, video_id=VIDEO_ID) == 204

    assert [song["id"] for song in client.get(SAVED_SONGS_PATH).json()["songs"]] == [101]
    reply = open_song(client)
    assert reply["saved"] is True
    assert reply["playback"] == {"videoId": VIDEO_ID, "offsetMs": 0}


def test_spec016_ac4_saving_an_unknown_song_is_not_found(client: TestClient) -> None:
    assert save(client, 999) == 404


@pytest.mark.usefixtures("gemini_key")
def test_spec016_ac4_saving_with_a_bad_video_id_is_invalid_request(
    client: TestClient, fake_lrclib: FakeLrclib, fake_gemini: FakeGemini
) -> None:
    open_new_song(client, fake_lrclib, fake_gemini)

    response = client.put(
        f"{SAVED_SONGS_PATH}/101/saved", json={"videoId": "<script>x</s", "offsetMs": 0}
    )

    assert response.status_code == 400
    assert_error_shape(response.json(), "invalid_request")


@pytest.mark.usefixtures("gemini_key")
def test_spec016_ac6_playback_is_kept_only_once_the_song_is_saved(
    client: TestClient, fake_lrclib: FakeLrclib, fake_gemini: FakeGemini
) -> None:
    open_new_song(client, fake_lrclib, fake_gemini)
    playback = {"videoId": VIDEO_ID, "offsetMs": 500}

    before = client.put(f"{SAVED_SONGS_PATH}/101/playback", json=playback)
    save(client)
    after = client.put(f"{SAVED_SONGS_PATH}/101/playback", json=playback)

    assert (before.status_code, after.status_code) == (404, 204)
    assert open_song(client)["playback"] == playback


@pytest.mark.usefixtures("gemini_key")
def test_ac4_the_list_is_most_recently_opened_first_without_lines(
    client: TestClient, fake_lrclib: FakeLrclib, fake_gemini: FakeGemini
) -> None:
    for song_id in (1, 2, 3):
        open_new_song(client, fake_lrclib, fake_gemini, song_id)
        save(client, song_id)
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
        "offsetMs",
        "lastOpenedAt",
    }


@pytest.mark.usefixtures("gemini_key")
def test_spec013_ac12_the_list_has_each_songs_video_and_last_opened_time(
    client: TestClient, fake_lrclib: FakeLrclib, fake_gemini: FakeGemini
) -> None:
    before_ms = time.time() * 1000
    for song_id in (1, 2):
        open_new_song(client, fake_lrclib, fake_gemini, song_id)
        save(client, song_id)
    client.put(f"{SAVED_SONGS_PATH}/1/playback", json={"videoId": "abcdefghijk", "offsetMs": 0})

    songs = {song["id"]: song for song in client.get(SAVED_SONGS_PATH).json()["songs"]}

    assert songs[1]["videoId"] == "abcdefghijk"
    assert songs[2]["videoId"] is None
    assert songs[2]["lastOpenedAt"] >= before_ms - 1000


@pytest.mark.usefixtures("gemini_key")
def test_spec016_ac5_unsaving_leaves_the_library_but_keeps_the_song_cached(
    client: TestClient, fake_lrclib: FakeLrclib, fake_gemini: FakeGemini
) -> None:
    open_new_song(client, fake_lrclib, fake_gemini)
    save(client, video_id=VIDEO_ID)
    calls = (len(fake_lrclib.requests), len(fake_gemini.requests))

    response = client.delete(f"{SAVED_SONGS_PATH}/101/saved")

    assert response.status_code == 204
    assert client.get(SAVED_SONGS_PATH).json()["songs"] == []
    reply = open_song(client)
    assert (reply["saved"], reply["playback"]["videoId"]) == (False, None)
    assert (len(fake_lrclib.requests), len(fake_gemini.requests)) == calls


def test_ac5_removing_an_unknown_song_is_not_found(client: TestClient) -> None:
    response = client.delete(f"{SAVED_SONGS_PATH}/999/saved")

    assert response.status_code == 404
    assert_error_shape(response.json(), "song_not_found")


@pytest.mark.parametrize("bad_id", ["0", "-1", "abc", "1.5", "true"])
def test_ac5_a_bad_id_is_invalid_request(client: TestClient, bad_id: str) -> None:
    response = client.delete(f"{SAVED_SONGS_PATH}/{bad_id}/saved")

    assert response.status_code == 400
    assert_error_shape(response.json(), "invalid_request")


@pytest.mark.usefixtures("gemini_key")
def test_ac6_search_results_say_which_songs_are_saved(
    client: TestClient, fake_lrclib: FakeLrclib, fake_gemini: FakeGemini
) -> None:
    open_new_song(client, fake_lrclib, fake_gemini, 7)
    save(client, 7)
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
        connection.execute('UPDATE songs SET lines_json = \'[{"index": "x"}]\'')

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

    monkeypatch.setattr(library, "cache_song", failing_save)

    open_new_song(client, fake_lrclib, fake_gemini)

    assert "save_failed=true" in caplog.text
    assert "/secret/path" not in caplog.text


@pytest.mark.parametrize("too_big", [2**63, 10**20])
def test_an_id_too_large_for_the_library_is_invalid_request(
    client: TestClient, too_big: int
) -> None:
    opened = client.post(SONG_VERSIONS_PATH, json={"id": too_big})
    removed = client.delete(f"{SAVED_SONGS_PATH}/{too_big}/saved")

    for response in (opened, removed):
        assert response.status_code == 400
        assert_error_shape(response.json(), "invalid_request")


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

    lines = [r.getMessage() for r in caplog.records if r.name == "subbed.server.request_log"]
    assert "from_library=false" in lines[0]
    assert "from_library=true" in lines[1]
    assert "歌101" not in caplog.text


def test_the_paste_route_is_gone(client: TestClient) -> None:
    response = client.post("/api/versions", json={"lyrics": "夜の月"})

    assert response.status_code == 404
    assert_error_shape(response.json(), "not_found")


# Playback (spec 012)


@pytest.mark.usefixtures("gemini_key")
def test_spec012_ac4_playback_is_saved_and_comes_back_on_the_next_open(
    client: TestClient, fake_lrclib: FakeLrclib, fake_gemini: FakeGemini
) -> None:
    first = open_new_song(client, fake_lrclib, fake_gemini)
    save(client)

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
    save(client)
    client.put(f"{SAVED_SONGS_PATH}/101/playback", json={"videoId": VIDEO_ID, "offsetMs": 250})
    saved = library.find_song(101)
    assert saved is not None

    library.cache_song(saved)

    reply = open_song(client)
    assert reply["playback"] == {"videoId": VIDEO_ID, "offsetMs": 250}
    # Spec 016: a new copy in the cache keeps the song in the library.
    assert reply["saved"] is True
    assert [song["id"] for song in client.get(SAVED_SONGS_PATH).json()["songs"]] == [101]


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
def test_a_saved_playback_that_fails_the_checks_is_dropped_but_the_song_opens(
    client: TestClient,
    fake_lrclib: FakeLrclib,
    fake_gemini: FakeGemini,
    temporary_database: Path,
) -> None:
    open_new_song(client, fake_lrclib, fake_gemini)
    save(client)
    with closing(sqlite3.connect(temporary_database)) as connection, connection:
        connection.execute(
            "UPDATE library_entries SET video_id = 'not an id', offset_ms = 99999999"
        )

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


@pytest.mark.usefixtures("gemini_key")
def test_spec021_ac7_recent_songs_are_capped_newest_first_without_lines(
    client: TestClient,
    fake_lrclib: FakeLrclib,
    fake_gemini: FakeGemini,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(config, "RECENT_SONGS_SHOWN", 2)
    for song_id in (101, 102, 103):
        open_new_song(client, fake_lrclib, fake_gemini, song_id)
    assert save(client, 102, VIDEO_ID) == 204
    open_song(client, 101)  # Opening again moves it to the front.

    response = client.get(RECENT_SONGS_PATH)

    assert response.status_code == 200
    songs = response.json()["songs"]
    assert [song["id"] for song in songs] == [101, 103]
    assert all("lines" not in song for song in songs)
    assert songs[0] == {
        "id": 101,
        "track": "歌101",
        "artist": songs[0]["artist"],
        "album": songs[0]["album"],
        "durationSeconds": songs[0]["durationSeconds"],
        "videoId": None,
    }


@pytest.mark.usefixtures("gemini_key")
def test_spec021_ac7_recent_songs_hold_saved_and_unsaved_songs(
    client: TestClient, fake_lrclib: FakeLrclib, fake_gemini: FakeGemini
) -> None:
    open_new_song(client, fake_lrclib, fake_gemini, 101)
    open_new_song(client, fake_lrclib, fake_gemini, 102)
    assert save(client, 101, VIDEO_ID) == 204

    songs = client.get(RECENT_SONGS_PATH).json()["songs"]

    assert {song["id"]: song["videoId"] for song in songs} == {102: None, 101: VIDEO_ID}


@pytest.mark.usefixtures("gemini_key")
def test_spec025_ac5_saved_songs_list_their_sync(
    client: TestClient, fake_lrclib: FakeLrclib, fake_gemini: FakeGemini
) -> None:
    open_new_song(client, fake_lrclib, fake_gemini, 101)
    body = {"videoId": VIDEO_ID, "offsetMs": -750}
    assert client.put(f"{SAVED_SONGS_PATH}/101/saved", json=body).status_code == 204

    songs = client.get(SAVED_SONGS_PATH).json()["songs"]

    assert [(song["id"], song["videoId"], song["offsetMs"]) for song in songs] == [
        (101, VIDEO_ID, -750)
    ]


def test_a_database_that_cannot_be_read_counts_as_not_cached_and_none_saved(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    def broken_connect() -> Any:
        raise sqlite3.OperationalError("unable to open database file")

    monkeypatch.setattr(library, "connect", broken_connect)

    assert library.find_song(1) is None
    assert library.saved_ids(1, [1]) == set()
    assert caplog.text.count("library_unavailable") == 2
