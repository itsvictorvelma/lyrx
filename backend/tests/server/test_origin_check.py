"""Tests for the Origin check on requests that change data (spec 014 AC-11)."""

import pytest
from conftest import ALLOWED_TEST_BASE_URL
from error_shape import assert_error_shape
from fastapi import FastAPI
from fastapi.testclient import TestClient

from subbed import config
from subbed.accounts.routes import SIGN_UP_PATH
from subbed.app import RECENT_SONGS_PATH, SONG_SEARCH_PATH
from subbed.server.origin_check import origin_is_allowed

SIGN_UP_BODY = {"username": "mika", "password": "correct horse battery"}


@pytest.fixture
def no_origin_client(app: FastAPI) -> TestClient:
    """A client that sends no Origin unless a test adds one."""
    return TestClient(app, base_url=ALLOWED_TEST_BASE_URL, raise_server_exceptions=False)


@pytest.mark.parametrize(
    "origin",
    [None, "https://evil.example", "http://127.0.0.1.evil.example", "null", "not a url"],
)
@pytest.mark.parametrize("path", [SIGN_UP_PATH, SONG_SEARCH_PATH])
def test_ac11_a_post_with_a_foreign_or_missing_origin_is_bad_origin(
    no_origin_client: TestClient, origin: str | None, path: str
) -> None:
    headers = {} if origin is None else {"Origin": origin}

    response = no_origin_client.post(path, json=SIGN_UP_BODY, headers=headers)

    assert response.status_code == 403
    assert_error_shape(response.json(), "bad_origin")


@pytest.mark.parametrize("method", ["PUT", "DELETE"])
def test_ac11_put_and_delete_are_checked_too(no_origin_client: TestClient, method: str) -> None:
    response = no_origin_client.request(method, "/api/songs/101/saved")

    assert response.status_code == 403
    assert_error_shape(response.json(), "bad_origin")


@pytest.mark.parametrize(
    "origin", ["http://127.0.0.1:5173", "http://localhost:5173", "http://localhost"]
)
def test_ac11_the_pages_own_origin_is_allowed(no_origin_client: TestClient, origin: str) -> None:
    response = no_origin_client.post(SIGN_UP_PATH, json=SIGN_UP_BODY, headers={"Origin": origin})

    assert response.status_code == 200


def test_ac11_get_is_not_checked(no_origin_client: TestClient) -> None:
    response = no_origin_client.get(RECENT_SONGS_PATH, headers={"Origin": "https://evil.example"})

    assert response.status_code == 200


def test_spec020_ac2_the_allowed_hosts_setting_sets_the_allowed_origin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(config, "ALLOWED_HOST_NAMES", frozenset({"subbed.example"}))

    assert origin_is_allowed("https://subbed.example")
    assert not origin_is_allowed("http://127.0.0.1:5173")
    assert not origin_is_allowed("https://evil.example")
