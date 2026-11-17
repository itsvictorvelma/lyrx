"""Tests for the app shell: the one error shape, the Host check, and errors that leak nothing."""

import inspect
import json
import logging

import pytest
from error_shape import ERROR_SHAPE_KEYS, assert_error_shape
from fake_claude import FakeClaudeClient, fake_message
from fastapi import FastAPI, HTTPException
from fastapi.routing import APIRoute
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

from lyrx import claude
from lyrx.app import VERSIONS_PATH, create_app


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


# The route runs in FastAPI's threadpool (T7 follow-up).


def test_ac2_versions_route_is_a_sync_function_so_the_checks_run_off_the_event_loop(
    app: FastAPI,
) -> None:
    """The reading checks are CPU-bound; a sync `def` route keeps them off the event loop."""
    routes = [
        route for route in app.routes if isinstance(route, APIRoute) and route.path == VERSIONS_PATH
    ]

    assert len(routes) == 1
    assert not inspect.iscoroutinefunction(routes[0].endpoint)


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


# The crash guard: no exception escapes the app to uvicorn's traceback log.

REQUEST_LOGGER = "lyrx.request_log"
CRASH_GUARD_LOGGER = "lyrx.crash_guard"
CRASH_PATH = "/api/raise-outside-the-pipeline"
CRASH_SECRETS = ["/Users/someone/lyrx/src/lyrx/app.py", "君の声が 遠く ひびく", "test-key-not-real"]


def test_ac32_crash_guard_stops_an_exception_raised_outside_the_pipeline(
    app: FastAPI, caplog: pytest.LogCaptureFixture
) -> None:
    """A 500 in the error shape, no uvicorn traceback, one crash line with just the class name."""
    caplog.set_level(logging.DEBUG)

    def raise_outside_the_pipeline() -> None:
        raise RuntimeError(" ".join(CRASH_SECRETS))

    app.add_api_route(CRASH_PATH, raise_outside_the_pipeline, methods=["POST"])

    sent = run_like_uvicorn(app, [ALLOWED_HOST_HEADER], body_messages([b""]), path=CRASH_PATH)

    assert response_status(sent) == 500
    body = response_body(sent).decode()
    assert_error_shape(json.loads(body), "internal_error")
    assert [record for record in caplog.records if record.name == UVICORN_ERROR_LOGGER] == []
    crash_records = [record for record in caplog.records if record.name == CRASH_GUARD_LOGGER]
    assert len(crash_records) == 1
    assert "RuntimeError" in crash_records[0].getMessage()
    crash_text = logging.Formatter().format(crash_records[0]) + repr(crash_records[0].__dict__)
    for secret in CRASH_SECRETS:
        assert secret not in crash_text
        assert secret not in body


# The real SDK client is built only when a request needs it (T7 follow-up).

REAL_CLIENT_TEST_KEY = "test-key-for-make-client"
REAL_CLIENT_REPLY = '{"lines": [{"index": 0, "reading": "よる", "english": "Night"}]}'


@pytest.fixture
def made_clients(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Replaces `claude.make_client` with one that records the key and returns a fake client."""
    keys: list[str] = []

    def make_fake_client(api_key: str) -> FakeClaudeClient:
        keys.append(api_key)
        fake = FakeClaudeClient()
        fake.messages.final_message = fake_message(REAL_CLIENT_REPLY)
        return fake

    monkeypatch.setattr(claude, "make_client", make_fake_client)
    return keys


def test_ac2_without_a_client_create_app_uses_make_client_with_the_api_key(
    made_clients: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """No client is built by `create_app`; the request builds one from the environment's key."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", REAL_CLIENT_TEST_KEY)
    real_app = create_app()
    assert made_clients == []

    with TestClient(real_app, base_url="http://127.0.0.1:8000") as test_client:
        response = test_client.post(VERSIONS_PATH, json={"lyrics": "夜"})

    assert response.status_code == 200
    assert response.json()["lines"][0]["hiragana"] == "よる"
    assert made_clients == [REAL_CLIENT_TEST_KEY]


@pytest.mark.parametrize(
    ("lyrics", "api_key", "expected_status", "expected_code"),
    [
        ("We sing tonight", REAL_CLIENT_TEST_KEY, 400, "no_japanese"),
        ("   ", REAL_CLIENT_TEST_KEY, 400, "empty_input"),
        ("夜", None, 503, "server_not_configured"),
    ],
)
def test_ac22_a_refused_paste_never_builds_the_real_client(
    made_clients: list[str],
    monkeypatch: pytest.MonkeyPatch,
    lyrics: str,
    api_key: str | None,
    expected_status: int,
    expected_code: str,
) -> None:
    """Every refusal before the call happens before the real client is built."""
    if api_key is None:
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    else:
        monkeypatch.setenv("ANTHROPIC_API_KEY", api_key)

    with TestClient(create_app(), base_url="http://127.0.0.1:8000") as test_client:
        response = test_client.post(VERSIONS_PATH, json={"lyrics": lyrics})

    assert response.status_code == expected_status
    assert_error_shape(response.json(), expected_code)
    assert made_clients == []
