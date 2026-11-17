"""Tests for the body cap: over 64 KB is refused before parsing; a cut-off body ends quietly."""

import json
import logging

import pytest
from error_shape import assert_error_shape
from fake_claude import FakeClaudeClient
from fastapi import FastAPI
from fastapi.testclient import TestClient
from raw_asgi import (
    ALLOWED_HOST_HEADER,
    JSON_CONTENT_TYPE_HEADER,
    UVICORN_ERROR_LOGGER,
    body_messages,
    response_status,
    run_like_uvicorn,
)
from starlette.types import Message

from lyrx.app import VERSIONS_PATH

REQUEST_LOGGER = "lyrx.request_log"


def test_ac44_body_over_64kb_is_input_too_large_before_parsing(
    client: TestClient, fake_claude_client: FakeClaudeClient
) -> None:
    # Spec amendment: a body over 64 KB is refused before parsing. This body is
    # broken JSON, so if it were parsed the answer would be invalid_request.
    oversized_body = b"{" + b" " * 70_000

    response = client.post(
        VERSIONS_PATH, content=oversized_body, headers={"Content-Type": "application/json"}
    )

    assert response.status_code == 413
    assert_error_shape(response.json(), "input_too_large")
    assert fake_claude_client.messages.calls == []


def test_ac44_body_just_under_64kb_still_gets_the_normal_error(client: TestClient) -> None:
    # Spec amendment: the cap only catches oversized bodies; a smaller broken body is parsed.
    body_under_the_cap = b"{" + b" " * 60_000

    response = client.post(
        VERSIONS_PATH, content=body_under_the_cap, headers={"Content-Type": "application/json"}
    )

    assert response.status_code == 400
    assert_error_shape(response.json(), "invalid_request")


def test_ac44_chunked_body_over_64kb_without_content_length_is_input_too_large(
    client: TestClient, fake_claude_client: FakeClaudeClient
) -> None:
    # Spec amendment: the cap counts the bytes read, so a body with no Content-Length is capped.
    chunks = iter([b"{" + b" " * 40_000, b" " * 40_000])

    response = client.post(
        VERSIONS_PATH, content=chunks, headers={"Content-Type": "application/json"}
    )

    assert "content-length" not in response.request.headers
    assert response.status_code == 413
    assert_error_shape(response.json(), "input_too_large")
    assert fake_claude_client.messages.calls == []


def send_raw_request(app: FastAPI, headers: list[tuple[bytes, bytes]], chunks: list[bytes]) -> int:
    """Call the ASGI app directly with `chunks` as the body; return the response status."""
    return response_status(run_like_uvicorn(app, headers, body_messages(chunks)))


def test_ac44_body_over_64kb_with_a_false_small_content_length_is_input_too_large(
    app: FastAPI, fake_claude_client: FakeClaudeClient
) -> None:
    # Spec amendment: a lying Content-Length cannot get a large body past the cap.
    headers = [
        (b"host", b"127.0.0.1:8000"),
        (b"content-type", b"application/json"),
        (b"content-length", b"10"),
    ]
    chunks = [b"{" + b" " * 40_000, b" " * 40_000]

    status = send_raw_request(app, headers, chunks)

    assert status == 413
    assert fake_claude_client.messages.calls == []


# A client that disconnects mid-body never reaches the app (T7 follow-up).


def test_ac44_client_disconnecting_mid_body_never_reaches_the_app_or_claude(
    app: FastAPI,
    fake_claude_client: FakeClaudeClient,
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The body cap reads the whole body first; a cut-off body never reaches the route."""
    caplog.set_level(logging.DEBUG)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-real")
    whole_body = json.dumps({"lyrics": "夜の月が ひかる"}, ensure_ascii=False).encode()
    # The first chunk is a complete, valid body, but `more_body` says more is coming; then the
    # client disconnects.
    incoming: list[Message] = [{"type": "http.request", "body": whole_body, "more_body": True}]

    run_like_uvicorn(app, [ALLOWED_HOST_HEADER, JSON_CONTENT_TYPE_HEADER], incoming)

    # The route always calls Claude for this paste and always writes its one request line.
    assert fake_claude_client.messages.calls == []
    assert [record for record in caplog.records if record.name == REQUEST_LOGGER] == []


def test_ac44_client_disconnecting_mid_body_gets_no_response_and_logs_no_traceback(
    app: FastAPI, caplog: pytest.LogCaptureFixture
) -> None:
    """A cut-off body ends quietly: nothing is sent and nothing reaches uvicorn's log."""
    caplog.set_level(logging.DEBUG)
    whole_body = json.dumps({"lyrics": "夜の月が ひかる"}, ensure_ascii=False).encode()
    incoming: list[Message] = [{"type": "http.request", "body": whole_body, "more_body": True}]

    sent = run_like_uvicorn(app, [ALLOWED_HOST_HEADER, JSON_CONTENT_TYPE_HEADER], incoming)

    assert sent == []
    assert [record for record in caplog.records if record.name == UVICORN_ERROR_LOGGER] == []
