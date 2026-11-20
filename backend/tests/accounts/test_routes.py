"""Tests for the account routes: sign up, sign in, the abuse limits, and delete (spec 014)."""

import logging
from typing import Any

import pytest
from conftest import TEST_PASSWORD, make_client, sign_up
from error_shape import assert_error_shape
from fake_gemini import FakeGemini, answer_with_placeholders
from fake_lrclib import FakeLrclib, json_reply, record
from fastapi import FastAPI
from fastapi.testclient import TestClient

from lyrx import library
from lyrx.accounts.routes import ACCOUNT_PATH, SIGN_IN_PATH, SIGN_UP_PATH
from lyrx.app import SAVED_SONGS_PATH, SONG_VERSIONS_PATH

VIDEO_ID = "abcDEF12_-z"


def post_account(client: TestClient, path: str, username: str, password: str) -> Any:
    return client.post(path, json={"username": username, "password": password})


def test_ac1_creating_an_account_signs_in_and_the_account_route_names_it(
    client: TestClient,
) -> None:
    assert client.get(ACCOUNT_PATH).json() == {"username": None}

    response = post_account(client, SIGN_UP_PATH, "Mika_01", TEST_PASSWORD)

    assert response.status_code == 200
    assert response.json() == {"username": "mika_01"}
    assert client.get(ACCOUNT_PATH).json() == {"username": "mika_01"}


def test_ac1_a_taken_username_in_any_letter_case_is_username_taken(
    app: FastAPI, client: TestClient
) -> None:
    sign_up(client, "mika")

    with make_client(app) as other:
        response = post_account(other, SIGN_UP_PATH, "MIKA", TEST_PASSWORD)

    assert response.status_code == 409
    assert_error_shape(response.json(), "username_taken")


@pytest.mark.parametrize(
    ("username", "password"),
    [
        ("ab", TEST_PASSWORD),
        ("a" * 31, TEST_PASSWORD),
        ("mika chan", TEST_PASSWORD),
        ("みか", TEST_PASSWORD),
        ("mika", "short"),
        ("mika", "x" * 129),
    ],
)
def test_ac1_a_bad_username_or_password_is_invalid_request(
    client: TestClient, username: str, password: str
) -> None:
    response = post_account(client, SIGN_UP_PATH, username, password)

    assert response.status_code == 400
    assert_error_shape(response.json(), "invalid_request")


def test_ac2_the_right_password_signs_in(app: FastAPI, client: TestClient) -> None:
    sign_up(client)

    with make_client(app) as other:
        response = post_account(other, SIGN_IN_PATH, "MIKA", TEST_PASSWORD)
        assert response.status_code == 200
        assert other.get(ACCOUNT_PATH).json() == {"username": "mika"}


def test_ac2_a_wrong_password_and_an_unknown_username_give_the_same_reply(
    app: FastAPI, client: TestClient
) -> None:
    sign_up(client)

    with make_client(app) as other:
        wrong = post_account(other, SIGN_IN_PATH, "mika", "wrong password")
        unknown = post_account(other, SIGN_IN_PATH, "nobody", TEST_PASSWORD)

    assert (wrong.status_code, unknown.status_code) == (401, 401)
    assert wrong.json() == unknown.json()
    assert_error_shape(wrong.json(), "sign_in_failed")


def test_ac10_the_sixth_sign_up_from_one_ip_in_a_day_is_too_many_attempts(
    client: TestClient,
) -> None:
    for number in range(5):
        assert post_account(client, SIGN_UP_PATH, f"user{number}", TEST_PASSWORD).status_code == 200

    response = post_account(client, SIGN_UP_PATH, "user5", TEST_PASSWORD)

    assert response.status_code == 429
    assert_error_shape(response.json(), "too_many_attempts")


def test_ac10_the_eleventh_failed_sign_in_in_an_hour_is_refused_even_with_the_right_password(
    app: FastAPI, client: TestClient
) -> None:
    sign_up(client)

    with make_client(app) as other:
        for _ in range(10):
            assert post_account(other, SIGN_IN_PATH, "mika", "wrong password").status_code == 401
        response = post_account(other, SIGN_IN_PATH, "mika", TEST_PASSWORD)

    assert response.status_code == 429
    assert_error_shape(response.json(), "too_many_attempts")


@pytest.mark.usefixtures("gemini_key")
def test_ac12_deleting_the_account_removes_its_sessions_and_saved_songs_but_not_the_cache(
    client: TestClient, fake_lrclib: FakeLrclib, fake_gemini: FakeGemini
) -> None:
    sign_up(client)
    fake_lrclib.script(json_reply(record()))
    fake_gemini.answer = answer_with_placeholders
    client.post(SONG_VERSIONS_PATH, json={"id": 101})
    client.put(f"{SAVED_SONGS_PATH}/101/saved", json={"videoId": VIDEO_ID, "offsetMs": 0})

    response = client.request("DELETE", ACCOUNT_PATH, json={"password": TEST_PASSWORD})

    assert response.status_code == 204
    assert client.get(ACCOUNT_PATH).json() == {"username": None}
    assert library.find_song(101) is not None
    assert post_account(client, SIGN_IN_PATH, "mika", TEST_PASSWORD).status_code == 401
    sign_up(client, "mika")
    assert client.get(SAVED_SONGS_PATH).json()["songs"] == []


def test_ac12_a_wrong_password_changes_nothing(client: TestClient) -> None:
    sign_up(client)

    response = client.request("DELETE", ACCOUNT_PATH, json={"password": "wrong password"})

    assert response.status_code == 401
    assert_error_shape(response.json(), "sign_in_failed")
    assert client.get(ACCOUNT_PATH).json() == {"username": "mika"}


def test_deleting_as_a_guest_is_sign_in_required(client: TestClient) -> None:
    response = client.request("DELETE", ACCOUNT_PATH, json={"password": TEST_PASSWORD})

    assert response.status_code == 401
    assert_error_shape(response.json(), "sign_in_required")


def test_the_log_has_the_event_and_user_id_but_never_the_password_or_token(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO)

    sign_up(client)
    post_account(client, SIGN_IN_PATH, "mika", "wrong password")

    assert "event=signed_up" in caplog.text
    assert "user_id=1" in caplog.text
    assert "code=sign_in_failed" in caplog.text
    assert TEST_PASSWORD not in caplog.text
    assert "wrong password" not in caplog.text
    assert client.cookies["lyrx_session"] not in caplog.text
