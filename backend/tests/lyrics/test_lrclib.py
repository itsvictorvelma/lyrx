"""Tests for lrclib.py: fixed addresses, the User-Agent, caps, and record checks."""

import httpx2
import pytest
from fake_lrclib import FakeLrclib, json_reply, record

from subbed import config
from subbed.errors import ApiError
from subbed.lyrics import lrclib
from subbed.lyrics.lrclib import make_lrclib_client


def test_search_sends_one_get_with_the_query_and_the_user_agent() -> None:
    fake = FakeLrclib()
    fake.script(json_reply([record()]))

    records = lrclib.search("星の歌 ミナト", make_lrclib_client(fake.make_transport()))

    assert len(fake.requests) == 1
    request = fake.requests[0]
    assert request.method == "GET"
    assert str(request.url).startswith("https://lrclib.net/api/search?")
    assert request.url.params["q"] == "星の歌 ミナト"
    assert request.headers["User-Agent"] == config.USER_AGENT
    assert request.headers["Accept-Encoding"] == "identity"
    assert [found.id for found in records] == [101]


def test_search_drops_items_that_fail_the_schema() -> None:
    fake = FakeLrclib()
    fake.script(json_reply([{"id": "x"}, record(record_id=7), "text"]))

    assert [
        found.id for found in lrclib.search("q", make_lrclib_client(fake.make_transport()))
    ] == [7]


def test_get_record_asks_for_the_id_and_checks_it_matches() -> None:
    fake = FakeLrclib()
    fake.script(json_reply(record(record_id=5)), json_reply(record(record_id=6)))

    assert lrclib.get_record(5, make_lrclib_client(fake.make_transport())).id == 5
    assert str(fake.requests[0].url) == "https://lrclib.net/api/get/5"
    with pytest.raises(ApiError) as caught:
        lrclib.get_record(5, make_lrclib_client(fake.make_transport()))
    assert caught.value.code == "lyrics_source_unavailable"


@pytest.mark.parametrize(
    ("reply", "code"),
    [
        (json_reply({"message": "nope"}, status=404), "song_not_found"),
        (json_reply({}, status=500), "lyrics_source_unavailable"),
        (
            httpx2.Response(302, headers={"Location": "https://elsewhere.example"}),
            "lyrics_source_unavailable",
        ),
        (httpx2.Response(200, content=b"<html>"), "lyrics_source_unavailable"),
        (httpx2.ConnectTimeout("fake-secret"), "lyrics_source_unavailable"),
    ],
)
def test_failures_become_short_codes(
    reply: httpx2.Response | httpx2.RequestError, code: str
) -> None:
    fake = FakeLrclib()
    fake.script(reply)

    with pytest.raises(ApiError) as caught:
        lrclib.get_record(5, make_lrclib_client(fake.make_transport()))

    assert caught.value.code == code
    assert len(fake.requests) == 1


def test_a_reply_over_the_cap_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "LRCLIB_SEARCH_MAX_BYTES", 100)
    fake = FakeLrclib()
    fake.script(json_reply([record()]))

    with pytest.raises(ApiError) as caught:
        lrclib.search("q", make_lrclib_client(fake.make_transport()))

    assert caught.value.code == "lyrics_source_unavailable"
