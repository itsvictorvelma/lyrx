"""Tests for the search route (AC-1 to AC-4): checks, ranking, duplicates, and errors."""

import json
import logging

import httpx2
import pytest
from error_shape import assert_error_shape
from fake_lrclib import ENGLISH_LYRICS, FakeLrclib, json_reply, record
from fastapi.testclient import TestClient

from lyrx import config
from lyrx.app import SONG_SEARCH_PATH


def search(client: TestClient, query: object) -> dict[str, object]:
    response = client.post(SONG_SEARCH_PATH, json={"query": query})
    return {"status": response.status_code, "body": response.json()}


def test_ac1_one_search_request_with_the_trimmed_query(
    client: TestClient, fake_lrclib: FakeLrclib
) -> None:
    fake_lrclib.script(json_reply([record()]))

    result = search(client, "  星の歌 ミナト  ")

    assert result["status"] == 200
    assert len(fake_lrclib.requests) == 1
    assert fake_lrclib.requests[0].url.params["q"] == "星の歌 ミナト"


@pytest.mark.parametrize(
    ("query", "code"),
    [
        ("", "empty_search"),
        ("   ", "empty_search"),
        ("あ" * 301, "invalid_request"),
        (5, "invalid_request"),
    ],
)
def test_ac2_bad_queries_never_reach_lrclib(
    client: TestClient, fake_lrclib: FakeLrclib, query: object, code: str
) -> None:
    result = search(client, query)

    assert result["status"] == 400
    assert_error_shape(result["body"], code)
    assert fake_lrclib.requests == []


def test_ac3_results_are_filtered_ranked_deduplicated_and_have_no_lyrics(
    client: TestClient, fake_lrclib: FakeLrclib
) -> None:
    fake_lrclib.script(
        json_reply(
            [
                {"id": "broken"},
                record(record_id=1, track="River", artist="Sam", lyrics=ENGLISH_LYRICS),
                record(record_id=2, instrumental=True),
                record(record_id=3, lyrics="  "),
                record(record_id=4, duration=214.0),
                record(
                    record_id=5, track="\uff33\uff34\uff21\uff32", duration=200
                ),  # full-width STAR
                record(record_id=6, duration=215.9),
                record(record_id=7, track="star", duration=201),
            ]
        )
    )

    body = search(client, "星の歌")["body"]

    assert isinstance(body, dict)
    results = body["results"]
    assert [result["id"] for result in results] == [4, 5, 1]
    assert results[0] == {
        "id": 4,
        "track": "星の歌",
        "artist": "ミナト",
        "album": "夜の窓",
        "durationSeconds": 214,
        "looksJapanese": True,
    }
    assert results[2]["looksJapanese"] is False


def test_ac3_at_most_ten_results(client: TestClient, fake_lrclib: FakeLrclib) -> None:
    fake_lrclib.script(json_reply([record(record_id=n, track=f"歌{n}") for n in range(1, 30)]))

    body = search(client, "歌")["body"]

    assert isinstance(body, dict)
    assert len(body["results"]) == 10


@pytest.mark.parametrize(
    ("reply", "status", "code"),
    [
        (json_reply([record(instrumental=True)]), 404, "song_not_found"),
        (json_reply([]), 404, "song_not_found"),
        (json_reply({"not": "a list"}), 502, "lyrics_source_unavailable"),
        (json_reply({}, status=404), 502, "lyrics_source_unavailable"),
        (httpx2.ConnectTimeout("fake-secret"), 502, "lyrics_source_unavailable"),
    ],
)
def test_ac4_nothing_usable_or_a_bad_reply(
    client: TestClient, fake_lrclib: FakeLrclib, reply: object, status: int, code: str
) -> None:
    fake_lrclib.script(reply)  # type: ignore[arg-type]

    result = search(client, "星の歌")

    assert result["status"] == status
    assert_error_shape(result["body"], code)


def test_ac13_the_log_line_never_holds_the_query(
    client: TestClient, fake_lrclib: FakeLrclib, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO)
    fake_lrclib.script(json_reply([record()]))

    search(client, "ひみつの歌")

    messages = [r.getMessage() for r in caplog.records if r.name == "lyrx.request_log"]
    assert len(messages) == 1
    assert "results=1" in messages[0]
    assert "ひみつ" not in caplog.text


def test_ac4_a_reply_over_the_cap_is_lyrics_source_unavailable(
    client: TestClient, fake_lrclib: FakeLrclib, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(config, "LRCLIB_SEARCH_MAX_BYTES", 100)
    fake_lrclib.script(json_reply([record()]))

    result = search(client, "星の歌")

    assert result["status"] == 502
    assert_error_shape(result["body"], "lyrics_source_unavailable")


def test_ac3_an_item_with_a_bad_duration_is_dropped_not_a_crash(
    client: TestClient, fake_lrclib: FakeLrclib
) -> None:
    good = json.dumps(record(record_id=2), ensure_ascii=False)
    body = f'[{{"id": 1, "trackName": "a", "artistName": "b", "duration": Infinity}}, {good}]'
    fake_lrclib.script(httpx2.Response(200, content=body.encode()))

    result = search(client, "星の歌")

    assert result["status"] == 200
    assert isinstance(result["body"], dict)
    assert [found["id"] for found in result["body"]["results"]] == [2]
