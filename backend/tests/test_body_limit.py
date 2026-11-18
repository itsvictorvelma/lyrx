"""Tests for the body cap: over 256 KiB is refused before parsing; a cut-off body ends quietly."""

import json
import logging
from typing import Any

import pytest
from error_shape import assert_error_shape
from fake_gemini import FakeGemini
from fake_lrclib import FakeLrclib
from fastapi import FastAPI
from fastapi.testclient import TestClient
from raw_asgi import (
    ALLOWED_HOST_HEADER,
    JSON_CONTENT_TYPE_HEADER,
    UVICORN_ERROR_LOGGER,
    body_messages,
    response_body,
    response_status,
    run_like_uvicorn,
)
from starlette.types import Message

from lyrx.app import SONG_SEARCH_PATH

REQUEST_LOGGER = "lyrx.request_log"

BODY_CAP_BYTES = 262_144
NOT_LYRICS_MESSAGE = "This doesn't look like song lyrics."
JSON_HEADERS = {"Content-Type": "application/json"}
# Broken JSON one byte over the cap: if it were parsed, the answer would be invalid_request.
OVERSIZED_BODY = b"{" + b" " * BODY_CAP_BYTES
# The same size in two chunks, so the client sends no Content-Length.
OVERSIZED_CHUNKS = [b"{" + b" " * (BODY_CAP_BYTES // 2), b" " * (BODY_CAP_BYTES // 2)]


def assert_not_lyrics_body(body: Any) -> None:
    """Spec 003 AC-65: the exact sentence, no `details`, and no "too long" or "limit"."""
    assert_error_shape(body, "not_lyrics")
    assert body == {"code": "not_lyrics", "message": NOT_LYRICS_MESSAGE}
    text = json.dumps(body).lower()
    assert "too long" not in text
    assert "limit" not in text


def test_spec003_ac65_body_over_256_kib_with_content_length_is_not_lyrics_before_parsing(
    client: TestClient, fake_gemini: FakeGemini
) -> None:
    assert len(OVERSIZED_BODY) == BODY_CAP_BYTES + 1

    response = client.post(SONG_SEARCH_PATH, content=OVERSIZED_BODY, headers=JSON_HEADERS)

    assert response.request.headers["content-length"] == str(BODY_CAP_BYTES + 1)
    assert response.status_code == 413
    assert_not_lyrics_body(response.json())
    assert fake_gemini.requests == []


def test_spec003_ac65_body_over_256_kib_without_content_length_is_not_lyrics(
    client: TestClient, fake_gemini: FakeGemini
) -> None:
    """The cap counts the bytes read, so a body with no Content-Length is capped."""
    assert sum(len(chunk) for chunk in OVERSIZED_CHUNKS) == BODY_CAP_BYTES + 1

    response = client.post(SONG_SEARCH_PATH, content=iter(OVERSIZED_CHUNKS), headers=JSON_HEADERS)

    assert "content-length" not in response.request.headers
    assert response.status_code == 413
    assert_not_lyrics_body(response.json())
    assert fake_gemini.requests == []


def send_raw_request(
    app: FastAPI, headers: list[tuple[bytes, bytes]], chunks: list[bytes]
) -> list[Message]:
    """Call the ASGI app directly with `chunks` as the body; return what it sent."""
    return run_like_uvicorn(app, headers, body_messages(chunks))


def test_spec003_ac65_body_over_256_kib_with_a_false_small_content_length_is_not_lyrics(
    app: FastAPI, fake_gemini: FakeGemini
) -> None:
    """A lying Content-Length cannot get a large body past the cap."""
    headers = [ALLOWED_HOST_HEADER, JSON_CONTENT_TYPE_HEADER, (b"content-length", b"10")]

    sent = send_raw_request(app, headers, OVERSIZED_CHUNKS)

    assert response_status(sent) == 413
    assert_not_lyrics_body(json.loads(response_body(sent)))
    assert fake_gemini.requests == []


def test_spec003_ac65_broken_body_of_exactly_256_kib_is_parsed_and_gets_the_normal_error(
    client: TestClient,
) -> None:
    """The cap only catches bodies over it; a broken body at the cap is parsed."""
    body_at_the_cap = b"{" + b" " * (BODY_CAP_BYTES - 1)

    response = client.post(SONG_SEARCH_PATH, content=body_at_the_cap, headers=JSON_HEADERS)

    assert response.status_code == 400
    assert_error_shape(response.json(), "invalid_request")


def test_spec003_ac65_the_cap_applies_on_every_route(client: TestClient) -> None:
    """The body cap runs before routing, so an unknown path gets `not_lyrics` too."""
    response = client.post("/api/no-such-route", content=OVERSIZED_BODY, headers=JSON_HEADERS)

    assert response.status_code == 413
    assert_not_lyrics_body(response.json())


# A client that disconnects mid-body never reaches the app (T7 follow-up).


def test_ac44_client_disconnecting_mid_body_never_reaches_the_app_or_lrclib(
    app: FastAPI,
    fake_lrclib: FakeLrclib,
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The body cap reads the whole body first; a cut-off body never reaches the route."""
    caplog.set_level(logging.DEBUG)
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-not-real")
    whole_body = json.dumps({"query": "夜の月が ひかる"}, ensure_ascii=False).encode()
    # The first chunk is a complete, valid body, but `more_body` says more is coming; then the
    # client disconnects.
    incoming: list[Message] = [{"type": "http.request", "body": whole_body, "more_body": True}]

    run_like_uvicorn(app, [ALLOWED_HOST_HEADER, JSON_CONTENT_TYPE_HEADER], incoming)

    # The route would call LRCLIB for this search and always writes its one request line.
    assert fake_lrclib.requests == []
    assert [record for record in caplog.records if record.name == REQUEST_LOGGER] == []


def test_ac44_client_disconnecting_mid_body_gets_no_response_and_logs_no_traceback(
    app: FastAPI, caplog: pytest.LogCaptureFixture
) -> None:
    """A cut-off body ends quietly: nothing is sent and nothing reaches uvicorn's log."""
    caplog.set_level(logging.DEBUG)
    whole_body = json.dumps({"query": "夜の月が ひかる"}, ensure_ascii=False).encode()
    incoming: list[Message] = [{"type": "http.request", "body": whole_body, "more_body": True}]

    sent = run_like_uvicorn(app, [ALLOWED_HOST_HEADER, JSON_CONTENT_TYPE_HEADER], incoming)

    assert sent == []
    assert [record for record in caplog.records if record.name == UVICORN_ERROR_LOGGER] == []
