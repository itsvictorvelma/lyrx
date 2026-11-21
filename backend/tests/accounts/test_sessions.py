"""Tests for sessions: the cookie's flags, the stored hash, sign-out, and expiry (spec 014)."""

import sqlite3
from contextlib import closing
from pathlib import Path

import pytest
from conftest import sign_up
from fastapi.testclient import TestClient

from lyrx import config
from lyrx.accounts.sessions import hash_token
from lyrx.app import SAVED_SONGS_PATH

ACCOUNT_PATH = "/api/account"


def session_cookie_header(client: TestClient) -> str:
    response = client.post(
        "/api/account/sign-up", json={"username": "mika", "password": "correct horse battery"}
    )
    assert response.status_code == 200
    header: str = response.headers["set-cookie"]
    return header


def stored_token_hashes(path: Path) -> list[str]:
    with closing(sqlite3.connect(path)) as connection:
        return [row[0] for row in connection.execute("SELECT token_hash FROM sessions")]


def test_ac3_the_cookie_is_httponly_and_lax_and_not_secure_by_default(
    client: TestClient, temporary_database: Path
) -> None:
    header = session_cookie_header(client).lower()

    assert header.startswith(f"{config.SESSION_COOKIE_NAME}=")
    assert "httponly" in header
    assert "samesite=lax" in header
    assert "path=/" in header
    assert "secure" not in header.replace("samesite", "")


def test_ac3_spec020_ac7_the_cookie_is_secure_when_the_setting_is_on(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(config, "SECURE_COOKIES", True)

    assert "; secure" in session_cookie_header(client).lower()


def test_ac3_the_database_holds_the_tokens_hash_not_the_token(
    client: TestClient, temporary_database: Path
) -> None:
    sign_up(client)
    token = client.cookies[config.SESSION_COOKIE_NAME]

    assert stored_token_hashes(temporary_database) == [hash_token(token)]
    assert token not in temporary_database.read_bytes().decode(errors="ignore")


def test_ac4_signing_out_removes_the_session_and_the_old_cookie_stops_working(
    client: TestClient, temporary_database: Path
) -> None:
    sign_up(client)
    token = client.cookies[config.SESSION_COOKIE_NAME]

    response = client.post("/api/account/sign-out")

    assert response.status_code == 204
    assert stored_token_hashes(temporary_database) == []
    client.cookies.set(config.SESSION_COOKIE_NAME, token)
    assert client.get(ACCOUNT_PATH).json() == {"username": None}
    assert client.get(SAVED_SONGS_PATH).status_code == 401


def test_ac4_an_expired_session_is_not_accepted_and_is_removed_at_the_next_sign_in(
    client: TestClient, temporary_database: Path
) -> None:
    sign_up(client)
    with closing(sqlite3.connect(temporary_database)) as connection, connection:
        connection.execute("UPDATE sessions SET expires_at = 1.0")

    assert client.get(ACCOUNT_PATH).json() == {"username": None}

    client.post(
        "/api/account/sign-in", json={"username": "mika", "password": "correct horse battery"}
    )
    assert len(stored_token_hashes(temporary_database)) == 1


def test_a_cookie_too_long_to_be_a_token_counts_as_a_guest(client: TestClient) -> None:
    client.cookies.set(config.SESSION_COOKIE_NAME, "x" * 500)

    assert client.get(ACCOUNT_PATH).json() == {"username": None}
