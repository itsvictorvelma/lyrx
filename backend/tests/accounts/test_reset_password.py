"""Tests for the password reset command (spec 014 AC-14)."""

import getpass

import pytest
from conftest import TEST_PASSWORD, sign_up
from fastapi.testclient import TestClient

from lyrx.accounts import reset_password
from lyrx.accounts.routes import ACCOUNT_PATH, SIGN_IN_PATH

NEW_PASSWORD = "a brand new password"


def type_passwords(monkeypatch: pytest.MonkeyPatch, *typed: str) -> None:
    answers = list(typed)
    monkeypatch.setattr(getpass, "getpass", lambda _prompt: answers.pop(0))


def test_ac14_the_reset_sets_a_new_password_and_signs_the_person_out_everywhere(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    sign_up(client, "mika")
    type_passwords(monkeypatch, NEW_PASSWORD, NEW_PASSWORD)

    assert reset_password.main(["mika"]) == 0

    assert client.get(ACCOUNT_PATH).json() == {"username": None}
    old = client.post(SIGN_IN_PATH, json={"username": "mika", "password": TEST_PASSWORD})
    new = client.post(SIGN_IN_PATH, json={"username": "mika", "password": NEW_PASSWORD})
    assert (old.status_code, new.status_code) == (401, 200)


@pytest.mark.parametrize(
    ("username", "typed"),
    [
        ("nobody", (NEW_PASSWORD, NEW_PASSWORD)),
        ("mika", (NEW_PASSWORD, "something else")),
        ("mika", ("short", "short")),
    ],
)
def test_an_unknown_name_or_a_bad_password_changes_nothing(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, username: str, typed: tuple[str, str]
) -> None:
    sign_up(client, "mika")
    type_passwords(monkeypatch, *typed)

    assert reset_password.main([username]) == 1

    assert client.get(ACCOUNT_PATH).json() == {"username": "mika"}
