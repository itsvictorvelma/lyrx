"""Tests for the app shell: the one error shape, the Host check, and errors that leak nothing."""

from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

ERROR_SHAPE_KEYS = {"code", "message", "details"}
VERSIONS_PATH = "/api/versions"


def assert_error_shape(body: Any, expected_code: str) -> None:
    assert isinstance(body, dict)
    assert set(body) <= ERROR_SHAPE_KEYS
    assert body["code"] == expected_code
    assert isinstance(body["message"], str)
    assert body["message"] != ""


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

    assert response.status_code != 403
    assert response.json().get("code") != "host_not_allowed"


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
