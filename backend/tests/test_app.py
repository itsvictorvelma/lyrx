"""Tests for the app shell: the one error shape, routing errors, the sync route, and the client."""

import inspect

import pytest
from error_shape import ERROR_SHAPE_KEYS, assert_error_shape
from fastapi import FastAPI, HTTPException
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from lyrx.app import SONG_SEARCH_PATH, SONG_VERSIONS_PATH, VERSIONS_PATH


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


@pytest.mark.parametrize("path", ["/docs", "/redoc", "/openapi.json"])
def test_ac42_api_docs_pages_are_disabled_and_not_found(client: TestClient, path: str) -> None:
    """The docs pages would load assets from a CDN, so the app turns them off."""
    response = client.get(path)

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


# The routes run in FastAPI's threadpool.


@pytest.mark.parametrize("path", [VERSIONS_PATH, SONG_SEARCH_PATH, SONG_VERSIONS_PATH])
def test_routes_are_sync_functions_so_blocking_calls_run_off_the_event_loop(
    app: FastAPI, path: str
) -> None:
    routes = [route for route in app.routes if isinstance(route, APIRoute) and route.path == path]

    assert len(routes) == 1
    assert not inspect.iscoroutinefunction(routes[0].endpoint)
