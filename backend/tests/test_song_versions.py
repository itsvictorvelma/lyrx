"""Tests for opening a song (AC-5 to AC-10, AC-13): LRCLIB record to four versions."""

import logging

import httpx2
import pytest
from error_shape import assert_error_shape
from fake_gemini import FakeGemini, sent_indexes, status, success, success_for
from fake_lrclib import ENGLISH_LYRICS, FakeLrclib, json_reply, record
from fastapi.testclient import TestClient

from lyrx import config
from lyrx.app import SONG_VERSIONS_PATH

# The invented record's lines: 0-1 Japanese, 2 blank, 3 English, 4 Japanese.
SENT = [0, 1, 3, 4]


def open_song(client: TestClient, record_id: object = 101) -> httpx2.Response:
    return client.post(SONG_VERSIONS_PATH, json={"id": record_id})


@pytest.mark.usefixtures("gemini_key")
def test_ac5_a_japanese_song_comes_back_in_four_versions_with_one_gemini_call(
    client: TestClient, fake_lrclib: FakeLrclib, fake_gemini: FakeGemini
) -> None:
    fake_lrclib.script(json_reply(record()))
    fake_gemini.script(
        success(
            {
                0: ("きみ の こえ が きこえる", "kimi no koe ga kikoeru", "I can hear your voice"),
                1: ("よぞら に ほし が ひかる", "yozora ni hoshi ga hikaru", "Stars shine"),
                3: ("x", "x", "ignored"),
                4: ("また あえる ひ まで", "mata aeru hi made", "Until we meet again"),
            }
        )
    )

    response = open_song(client)

    assert response.status_code == 200
    body = response.json()
    assert body["song"] == {
        "id": 101,
        "track": "星の歌",
        "artist": "ミナト",
        "album": "夜の窓",
        "durationSeconds": 214,
    }
    lines = body["lines"]
    assert [line["index"] for line in lines] == [0, 1, 2, 3, 4]
    assert lines[0] == {
        "index": 0,
        "original": "君の声が聞こえる",
        "hiragana": "きみ の こえ が きこえる",
        "romaji": "kimi no koe ga kikoeru",
        "english": "I can hear your voice",
    }
    assert lines[2] == {"index": 2, "original": "", "hiragana": "", "romaji": "", "english": ""}
    assert set(lines[3].values()) == {3, "We sing tonight"}
    assert len(fake_gemini.requests) == 1
    assert sent_indexes(fake_gemini.requests[0]) == SENT


@pytest.mark.parametrize("bad_id", [0, -1, True, 1.5, "1", None])
def test_ac6_bad_ids_never_reach_lrclib(
    client: TestClient, fake_lrclib: FakeLrclib, bad_id: object
) -> None:
    response = open_song(client, bad_id)

    assert response.status_code == 400
    assert_error_shape(response.json(), "invalid_request")
    assert fake_lrclib.requests == []


def test_ac7_without_a_key_nothing_is_called_and_setting_it_later_works(
    client: TestClient,
    fake_lrclib: FakeLrclib,
    fake_gemini: FakeGemini,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(config.GEMINI_API_KEY_ENV_VAR, "")

    response = open_song(client)

    assert response.status_code == 503
    assert_error_shape(response.json(), "server_not_configured")
    assert fake_lrclib.requests == []
    assert fake_gemini.requests == []

    monkeypatch.setenv(config.GEMINI_API_KEY_ENV_VAR, "fake-key-set-later")
    fake_lrclib.script(json_reply(record()))
    fake_gemini.script(success_for(SENT))
    assert open_song(client).status_code == 200


@pytest.mark.usefixtures("gemini_key")
@pytest.mark.parametrize(
    ("reply", "status_code", "code"),
    [
        (json_reply({}, status=404), 404, "song_not_found"),
        (json_reply({}, status=500), 502, "lyrics_source_unavailable"),
        (json_reply(record(record_id=999)), 502, "lyrics_source_unavailable"),
    ],
)
def test_ac8_lrclib_failures(
    client: TestClient,
    fake_lrclib: FakeLrclib,
    reply: httpx2.Response,
    status_code: int,
    code: str,
) -> None:
    fake_lrclib.script(reply)

    response = open_song(client)

    assert response.status_code == status_code
    assert_error_shape(response.json(), code)


@pytest.mark.usefixtures("gemini_key")
@pytest.mark.parametrize("not_japanese", [record(lyrics=ENGLISH_LYRICS), record(instrumental=True)])
def test_ac9_a_song_that_is_not_japanese_never_reaches_gemini(
    client: TestClient,
    fake_lrclib: FakeLrclib,
    fake_gemini: FakeGemini,
    not_japanese: dict[str, object],
) -> None:
    fake_lrclib.script(json_reply(not_japanese))

    response = open_song(client)

    assert response.status_code == 422
    assert_error_shape(response.json(), "song_not_japanese")
    assert fake_gemini.requests == []


@pytest.mark.usefixtures("gemini_key")
@pytest.mark.parametrize(
    ("reply", "status_code", "code"),
    [
        (status(429), 429, "translation_rate_limited"),
        (status(500), 503, "translation_unavailable"),
    ],
)
def test_ac10_gemini_failures_give_their_code_after_one_call(
    client: TestClient,
    fake_lrclib: FakeLrclib,
    fake_gemini: FakeGemini,
    reply: httpx2.Response,
    status_code: int,
    code: str,
) -> None:
    fake_lrclib.script(json_reply(record()))
    fake_gemini.script(reply)

    response = open_song(client)

    assert response.status_code == status_code
    assert_error_shape(response.json(), code)
    assert len(fake_gemini.requests) == 1


@pytest.mark.usefixtures("gemini_key")
def test_ac13_the_log_line_has_counts_and_never_lyrics(
    client: TestClient,
    fake_lrclib: FakeLrclib,
    fake_gemini: FakeGemini,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO)
    fake_lrclib.script(json_reply(record()))
    fake_gemini.script(success_for(SENT))

    open_song(client)

    messages = [r.getMessage() for r in caplog.records if r.name == "lyrx.request_log"]
    assert len(messages) == 1
    for field in (
        "route=/api/song-versions",
        "status=200",
        "lrclib_id=101",
        "lines=5",
        "gemini_calls=1",
    ):
        assert field in messages[0]
    assert "君" not in caplog.text
    assert "fake-gemini-key" not in caplog.text
