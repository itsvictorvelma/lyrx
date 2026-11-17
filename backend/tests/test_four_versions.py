"""Tests for the pipeline: refusals before Claude, the four versions, errors, and logging."""

import json
import logging
import re
from typing import Any

import anthropic
import httpx2
import pytest
from anthropic.types import Message
from error_shape import assert_error_shape
from fake_claude import ErrorPoint, FakeClaudeClient, fake_message
from fastapi import FastAPI
from fastapi.testclient import TestClient
from raw_asgi import (
    ALLOWED_HOST_HEADER,
    JSON_CONTENT_TYPE_HEADER,
    body_messages,
    response_body,
    response_status,
    run_like_uvicorn,
)

from lyrx import four_versions, readings
from lyrx.app import VERSIONS_PATH
from lyrx.lines import split_lines
from lyrx.prompt import build_user_message
from lyrx.romaji import to_romaji

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


# The four versions (AC-2, 3, 4, 18, 29). From here on the key is set and Claude is the fake.

# The spec's example paste: line 2 is blank, line 3 has no Japanese.
SPEC_ITEMS: list[dict[str, Any]] = [
    {"index": 0, "reading": "きみ の こえ が", "english": "Your voice"},
    {"index": 1, "reading": "とおく ひびく", "english": "echoes far away"},
    {"index": 3, "reading": "We sing tonight", "english": "We sing tonight"},
]
SPEC_RESPONSE = {
    "lines": [
        {
            "index": 0,
            "original": "君の声が",
            "hiragana": "きみ の こえ が",
            "romaji": "kimi no koe ga",
            "english": "Your voice",
            "readingVerified": True,
        },
        {
            "index": 1,
            "original": "遠く ひびく",
            "hiragana": "とおく ひびく",
            "romaji": "tooku hibiku",
            "english": "echoes far away",
            "readingVerified": True,
        },
        {
            "index": 2,
            "original": "",
            "hiragana": "",
            "romaji": "",
            "english": "",
            "readingVerified": True,
        },
        {
            "index": 3,
            "original": "We sing tonight",
            "hiragana": "We sing tonight",
            "romaji": "We sing tonight",
            "english": "We sing tonight",
            "readingVerified": True,
        },
    ]
}
LINE_FIELDS = {"index", "original", "hiragana", "romaji", "english", "readingVerified"}


def reply_text(items: list[dict[str, Any]]) -> str:
    return json.dumps({"lines": items}, ensure_ascii=False)


def set_reply(
    fake_claude_client: FakeClaudeClient, items: list[dict[str, Any]], stop_reason: str = "end_turn"
) -> None:
    fake_claude_client.messages.final_message = fake_message(reply_text(items), stop_reason)


def post_for_lines(client: TestClient, lyrics: str) -> list[dict[str, Any]]:
    """Posts the paste, expects 200, and returns the response's lines."""
    response = client.post(VERSIONS_PATH, json={"lyrics": lyrics})
    assert response.status_code == 200, response.text
    lines: list[dict[str, Any]] = response.json()["lines"]
    return lines


def sent_user_message(fake_claude_client: FakeClaudeClient) -> str:
    assert len(fake_claude_client.messages.calls) == 1
    content: str = fake_claude_client.messages.calls[0]["messages"][0]["content"]
    return content


@pytest.mark.usefixtures("with_api_key")
def test_ac2_valid_paste_returns_exactly_the_spec_example_response(
    client: TestClient, fake_claude_client: FakeClaudeClient
) -> None:
    """Field names, values, order, and no extra fields, as in the spec's output example."""
    set_reply(fake_claude_client, SPEC_ITEMS)

    response = client.post(VERSIONS_PATH, json={"lyrics": VALID_PASTE})

    assert response.status_code == 200
    assert response.json() == SPEC_RESPONSE
    assert len(fake_claude_client.messages.calls) == 1


@pytest.mark.usefixtures("with_api_key")
def test_ac2_indexes_run_from_0_with_no_gaps_and_originals_follow_the_cleaned_lines(
    client: TestClient, fake_claude_client: FakeClaudeClient
) -> None:
    """One entry per cleaned line, in order, each with all six fields and `readingVerified: true`.

    Spec 003 cleanup step 3.3: the leading spaces of `  星の夜に` are trimmed from its `original`.
    """
    lyrics = "\r\n\r\n  星の夜に  \r\n\r\n\r\n風が ふく\r\nLa la la\r\n\r\n月 ひかる\r\n\r\n"
    assert split_lines(lyrics)[0] == "  星の夜に"
    cleaned = ["星の夜に", "", "風が ふく", "La la la", "", "月 ひかる"]
    set_reply(
        fake_claude_client,
        [
            {"index": 0, "reading": "ほし の よる に", "english": "On a starry night"},
            {"index": 2, "reading": "かぜ が ふく", "english": "The wind blows"},
            {"index": 3, "reading": "La la la", "english": "La la la"},
            {"index": 5, "reading": "つき ひかる", "english": "The moon shines"},
        ],
    )

    lines = post_for_lines(client, lyrics)

    assert [line["index"] for line in lines] == list(range(len(cleaned)))
    assert [line["original"] for line in lines] == cleaned
    for line in lines:
        assert set(line) == LINE_FIELDS
        assert isinstance(line["index"], int)
        for field in ("original", "hiragana", "romaji", "english"):
            assert isinstance(line[field], str)
        assert line["readingVerified"] is True


@pytest.mark.usefixtures("with_api_key")
def test_ac3_blank_line_comes_back_in_place_with_empty_versions(
    client: TestClient, fake_claude_client: FakeClaudeClient
) -> None:
    """A verse break keeps its index, with all four texts empty and the reading verified."""
    set_reply(
        fake_claude_client,
        [
            {"index": 0, "reading": "そら が あおい", "english": "The sky is blue"},
            {"index": 2, "reading": "うみ も あおい", "english": "The sea is blue too"},
        ],
    )

    lines = post_for_lines(client, "空が青い\n\n海も青い")

    assert lines[1] == {
        "index": 1,
        "original": "",
        "hiragana": "",
        "romaji": "",
        "english": "",
        "readingVerified": True,
    }


@pytest.mark.usefixtures("with_api_key")
def test_ac3_blank_line_is_not_sent_to_claude(
    client: TestClient, fake_claude_client: FakeClaudeClient
) -> None:
    """Only the non-blank lines go to Claude, each labeled with its index in the paste."""
    set_reply(
        fake_claude_client,
        [
            {"index": 0, "reading": "そら が あおい", "english": "The sky is blue"},
            {"index": 2, "reading": "うみ も あおい", "english": "The sea is blue too"},
        ],
    )

    post_for_lines(client, "空が青い\n\n海も青い")

    assert sent_user_message(fake_claude_client) == build_user_message(
        [(0, "空が青い"), (2, "海も青い")]
    )


@pytest.mark.usefixtures("with_api_key")
def test_ac4_line_without_japanese_ignores_claudes_reading_and_english(
    client: TestClient, fake_claude_client: FakeClaudeClient
) -> None:
    """The server sets all three versions to the original, whatever Claude said for that line."""
    set_reply(
        fake_claude_client,
        [
            {"index": 0, "reading": "きみ の こえ が", "english": "Your voice"},
            {"index": 1, "reading": "うぃー しんぐ", "english": "Tonight we are singing"},
        ],
    )

    lines = post_for_lines(client, "君の声が\nWe sing tonight")

    assert lines[1] == {
        "index": 1,
        "original": "We sing tonight",
        "hiragana": "We sing tonight",
        "romaji": "We sing tonight",
        "english": "We sing tonight",
        "readingVerified": True,
    }


@pytest.mark.usefixtures("with_api_key")
def test_ac4_line_without_japanese_is_still_sent_to_claude_as_context(
    client: TestClient, fake_claude_client: FakeClaudeClient
) -> None:
    """The English line goes to Claude so the lines around it translate well."""
    set_reply(
        fake_claude_client,
        [
            {"index": 0, "reading": "きみ の こえ が", "english": "Your voice"},
            {"index": 1, "reading": "We sing tonight", "english": "We sing tonight"},
        ],
    )

    post_for_lines(client, "君の声が\nWe sing tonight")

    assert sent_user_message(fake_claude_client) == build_user_message(
        [(0, "君の声が"), (1, "We sing tonight")]
    )


@pytest.mark.usefixtures("with_api_key")
def test_ac4_reading_for_a_line_without_japanese_is_ignored_not_checked(
    client: TestClient, fake_claude_client: FakeClaudeClient
) -> None:
    """Rule 5 checks readings of Japanese lines only; an ignored value cannot fail the reply."""
    set_reply(
        fake_claude_client,
        [
            {"index": 0, "reading": "きみ の こえ が", "english": "Your voice"},
            {"index": 1, "reading": "漢字 ABC xyz", "english": ""},
        ],
    )

    lines = post_for_lines(client, "君の声が\nOh oh oh!")

    assert lines[1]["hiragana"] == "Oh oh oh!"
    assert lines[1]["english"] == "Oh oh oh!"
    assert lines[1]["readingVerified"] is True


@pytest.mark.usefixtures("with_api_key")
def test_ac18_reading_that_changes_kana_comes_back_unverified(
    client: TestClient, fake_claude_client: FakeClaudeClient
) -> None:
    """The spec example: `る` became `た`, so the line is flagged but still returned."""
    set_reply(
        fake_claude_client,
        [
            {"index": 0, "reading": "きみ が いた", "english": "You were there"},
            {"index": 1, "reading": "ほし が ひかる", "english": "The stars shine"},
            {"index": 3, "reading": "そら へ", "english": "To the sky"},
        ],
    )

    lines = post_for_lines(client, "君がいる\n星が光る\n\n空へ")

    assert lines[0]["hiragana"] == "きみ が いた"
    assert lines[0]["romaji"] == "kimi ga ita"
    assert lines[0]["readingVerified"] is False
    assert [line["readingVerified"] for line in lines[1:]] == [True, True, True]


@pytest.mark.usefixtures("with_api_key")
def test_ac18_reading_that_drops_a_digit_comes_back_unverified_with_romaji(
    client: TestClient, fake_claude_client: FakeClaudeClient
) -> None:
    """Spec example `2人で` read `ふたり で`: flagged, and romaji still comes from the reading."""
    set_reply(
        fake_claude_client, [{"index": 0, "reading": "ふたり で", "english": "The two of us"}]
    )

    lines = post_for_lines(client, "2人で")

    assert lines[0]["hiragana"] == "ふたり で"
    assert lines[0]["romaji"] == "futari de"
    assert lines[0]["readingVerified"] is False


@pytest.mark.usefixtures("with_api_key")
@pytest.mark.parametrize(
    "bad_reading",
    ["きみ が 居る", "kimi ga iru", "きみ\tが いる", "きみ　が いる"],
    ids=["kanji-not-in-line", "latin-not-in-line", "tab", "full-width-space"],
)
def test_ac18_reading_that_fails_the_hard_check_fails_the_whole_request(
    client: TestClient, fake_claude_client: FakeClaudeClient, bad_reading: str
) -> None:
    """Rule 5 is a hard check: one disallowed reading means 502 and no lines at all."""
    set_reply(
        fake_claude_client,
        [
            {"index": 0, "reading": "ほし が ひかる", "english": "The stars shine"},
            {"index": 1, "reading": bad_reading, "english": "You are here"},
        ],
    )

    response = client.post(VERSIONS_PATH, json={"lyrics": "星が光る\n君がいる"})

    assert response.status_code == 502
    assert_error_shape(response.json(), "model_output_invalid")
    assert len(fake_claude_client.messages.calls) == 1


@pytest.mark.usefixtures("with_api_key")
def test_ac18_reading_spaces_are_tidied_before_the_checks(
    client: TestClient, fake_claude_client: FakeClaudeClient
) -> None:
    """Leading, trailing, and repeated ASCII spaces collapse to single spaces between words."""
    set_reply(fake_claude_client, [{"index": 0, "reading": "  きみ  が   いる ", "english": "You"}])

    lines = post_for_lines(client, "君がいる")

    assert lines[0]["hiragana"] == "きみ が いる"
    assert lines[0]["romaji"] == "kimi ga iru"
    assert lines[0]["readingVerified"] is True


@pytest.mark.usefixtures("with_api_key")
def test_ac46_over_long_reading_fails_the_reply_before_any_kana_kept_check(
    client: TestClient, fake_claude_client: FakeClaudeClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Every reading passes the hard checks before the matcher runs on any line, valid or not."""
    kana_kept_calls: list[tuple[str, str]] = []

    def kana_kept_must_not_run(original: str, reading: str) -> bool:
        kana_kept_calls.append((original, reading))
        raise AssertionError("reading_keeps_kana ran before every reading was allowed")

    monkeypatch.setattr(readings, "reading_keeps_kana", kana_kept_must_not_run)
    monkeypatch.setattr(four_versions, "reading_keeps_kana", kana_kept_must_not_run, raising=False)
    set_reply(
        fake_claude_client,
        [
            {"index": 0, "reading": "ほし が ひかる", "english": "The stars shine"},
            # 7 characters for a 1-character line: over the 6x cap.
            {"index": 1, "reading": "そらそらそらそ", "english": "Sky"},
        ],
    )

    response = client.post(VERSIONS_PATH, json={"lyrics": "星が光る\n空"})

    assert response.status_code == 502
    assert_error_shape(response.json(), "model_output_invalid")
    assert kana_kept_calls == []


@pytest.mark.usefixtures("with_api_key")
def test_ac18_decomposed_kana_in_the_paste_behaves_like_composed_kana(
    client: TestClient, fake_claude_client: FakeClaudeClient
) -> None:
    """`か` + U+3099 in the paste is normalized to `が` before it is split, sent, or compared."""
    set_reply(fake_claude_client, [{"index": 0, "reading": "きみ が いる", "english": "You"}])

    lines = post_for_lines(client, "君がいる")

    assert lines[0]["original"] == "君がいる"
    assert lines[0]["readingVerified"] is True
    assert "゙" not in sent_user_message(fake_claude_client)
    assert "0: 君がいる" in sent_user_message(fake_claude_client)


@pytest.mark.usefixtures("with_api_key")
def test_ac18_decomposed_kana_in_the_reading_behaves_like_composed_kana(
    client: TestClient, fake_claude_client: FakeClaudeClient
) -> None:
    """`か` + U+3099 in Claude's reading becomes `が`, so it is verified and spelled `ga`."""
    set_reply(fake_claude_client, [{"index": 0, "reading": "きみ が いる", "english": "You"}])

    lines = post_for_lines(client, "君がいる")

    assert lines[0]["hiragana"] == "きみ が いる"
    assert lines[0]["romaji"] == "kimi ga iru"
    assert lines[0]["readingVerified"] is True


@pytest.mark.usefixtures("with_api_key")
def test_ac29_romaji_is_spelled_in_code_from_each_hiragana(
    client: TestClient, fake_claude_client: FakeClaudeClient
) -> None:
    """Romaji is `to_romaji(hiragana)` on every line, whatever romaji-like text Claude sends."""
    set_reply(
        fake_claude_client,
        [
            {"index": 0, "reading": "きみ は うみ へ", "english": "romaji: kimi ha umi he"},
            {"index": 1, "reading": "がっこう で まっちゃ", "english": "romaji: gakko de macha"},
            {"index": 2, "reading": "らーめん と さんぽ", "english": "romaji: ramen to sampo"},
            {"index": 3, "reading": "きみ が いた", "english": "romaji: kimi ga iru"},
        ],
    )

    lines = post_for_lines(client, "君は海へ\n学校で抹茶\nラーメンと散歩\n君がいる")

    assert [line["romaji"] for line in lines] == [
        "kimi wa umi e",
        "gakkou de matcha",
        "raamen to sanpo",
        "kimi ga ita",
    ]
    for line in lines:
        assert line["romaji"] == to_romaji(line["hiragana"])


# Errors after the call, end to end: one error shape, nothing from the reply or the SDK error.

REPLY_MARKER = "REPLY-MARKER-never-in-a-body-or-log"
SDK_SECRET = "/Users/someone/private sk-ant-not-a-real-key api.anthropic.com"
SENSITIVE_LYRICS = "君の声が\n遠く ひびく\n\nWe sing tonight"
SENSITIVE_LINES = ["君の声が", "遠く ひびく", "We sing tonight"]


def marked_items() -> list[dict[str, Any]]:
    """The spec reply, with the marker in every English line so a leak is easy to spot."""
    return [{**item, "english": f"{item['english']} {REPLY_MARKER}"} for item in SPEC_ITEMS]


def items_without_english() -> list[dict[str, Any]]:
    return [{"index": item["index"], "reading": item["reading"]} for item in marked_items()]


def items_with_field(index: int, field: str, value: str) -> list[dict[str, Any]]:
    items = marked_items()
    items[index][field] = value
    return items


def invalid_reply_messages() -> list[tuple[Message, str]]:
    """(reply, expected code) for every way a reply fails a hard check after the call."""
    return [
        (fake_message(reply_text(marked_items()), "refusal"), "model_refused"),
        (fake_message(reply_text(marked_items()), "max_tokens"), "model_output_truncated"),
        (fake_message(f"not json {REPLY_MARKER} 君の声が"), "model_output_invalid"),
        (fake_message(reply_text(items_without_english())), "model_output_invalid"),
        (fake_message(reply_text(marked_items()[:2])), "model_output_invalid"),
        (fake_message(reply_text(items_with_field(0, "english", ""))), "model_output_invalid"),
        (fake_message(reply_text(items_with_field(0, "reading", ""))), "model_output_invalid"),
        (
            fake_message(reply_text(items_with_field(0, "reading", f"きみ {REPLY_MARKER}"))),
            "model_output_invalid",
        ),
    ]


INVALID_REPLY_IDS = [
    "refusal",
    "max-tokens",
    "not-json",
    "missing-english",
    "missing-index",
    "empty-english",
    "empty-reading",
    "reading-not-allowed",
]


def sdk_errors() -> list[tuple[BaseException, ErrorPoint]]:
    request = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
    return [
        (anthropic.APIConnectionError(message=SDK_SECRET, request=request), "call"),
        (
            anthropic.APIStatusError(
                SDK_SECRET, response=httpx2.Response(529, request=request), body=None
            ),
            "enter",
        ),
        (httpx2.ReadTimeout(SDK_SECRET, request=request), "final"),
        (httpx2.DecodingError(SDK_SECRET, request=request), "final"),
    ]


SDK_ERROR_IDS = ["connection", "status-529", "raw-read-timeout", "raw-decoding-error"]


def assert_body_leaks_nothing(body_text: str) -> None:
    for leaked in (REPLY_MARKER, SDK_SECRET, "sk-ant", "/Users", FAKE_API_KEY, "Traceback"):
        assert leaked not in body_text
    for line in SENSITIVE_LINES:
        assert line not in body_text


@pytest.mark.usefixtures("with_api_key")
@pytest.mark.parametrize(
    ("reply", "expected_code"), invalid_reply_messages(), ids=INVALID_REPLY_IDS
)
def test_ac13_to_16_and_20_bad_reply_is_502_with_no_reply_text_in_the_body(
    client: TestClient, fake_claude_client: FakeClaudeClient, reply: Message, expected_code: str
) -> None:
    """Refused, truncated, and invalid replies: 502, the one error shape, and nothing leaked."""
    fake_claude_client.messages.final_message = reply

    response = client.post(VERSIONS_PATH, json={"lyrics": SENSITIVE_LYRICS})

    assert response.status_code == 502
    assert_error_shape(response.json(), expected_code)
    assert_body_leaks_nothing(response.text)
    assert len(fake_claude_client.messages.calls) == 1


@pytest.mark.usefixtures("with_api_key")
@pytest.mark.parametrize(("sdk_error", "error_point"), sdk_errors(), ids=SDK_ERROR_IDS)
def test_ac21_sdk_error_is_503_with_no_exception_text_in_the_body(
    client: TestClient,
    fake_claude_client: FakeClaudeClient,
    sdk_error: BaseException,
    error_point: ErrorPoint,
) -> None:
    """An SDK or mid-stream transport error: 503 model_unavailable, and nothing leaked."""
    fake_claude_client.messages.error = sdk_error
    fake_claude_client.messages.error_point = error_point

    response = client.post(VERSIONS_PATH, json={"lyrics": SENSITIVE_LYRICS})

    assert response.status_code == 503
    assert_error_shape(response.json(), "model_unavailable")
    assert_body_leaks_nothing(response.text)
    assert "api.anthropic.com" not in response.text
    assert len(fake_claude_client.messages.calls) == 1


def unexpected_error() -> RuntimeError:
    """An unexpected error whose message holds a path, the lyrics, and the key."""
    return RuntimeError(f"/Users/someone/lyrx/src/lyrx/claude.py {SENSITIVE_LYRICS} {FAKE_API_KEY}")


@pytest.mark.usefixtures("with_api_key")
def test_ac32_unexpected_error_from_the_claude_client_is_500_with_no_exception_text(
    client: TestClient, fake_claude_client: FakeClaudeClient
) -> None:
    """A RuntimeError raised by the client is internal_error, with only the error shape's keys."""
    fake_claude_client.messages.error = unexpected_error()

    response = client.post(VERSIONS_PATH, json={"lyrics": SENSITIVE_LYRICS})

    assert response.status_code == 500
    assert_error_shape(response.json(), "internal_error")
    assert_body_leaks_nothing(response.text)
    assert "RuntimeError" not in response.text
    assert len(fake_claude_client.messages.calls) == 1


# Logging (AC-33): one line per request, and nothing sensitive in any log record.

LYRX_LOGGER = "lyrx"
# The request line is written as `name=value` fields, e.g. `status=200 lines=4 ...`.
LOG_FIELD = re.compile(r"(\w+)=(\S+)")
PRIVATE_HEADER_VALUE = "header-value-never-logged"
PRIVATE_HEADERS = {"X-Private-Note": PRIVATE_HEADER_VALUE, "User-Agent": "agent-never-logged"}


def cleaned_characters(lyrics: str) -> int:
    """The logged character count: the cleaned lines joined by `\\n` (spec 003 AC-37).

    Only used for pastes that cleanup leaves as split, so the split lines are the cleaned lines.
    """
    return len("\n".join(split_lines(lyrics)))


def lyrx_records(caplog: pytest.LogCaptureFixture) -> list[logging.LogRecord]:
    return [
        record
        for record in caplog.records
        if record.name == LYRX_LOGGER or record.name.startswith(f"{LYRX_LOGGER}.")
    ]


def only_request_line(caplog: pytest.LogCaptureFixture) -> dict[str, str]:
    """The fields of the one lyrx log line this request wrote."""
    records = lyrx_records(caplog)
    assert len(records) == 1, [record.getMessage() for record in records]
    return dict(LOG_FIELD.findall(records[0].getMessage()))


def every_log_text(caplog: pytest.LogCaptureFixture) -> str:
    """Every captured record from every logger: message, traceback, arguments, and extras."""
    formatter = logging.Formatter()
    return "\n".join(formatter.format(record) + repr(record.__dict__) for record in caplog.records)


def sensitive_texts() -> list[str]:
    """What must never be logged, as written and JSON-escaped."""
    texts = [*SENSITIVE_LINES, REPLY_MARKER, FAKE_API_KEY, PRIVATE_HEADER_VALUE]
    texts += ["agent-never-logged", "Your voice", "echoes far away", "きみ の こえ が"]
    return texts + [json.dumps(text)[1:-1] for text in texts]


def assert_logs_leak_nothing(caplog: pytest.LogCaptureFixture) -> None:
    log_text = every_log_text(caplog)
    for text in sensitive_texts():
        assert text not in log_text
    assert "/Users/someone" not in log_text


@pytest.mark.usefixtures("with_api_key")
def test_ac33_successful_request_logs_one_line_with_counts_duration_and_tokens(
    client: TestClient, fake_claude_client: FakeClaudeClient, caplog: pytest.LogCaptureFixture
) -> None:
    """`status`, `lines`, `characters`, `duration_ms`, and Claude's token counts, in one line."""
    caplog.set_level(logging.DEBUG)
    set_reply(fake_claude_client, SPEC_ITEMS)

    post_for_lines(client, VALID_PASTE)

    fields = only_request_line(caplog)
    assert fields["status"] == "200"
    assert fields["lines"] == str(len(split_lines(VALID_PASTE)))
    assert fields["characters"] == str(cleaned_characters(VALID_PASTE))
    assert fields["duration_ms"].isdecimal()
    assert fields["input_tokens"] == "100"
    assert fields["output_tokens"] == "50"


def configure_failure(fake_claude_client: FakeClaudeClient, failure: str) -> tuple[str, int, str]:
    """Sets the fake up for one failure; returns (lyrics, expected status, expected code)."""
    if failure == "no-japanese":
        return "We sing tonight\nLa la la", 400, "no_japanese"
    if failure == "invalid-reply":
        fake_claude_client.messages.final_message = fake_message(f"not json {REPLY_MARKER}")
        return SENSITIVE_LYRICS, 502, "model_output_invalid"
    if failure == "missing-english":
        fake_claude_client.messages.final_message = fake_message(
            reply_text(items_without_english())
        )
        return SENSITIVE_LYRICS, 502, "model_output_invalid"
    if failure == "refusal":
        set_reply(fake_claude_client, marked_items(), stop_reason="refusal")
        return SENSITIVE_LYRICS, 502, "model_refused"
    if failure == "sdk-error":
        request = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
        message = f"{SDK_SECRET} {SENSITIVE_LYRICS} {FAKE_API_KEY}"
        fake_claude_client.messages.error = anthropic.APIConnectionError(
            message=message, request=request
        )
        return SENSITIVE_LYRICS, 503, "model_unavailable"
    if failure == "unexpected-error":
        fake_claude_client.messages.error = unexpected_error()
        return SENSITIVE_LYRICS, 500, "internal_error"
    raise AssertionError(f"unknown failure {failure}")


FAILURES = [
    "no-japanese",
    "invalid-reply",
    "missing-english",
    "refusal",
    "sdk-error",
    "unexpected-error",
]


@pytest.mark.usefixtures("with_api_key")
@pytest.mark.parametrize("failure", FAILURES)
def test_ac33_failed_request_logs_one_line_with_status_code_counts_and_duration(
    client: TestClient,
    fake_claude_client: FakeClaudeClient,
    caplog: pytest.LogCaptureFixture,
    failure: str,
) -> None:
    """Every failure, before or after the call, still writes its one line with its error code."""
    caplog.set_level(logging.DEBUG)
    lyrics, expected_status, expected_code = configure_failure(fake_claude_client, failure)

    response = client.post(VERSIONS_PATH, json={"lyrics": lyrics})

    assert response.status_code == expected_status
    fields = only_request_line(caplog)
    assert fields["status"] == str(expected_status)
    assert fields["code"] == expected_code
    assert fields["lines"] == str(len(split_lines(lyrics)))
    assert fields["characters"] == str(cleaned_characters(lyrics))
    assert fields["duration_ms"].isdecimal()


@pytest.mark.usefixtures("with_api_key")
@pytest.mark.parametrize("failure", ["success", *FAILURES])
def test_ac33_logs_never_hold_the_lyrics_the_reply_headers_or_the_key(
    client: TestClient,
    fake_claude_client: FakeClaudeClient,
    caplog: pytest.LogCaptureFixture,
    failure: str,
) -> None:
    """No record from any logger holds the lyrics, the reply, a header value, or the API key."""
    caplog.set_level(logging.DEBUG)
    if failure == "success":
        set_reply(fake_claude_client, marked_items())
        lyrics = SENSITIVE_LYRICS
    else:
        lyrics, _, _ = configure_failure(fake_claude_client, failure)

    response = client.post(VERSIONS_PATH, json={"lyrics": lyrics}, headers=PRIVATE_HEADERS)

    assert response.status_code < 600
    assert lyrx_records(caplog) != []
    assert_logs_leak_nothing(caplog)


@pytest.mark.usefixtures("with_api_key")
def test_ac33_a_500_under_uvicorn_logs_no_traceback_with_the_lyrics_or_the_key(
    app: FastAPI, fake_claude_client: FakeClaudeClient, caplog: pytest.LogCaptureFixture
) -> None:
    """uvicorn logs any exception that escapes the app; none may carry the lyrics or the key."""
    caplog.set_level(logging.DEBUG)
    fake_claude_client.messages.error = unexpected_error()
    body = json.dumps({"lyrics": SENSITIVE_LYRICS}, ensure_ascii=False).encode()
    headers = [
        ALLOWED_HOST_HEADER,
        JSON_CONTENT_TYPE_HEADER,
        (b"x-private-note", PRIVATE_HEADER_VALUE.encode()),
    ]

    sent = run_like_uvicorn(app, headers, body_messages([body]))

    assert response_status(sent) == 500
    assert_body_leaks_nothing(response_body(sent).decode())
    assert len(fake_claude_client.messages.calls) == 1
    assert only_request_line(caplog)["status"] == "500"
    assert_logs_leak_nothing(caplog)


@pytest.mark.parametrize(
    ("method", "path", "body", "headers", "expected_status"),
    [
        ("POST", VERSIONS_PATH, {"lyrics": "夜の月"}, {"Host": "evil.example"}, 403),
        ("GET", "/api/no-such-route", None, {}, 404),
        ("POST", VERSIONS_PATH, {"text": "夜の月"}, {}, 400),
    ],
    ids=["host-refused", "not-found", "invalid-request"],
)
def test_ac33_requests_that_never_reach_the_pipeline_write_no_lyrx_log_record(
    client: TestClient,
    caplog: pytest.LogCaptureFixture,
    method: str,
    path: str,
    body: dict[str, str] | None,
    headers: dict[str, str],
    expected_status: int,
) -> None:
    """Logging covers POST /api/versions only: a refused Host, a 404, and a bad body log nothing."""
    caplog.set_level(logging.DEBUG)

    response = client.request(method, path, json=body, headers=headers)

    assert response.status_code == expected_status
    assert lyrx_records(caplog) == []


# Cleaning up the lyrics (spec 003, AC-23 to AC-34 and AC-37), end to end.
# At T1 the paste route still calls Claude, so the fake Claude client stands in for the fake
# Gemini: "the fake Gemini receives lines X" is checked as the numbered lines Claude is sent.

FULL_WIDTH_SPACE = "\u3000"
FULL_WIDTH_OPEN = "\uff08"
FULL_WIDTH_CLOSE = "\uff09"
ZERO_WIDTH_SPACE = "\u200b"

# The AC-23 paste: three invented triples (Japanese, Hangul pronunciation, Korean translation),
# repeated 10 times, all 90 items joined by single spaces into one line.
AC23_TRIPLES = [
    ("君の声が聞こえる", "키미노 코에가 키코에루", "너의 목소리가 들려"),
    ("遠くまでひびく", "토오쿠마데 히비쿠", "멀리까지 울려"),
    ("星がながれる夜に", "호시가 나가레루 요루니", "별이 흐르는 밤에"),
]
AC23_PASTE = " ".join(item for _ in range(10) for triple in AC23_TRIPLES for item in triple)
AC23_LINES = [japanese for _ in range(10) for japanese, _, _ in AC23_TRIPLES]
AC32_KOREAN_PASTE = "君の声が\n키미노 코에가\n" + "か" * 201

# Readings for the kanji lines below; a kana-only or Latin line is its own reading.
KANJI_READINGS = {
    "君の声が聞こえる": "きみ の こえ が きこえる",
    "遠くまでひびく": "とおく まで ひびく",
    "星がながれる夜に": "ほし が ながれる よる に",
    "君の声が": "きみ の こえ が",
    "君の声": "きみ の こえ",
    "遠くひびく": "とおく ひびく",
    "遠く ひびく": "とおく ひびく",
    "星が ながれる": "ほし が ながれる",
    "星が  ながれる": "ほし が ながれる",
    "君の声が遠く": "きみ の こえ が とおく",
    f"君の声が{FULL_WIDTH_SPACE}遠く": "きみ の こえ が とおく",
    "Oh 君と": "Oh きみ と",
}


def numbered(lines: list[str]) -> list[tuple[int, str]]:
    """The non-blank lines with their indexes: what the readings call should receive."""
    return [(index, line) for index, line in enumerate(lines) if line]


def set_reply_for(fake_claude_client: FakeClaudeClient, lines: list[str]) -> None:
    """A valid reply for exactly these cleaned lines."""
    items = [
        {"index": index, "reading": KANJI_READINGS.get(line, line), "english": f"Line {index}"}
        for index, line in numbered(lines)
    ]
    set_reply(fake_claude_client, items)


def assert_cleaned_to(
    client: TestClient, fake_claude_client: FakeClaudeClient, lyrics: str, cleaned: list[str]
) -> list[dict[str, Any]]:
    """The paste returns 200 with one entry per cleaned line, and Claude gets those lines."""
    set_reply_for(fake_claude_client, cleaned)

    lines = post_for_lines(client, lyrics)

    assert [line["original"] for line in lines] == cleaned
    assert [line["index"] for line in lines] == list(range(len(cleaned)))
    assert sent_user_message(fake_claude_client) == build_user_message(numbered(cleaned))
    return lines


def has_hangul(text: str) -> bool:
    hangul_ranges = [
        (0x1100, 0x11FF),
        (0x3130, 0x318F),
        (0xA960, 0xA97F),
        (0xAC00, 0xD7AF),
        (0xD7B0, 0xD7FF),
        (0xFFA0, 0xFFDC),
    ]
    return any(
        first <= ord(character) <= last for character in text for first, last in hangul_ranges
    )


@pytest.mark.usefixtures("with_api_key")
def test_spec003_ac23_joined_paste_returns_the_thirty_japanese_lines(
    client: TestClient, fake_claude_client: FakeClaudeClient
) -> None:
    lines = assert_cleaned_to(client, fake_claude_client, AC23_PASTE, AC23_LINES)

    assert len(lines) == 30
    assert len(fake_claude_client.messages.calls) == 1
    assert not any(has_hangul(line["original"]) for line in lines)
    assert not has_hangul(sent_user_message(fake_claude_client))


@pytest.mark.usefixtures("with_api_key")
def test_spec003_ac24_normal_paste_is_sent_and_returned_unchanged(
    client: TestClient, fake_claude_client: FakeClaudeClient
) -> None:
    lyrics = "君の声が\n遠く ひびく\n\n星が  ながれる\nWe sing tonight"
    cleaned = ["君の声が", "遠く ひびく", "", "星が  ながれる", "We sing tonight"]
    assert split_lines(lyrics) == cleaned

    assert_cleaned_to(client, fake_claude_client, lyrics, cleaned)


@pytest.mark.usefixtures("with_api_key")
@pytest.mark.parametrize(
    ("lyrics", "expected"),
    [
        ("君の声が 너의 목소리가", "君の声が"),
        ("星が 별이 ながれる", "星が ながれる"),
        (f"君の声が{FULL_WIDTH_OPEN}키미노 코에가{FULL_WIDTH_CLOSE}", "君の声が"),
        ("君の声が【키미노】遠く", "君の声が遠く"),
        ("Oh 너의 君と", "Oh 君と"),
        (f"君{ZERO_WIDTH_SPACE}の声", "君の声"),
        (f"  君の声が{FULL_WIDTH_SPACE}", "君の声が"),
        (f"君の声が{FULL_WIDTH_SPACE}遠く", f"君の声が{FULL_WIDTH_SPACE}遠く"),
    ],
    ids=[
        "korean-after",
        "korean-between",
        "korean-in-brackets",
        "korean-in-lenticular-brackets",
        "korean-after-latin",
        "zero-width",
        "line-ends",
        "full-width-space-inside",
    ],
)
def test_spec003_ac25_ac26_each_line_comes_back_cleaned(
    client: TestClient, fake_claude_client: FakeClaudeClient, lyrics: str, expected: str
) -> None:
    assert_cleaned_to(client, fake_claude_client, lyrics, [expected])


@pytest.mark.usefixtures("with_api_key")
def test_spec003_ac27_blank_line_comes_back_with_all_four_fields_empty(
    client: TestClient, fake_claude_client: FakeClaudeClient
) -> None:
    lines = assert_cleaned_to(
        client, fake_claude_client, "君の声が\n\n遠くひびく", ["君の声が", "", "遠くひびく"]
    )

    assert lines[1] == {
        "index": 1,
        "original": "",
        "hiragana": "",
        "romaji": "",
        "english": "",
        "readingVerified": True,
    }


@pytest.mark.usefixtures("with_api_key")
@pytest.mark.parametrize(
    ("lyrics", "expected"),
    [
        (
            "君の声が\n키미노 코에가\n너의 목소리가\n\n遠くひびく",
            ["君の声が", "", "遠くひびく"],
        ),
        ("君の声が\n\n키미노\n\n遠くひびく", ["君の声が", "", "遠くひびく"]),
        ("키미노\n\n君の声が\n\n너의", ["君の声が"]),
    ],
    ids=["korean-lines-dropped", "blank-run-collapsed", "blank-ends-dropped"],
)
def test_spec003_ac27_korean_only_lines_are_dropped_and_blank_lines_tidied(
    client: TestClient, fake_claude_client: FakeClaudeClient, lyrics: str, expected: list[str]
) -> None:
    assert_cleaned_to(client, fake_claude_client, lyrics, expected)


@pytest.mark.usefixtures("with_api_key")
def test_spec003_ac28_line_of_200_characters_with_spaces_is_not_split(
    client: TestClient, fake_claude_client: FakeClaudeClient
) -> None:
    line = "ゆめ " * 66 + "ゆめ"
    assert len(line) == 200

    assert_cleaned_to(client, fake_claude_client, line, [line])


@pytest.mark.usefixtures("with_api_key")
def test_spec003_ac28_line_length_is_measured_after_removal(
    client: TestClient, fake_claude_client: FakeClaudeClient
) -> None:
    lyrics = "ゆめ " * 59 + "ゆめ" + " " + "꿈" * 100
    assert len(lyrics) == 280

    assert_cleaned_to(client, fake_claude_client, lyrics, ["ゆめ " * 59 + "ゆめ"])


@pytest.mark.usefixtures("with_api_key")
def test_spec003_ac29_long_line_is_split_at_whitespace(
    client: TestClient, fake_claude_client: FakeClaudeClient
) -> None:
    lyrics = "か" * 120 + FULL_WIDTH_SPACE + "き" * 120 + "  \t " + "く" * 10

    assert_cleaned_to(client, fake_claude_client, lyrics, ["か" * 120, "き" * 120, "く" * 10])


@pytest.mark.usefixtures("with_api_key")
def test_spec003_ac29_long_line_is_split_at_a_no_break_space(
    client: TestClient, fake_claude_client: FakeClaudeClient
) -> None:
    """User decision 2026-11-17: U+00A0 is a split point too."""
    lyrics = "か" * 120 + "\u00a0" + "き" * 120

    assert_cleaned_to(client, fake_claude_client, lyrics, ["か" * 120, "き" * 120])


@pytest.mark.usefixtures("with_api_key")
def test_spec003_ac29_long_latin_line_is_split_and_each_piece_comes_back_as_in_ac4(
    client: TestClient, fake_claude_client: FakeClaudeClient
) -> None:
    latin_line = ("la " * 80).rstrip()
    assert len(latin_line) == 239

    lines = assert_cleaned_to(
        client, fake_claude_client, "君の声が\n" + latin_line, ["君の声が"] + ["la"] * 80
    )

    assert len(lines) == 81
    for line in lines[1:]:
        assert (line["hiragana"], line["romaji"], line["english"]) == ("la", "la", "la")
        assert line["readingVerified"] is True


@pytest.mark.usefixtures("with_api_key")
def test_spec003_ac30_long_line_is_split_after_sentence_ending_marks(
    client: TestClient, fake_claude_client: FakeClaudeClient
) -> None:
    assert_cleaned_to(client, fake_claude_client, "かぜがふく。" * 50, ["かぜがふく。"] * 50)


@pytest.mark.usefixtures("with_api_key")
@pytest.mark.parametrize("marks", ["\uff01\uff1f", "!"], ids=["full-width-run", "ascii"])
def test_spec003_ac30_a_run_of_marks_splits_once_after_the_run(
    client: TestClient, fake_claude_client: FakeClaudeClient, marks: str
) -> None:
    lyrics = "あめ" * 60 + marks + "あめ" * 60

    assert_cleaned_to(client, fake_claude_client, lyrics, ["あめ" * 60 + marks, "あめ" * 60])


@pytest.mark.usefixtures("with_api_key")
def test_spec003_ac31_whitespace_first_then_marks_only_for_pieces_still_too_long(
    client: TestClient, fake_claude_client: FakeClaudeClient
) -> None:
    lyrics = "か" * 150 + "。" + "か" * 150 + " " + "そら。そら"
    expected = ["か" * 150 + "。", "か" * 150, "そら。そら"]

    assert_cleaned_to(client, fake_claude_client, lyrics, expected)


@pytest.mark.usefixtures("with_api_key")
@pytest.mark.parametrize(
    ("lyrics", "cleaned"),
    [
        ("ゆめ" * 150, ["ゆめ" * 150]),
        ("か" * 250 + " " + "そら", ["か" * 250, "そら"]),
        (AC32_KOREAN_PASTE, ["君の声が", "か" * 201]),
        (
            "\r\n\r\n星がながれる\r\n\r\n\r\n\r\n" + "か" * 201 + "   ",
            ["星がながれる", "", "か" * 201],
        ),
    ],
    ids=["no-split-point", "long-piece", "after-korean-line", "after-blank-lines"],
)
def test_spec003_ac32_line_still_over_200_after_both_splits_is_kept_not_refused(
    client: TestClient, fake_claude_client: FakeClaudeClient, lyrics: str, cleaned: list[str]
) -> None:
    assert_cleaned_to(client, fake_claude_client, lyrics, cleaned)


LIMIT_DETAIL_WORDS = ["input_too_large", "limitHit", "measured", "lineNumber"]


@pytest.mark.usefixtures("with_api_key")
@pytest.mark.parametrize(
    ("lyrics", "cleaned"),
    [
        ("\n".join(["うたう " + "노래" * 20] * 120), ["うたう"] * 120),
        ("\n".join(["うた", "노래"] * 201), ["うた"] * 201),
        (("うた " * 201).rstrip(), ["うた"] * 201),
        ("ゆめ" * 2501, ["ゆめ" * 2501]),
    ],
    ids=["5399-characters", "402-alternating-lines", "201-words", "5002-characters"],
)
def test_spec003_ac33_there_are_no_limits_on_characters_or_lines(
    client: TestClient, fake_claude_client: FakeClaudeClient, lyrics: str, cleaned: list[str]
) -> None:
    set_reply_for(fake_claude_client, cleaned)

    response = client.post(VERSIONS_PATH, json={"lyrics": lyrics})

    assert response.status_code == 200, response.text[:200]
    assert [line["original"] for line in response.json()["lines"]] == cleaned
    assert sent_user_message(fake_claude_client) == build_user_message(numbered(cleaned))
    for word in LIMIT_DETAIL_WORDS:
        assert word not in response.text


@pytest.mark.usefixtures("with_api_key")
@pytest.mark.parametrize(
    "lyrics",
    ["키미노 코에가\n너의 목소리가", "꿈" * 10000, ZERO_WIDTH_SPACE],
    ids=["korean-lines", "long-korean-line", "zero-width-only"],
)
def test_spec003_ac34_paste_that_cleans_to_no_japanese_is_no_japanese_and_claude_is_not_called(
    client: TestClient, fake_claude_client: FakeClaudeClient, lyrics: str
) -> None:
    status, body = post_lyrics(client, lyrics)

    assert status == 400
    assert_error_shape(body, "no_japanese")
    assert fake_claude_client.messages.calls == []


def assert_no_paste_text(text: str, lyrics: str) -> None:
    """No Hangul and no line of the paste as typed appears in `text`."""
    assert not has_hangul(text)
    assert not has_hangul(json.dumps(text))
    for line in split_lines(lyrics):
        if line:
            assert line not in text
            assert json.dumps(line)[1:-1] not in text


@pytest.mark.usefixtures("with_api_key")
def test_spec003_ac37_cleaned_paste_logs_cleaned_counts_and_no_paste_text(
    client: TestClient, fake_claude_client: FakeClaudeClient, caplog: pytest.LogCaptureFixture
) -> None:
    """For the AC-23 paste: `lines=30` and `characters=259`, and no pasted or cleaned text."""
    caplog.set_level(logging.DEBUG)
    set_reply_for(fake_claude_client, AC23_LINES)

    response = client.post(VERSIONS_PATH, json={"lyrics": AC23_PASTE})

    assert response.status_code == 200
    assert_no_paste_text(response.text, AC23_PASTE)
    fields = only_request_line(caplog)
    assert fields["lines"] == "30"
    assert fields["characters"] == "259"
    log_text = every_log_text(caplog)
    assert_no_paste_text(log_text, AC23_PASTE)
    for line in AC23_LINES:
        assert line not in log_text


@pytest.mark.usefixtures("with_api_key")
def test_spec003_ac37_long_line_paste_logs_cleaned_counts_and_no_paste_text(
    client: TestClient, fake_claude_client: FakeClaudeClient, caplog: pytest.LogCaptureFixture
) -> None:
    """For the AC-32 paste: 2 cleaned lines of 206 characters; no Hangul in the body or logs."""
    caplog.set_level(logging.DEBUG)
    set_reply_for(fake_claude_client, ["君の声が", "か" * 201])

    response = client.post(VERSIONS_PATH, json={"lyrics": AC32_KOREAN_PASTE})

    assert response.status_code == 200, response.text[:200]
    assert not has_hangul(response.text)
    fields = only_request_line(caplog)
    assert fields["status"] == "200"
    assert fields["lines"] == "2"
    assert fields["characters"] == "206"
    log_text = every_log_text(caplog)
    assert_no_paste_text(log_text, AC32_KOREAN_PASTE)
    for line in ["君の声が", "か" * 201]:
        assert line not in log_text
