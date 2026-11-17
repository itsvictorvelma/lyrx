"""Tests for the app shell: the one error shape, routing errors, the sync route, and the client."""

import inspect

import pytest
from error_shape import ERROR_SHAPE_KEYS, assert_error_shape
from fake_claude import FakeClaudeClient, fake_message
from fastapi import FastAPI, HTTPException
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

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
