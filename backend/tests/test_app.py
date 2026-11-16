"""Tests for the app shell: the one error shape, the Host check, and errors that leak nothing."""

import asyncio
import json

import pytest
from error_shape import ERROR_SHAPE_KEYS, assert_error_shape
from fake_claude import FakeClaudeClient
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from starlette.types import Message

from lyrx.app import VERSIONS_PATH


def test_ac9_body_that_is_not_json_is_invalid_request(client: TestClient) -> None:
    response = client.post(
        VERSIONS_PATH,
        content=b"{not json at all",
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 400
    assert_error_shape(response.json(), "invalid_request")


def test_ac9_body_without_lyrics_is_invalid_request(client: TestClient) -> None:
    response = client.post(VERSIONS_PATH, json={"text": "ほしが ひかる"})

    assert response.status_code == 400
    assert_error_shape(response.json(), "invalid_request")


@pytest.mark.parametrize("lyrics", [42, 3.5, None, ["ほしが ひかる"], {"line": "そら"}])
def test_ac9_lyrics_that_is_not_a_string_is_invalid_request(
    client: TestClient, lyrics: object
) -> None:
    response = client.post(VERSIONS_PATH, json={"lyrics": lyrics})

    assert response.status_code == 400
    assert_error_shape(response.json(), "invalid_request")


@pytest.mark.parametrize(
    "host",
    [
        "",
        "evil.example",
        "evil.example:8000",
        "localhost.evil.example",
        "127.0.0.1.evil.example",
        "0.0.0.0:8000",
    ],
)
def test_ac30_foreign_host_is_rejected(client: TestClient, host: str) -> None:
    response = client.post(VERSIONS_PATH, json={"lyrics": "夜の月"}, headers={"Host": host})

    assert response.status_code == 403
    assert_error_shape(response.json(), "host_not_allowed")


def test_ac30_foreign_host_is_rejected_before_routing(client: TestClient) -> None:
    response = client.get("/no-such-page", headers={"Host": "evil.example"})

    assert response.status_code == 403
    assert_error_shape(response.json(), "host_not_allowed")


@pytest.mark.parametrize(
    "host", ["127.0.0.1", "127.0.0.1:8000", "localhost", "localhost:8000", "localhost:5173"]
)
def test_ac30_local_host_passes_the_host_check(client: TestClient, host: str) -> None:
    # A body without `lyrics` keeps the request away from Claude; only the Host check matters.
    response = client.post(VERSIONS_PATH, json={}, headers={"Host": host})

    assert response.status_code == 400
    assert_error_shape(response.json(), "invalid_request")


def test_ac32_unexpected_exception_is_internal_error_without_leaks(
    app: FastAPI, client: TestClient
) -> None:
    exception_text = "secret-path /Users/someone/lyrx/src/lyrx/app.py boom"

    def raise_unexpected_error() -> None:
        raise RuntimeError(exception_text)

    app.add_api_route("/api/raise-unexpected-error", raise_unexpected_error, methods=["GET"])

    response = client.get("/api/raise-unexpected-error")

    assert response.status_code == 500
    assert_error_shape(response.json(), "internal_error")
    for leaked in (exception_text, "secret-path", "/Users", "boom", "Traceback", "RuntimeError"):
        assert leaked not in response.text


def test_ac42_unknown_path_is_not_found_in_the_error_shape(client: TestClient) -> None:
    response = client.get("/api/no-such-route")

    assert response.status_code == 404
    assert_error_shape(response.json(), "not_found")
    assert set(response.json()) <= ERROR_SHAPE_KEYS


def test_ac42_unknown_path_with_post_is_not_found(client: TestClient) -> None:
    response = client.post("/api/no-such-route", json={"lyrics": "夜の月"})

    assert response.status_code == 404
    assert_error_shape(response.json(), "not_found")


def test_ac42_get_on_versions_route_is_method_not_allowed(client: TestClient) -> None:
    response = client.get(VERSIONS_PATH)

    assert response.status_code == 405
    assert_error_shape(response.json(), "method_not_allowed")
    assert set(response.json()) <= ERROR_SHAPE_KEYS


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
    incoming: list[Message] = [
        {"type": "http.request", "body": chunk, "more_body": index < len(chunks) - 1}
        for index, chunk in enumerate(chunks)
    ]
    sent: list[Message] = []

    async def receive() -> Message:
        if incoming:
            return incoming.pop(0)
        return {"type": "http.disconnect"}

    async def send(message: Message) -> None:
        sent.append(message)

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": VERSIONS_PATH,
        "raw_path": VERSIONS_PATH.encode(),
        "query_string": b"",
        "root_path": "",
        "headers": headers,
        "client": ("127.0.0.1", 50000),
        "server": ("127.0.0.1", 8000),
    }
    asyncio.run(app(scope, receive, send))
    start = next(message for message in sent if message["type"] == "http.response.start")
    status: int = start["status"]
    return status


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


@pytest.mark.parametrize(
    ("raised_status", "expected_status", "expected_code"),
    [(418, 400, "invalid_request"), (503, 500, "internal_error")],
)
def test_ac44_other_http_exceptions_map_to_the_error_shape_without_their_detail(
    app: FastAPI,
    client: TestClient,
    raised_status: int,
    expected_status: int,
    expected_code: str,
) -> None:
    # Spec amendment: other client errors are invalid_request; a server error leaks nothing.
    def raise_http_exception() -> None:
        raise HTTPException(raised_status, detail="secret-detail")

    app.add_api_route("/api/raise-http-exception", raise_http_exception, methods=["GET"])

    response = client.get("/api/raise-http-exception")

    assert response.status_code == expected_status
    assert_error_shape(response.json(), expected_code)
    assert "secret-detail" not in response.text


def test_ac30_foreign_host_is_rejected_before_the_body_size_cap(
    client: TestClient, fake_claude_client: FakeClaudeClient
) -> None:
    oversized_body = json.dumps({"lyrics": "夜の月" * 30_000}).encode()
    assert len(oversized_body) > 70_000

    response = client.post(
        VERSIONS_PATH,
        content=oversized_body,
        headers={"Content-Type": "application/json", "Host": "evil.example"},
    )

    assert response.status_code == 403
    assert_error_shape(response.json(), "host_not_allowed")
    assert fake_claude_client.messages.calls == []
