"""Tests for the order of the pipeline: split, limits, key; every refusal comes before Claude."""

import pytest
from error_shape import assert_error_shape
from fake_claude import FakeClaudeClient
from fastapi.testclient import TestClient
from pastes import (
    LIMIT_DETAILS,
    LIMIT_MESSAGE,
    japanese_line,
    paste_of_characters,
    paste_of_lines,
)

from lyrx.app import VERSIONS_PATH

FAKE_API_KEY = "test-key-not-real"
VALID_PASTE = "君の声が\n遠く ひびく\n\nWe sing tonight"


@pytest.fixture
def with_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", FAKE_API_KEY)


@pytest.fixture
def without_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)


def post_lyrics(client: TestClient, lyrics: str) -> tuple[int, object]:
    response = client.post(VERSIONS_PATH, json={"lyrics": lyrics})
    return response.status_code, response.json()


def assert_passed_the_limits(client: TestClient, lyrics: str) -> None:
    """With no key set, a paste that passes split and limits stops at the key check.

    The pipeline checks the key right after the limits and before Claude, so
    `server_not_configured` proves the limits accepted the paste. This holds at
    every task, before and after the Claude call exists.
    """
    status, body = post_lyrics(client, lyrics)

    assert status == 503
    assert_error_shape(body, "server_not_configured")


# Empty input (AC-5)


@pytest.mark.usefixtures("with_api_key")
@pytest.mark.parametrize("lyrics", ["", "   ", "\n\n\n", " \r\n\t\r \n  ", "\u3000\n "])
def test_ac5_whitespace_only_paste_is_empty_input_and_claude_is_not_called(
    client: TestClient, fake_claude_client: FakeClaudeClient, lyrics: str
) -> None:
    status, body = post_lyrics(client, lyrics)

    assert status == 400
    assert_error_shape(body, "empty_input")
    assert fake_claude_client.messages.calls == []


# Character limit (AC-6)


@pytest.mark.usefixtures("with_api_key")
def test_ac6_paste_of_5001_characters_is_input_too_large_and_claude_is_not_called(
    client: TestClient, fake_claude_client: FakeClaudeClient
) -> None:
    status, body = post_lyrics(client, paste_of_characters(5001))

    assert status == 413
    assert_error_shape(body, "input_too_large")
    assert isinstance(body, dict)
    assert body["details"] == LIMIT_DETAILS
    assert fake_claude_client.messages.calls == []


@pytest.mark.usefixtures("without_api_key")
def test_ac6_paste_of_exactly_5000_characters_passes_the_limits(client: TestClient) -> None:
    assert_passed_the_limits(client, paste_of_characters(5000))


@pytest.mark.usefixtures("without_api_key")
def test_ac6_carriage_return_newline_counts_once_toward_the_character_limit(
    client: TestClient,
) -> None:
    lyrics = paste_of_characters(5000, line_ending="\r\n")
    assert len(lyrics) > 5000

    assert_passed_the_limits(client, lyrics)


# Line limit (AC-7)


@pytest.mark.usefixtures("with_api_key")
def test_ac7_paste_of_201_lines_is_input_too_large_and_claude_is_not_called(
    client: TestClient, fake_claude_client: FakeClaudeClient
) -> None:
    status, body = post_lyrics(client, paste_of_lines(201))

    assert status == 413
    assert_error_shape(body, "input_too_large")
    assert isinstance(body, dict)
    assert body["details"] == LIMIT_DETAILS
    assert fake_claude_client.messages.calls == []


@pytest.mark.usefixtures("without_api_key")
def test_ac7_paste_of_exactly_200_lines_passes_the_limits(client: TestClient) -> None:
    assert_passed_the_limits(client, paste_of_lines(200))


# Line length limit (AC-45)


@pytest.mark.usefixtures("with_api_key")
def test_ac45_line_of_201_characters_is_input_too_large_and_claude_is_not_called(
    client: TestClient, fake_claude_client: FakeClaudeClient
) -> None:
    status, body = post_lyrics(client, "夜の月\n" + japanese_line(201))

    assert status == 413
    assert_error_shape(body, "input_too_large")
    assert isinstance(body, dict)
    assert body["details"] == LIMIT_DETAILS
    assert body["message"] == LIMIT_MESSAGE
    assert fake_claude_client.messages.calls == []


@pytest.mark.usefixtures("without_api_key")
def test_ac45_line_of_exactly_200_characters_passes_the_limits(client: TestClient) -> None:
    assert_passed_the_limits(client, japanese_line(200))


@pytest.mark.usefixtures("without_api_key")
def test_ac7_lines_are_counted_after_splitting(client: TestClient) -> None:
    lyrics = "\r\n\r\n" + paste_of_lines(100, "\r\n") + "\r\n\r\n\r\n" + paste_of_lines(99, "\r\n")

    assert_passed_the_limits(client, lyrics + "\r\n\r\n\r\n")


# No Japanese (AC-8)


@pytest.mark.usefixtures("with_api_key")
@pytest.mark.parametrize(
    "lyrics",
    ["We sing tonight\nUnder the paper moon", "Oh oh oh!\n\n123, go!", "、。「」\uff01\uff1f"],
)
def test_ac8_paste_without_japanese_is_no_japanese_and_claude_is_not_called(
    client: TestClient, fake_claude_client: FakeClaudeClient, lyrics: str
) -> None:
    status, body = post_lyrics(client, lyrics)

    assert status == 400
    assert_error_shape(body, "no_japanese")
    assert fake_claude_client.messages.calls == []


# Missing API key (AC-22)


@pytest.mark.usefixtures("without_api_key")
def test_ac22_unset_api_key_is_server_not_configured_and_claude_is_not_called(
    client: TestClient, fake_claude_client: FakeClaudeClient
) -> None:
    status, body = post_lyrics(client, VALID_PASTE)

    assert status == 503
    assert_error_shape(body, "server_not_configured")
    assert fake_claude_client.messages.calls == []


def test_ac22_empty_api_key_counts_as_unset(
    client: TestClient, fake_claude_client: FakeClaudeClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    # `.env.example` ships `ANTHROPIC_API_KEY=`, which loads as an empty string.
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")

    status, body = post_lyrics(client, VALID_PASTE)

    assert status == 503
    assert_error_shape(body, "server_not_configured")
    assert fake_claude_client.messages.calls == []


@pytest.mark.usefixtures("without_api_key")
def test_ac22_size_limits_are_checked_before_the_api_key(
    client: TestClient, fake_claude_client: FakeClaudeClient
) -> None:
    status, body = post_lyrics(client, paste_of_lines(201))

    assert status == 413
    assert_error_shape(body, "input_too_large")
    assert fake_claude_client.messages.calls == []
