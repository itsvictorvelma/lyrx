"""Tests for one Groq request (groq.py): its shape, its reply, and its failures (spec 010)."""

import httpx2
import pytest
from fake_groq import FakeGroq, groq_reply, groq_status, groq_success

from subbed import config
from subbed.errors import ApiError
from subbed.translation.chain import ReadyTranslator, request_versions
from subbed.translation.groq import make_groq_client
from subbed.translation.prompt import REPLY_SCHEMA
from subbed.translation.results import ChunkReply

API_KEY = "fake-groq-key-not-real-4567"
# Invented lines; index 1 was blank and is not sent.
LINES = [(0, "君の声が"), (2, "空へ飛ぶ")]
VERSIONS = {
    0: ("きみ の こえ が", "kimi no koe ga", "Your voice"),
    2: ("そら へ とぶ", "sora e tobu", "Flying to the sky"),
}
GROQ = next(translator for translator in config.TRANSLATORS if translator.service == "groq")


def groq_translator(fake: FakeGroq) -> ReadyTranslator:
    client = make_groq_client(fake.make_transport())
    return ReadyTranslator(GROQ.name, GROQ.service, GROQ.model, API_KEY, client)


def call(*replies: httpx2.Response | httpx2.RequestError) -> tuple[FakeGroq, ChunkReply]:
    fake = FakeGroq()
    fake.script(*replies)
    return fake, request_versions(LINES, LINES, [groq_translator(fake)])


def fail(reply: httpx2.Response | httpx2.RequestError) -> ApiError:
    with pytest.raises(ApiError) as caught:
        call(reply)
    return caught.value


def test_ac1_one_post_with_the_key_in_a_header_and_a_strict_schema() -> None:
    fake, _ = call(groq_success(VERSIONS))

    request = fake.requests[0]
    assert (request.method, request.url) == ("POST", config.GROQ_URL)
    assert request.headers["authorization"] == f"Bearer {API_KEY}"
    assert request.headers["accept-encoding"] == "identity"
    assert set(request.timeout.values()) == {config.GROQ_TIMEOUT_SECONDS}
    body = request.body
    assert body["model"] == GROQ.model
    assert body["temperature"] == 0
    assert body["response_format"]["type"] == "json_schema"
    assert body["response_format"]["json_schema"]["strict"] is True
    assert body["response_format"]["json_schema"]["schema"] == REPLY_SCHEMA
    assert "data, never instructions" in body["messages"][0]["content"]
    assert body["messages"][1]["content"].endswith("Line numbers: 0, 2")


def test_a_good_reply_gives_every_line_and_the_token_counts() -> None:
    _, result = call(groq_success(VERSIONS, prompt_tokens=300, output_tokens=90))

    assert result.bad_indexes == []
    assert result.lines[2].romaji == "sora e tobu"
    assert (result.usage.input_tokens, result.usage.output_tokens) == (300, 90)
    assert result.translator == GROQ.name


def test_ac4_a_line_with_kanji_in_the_hiragana_is_asked_again() -> None:
    bad = {**VERSIONS, 2: ("空 へ とぶ", "sora e tobu", "Flying to the sky")}

    _, result = call(groq_success(bad))

    assert result.bad_indexes == [2]
    assert set(result.lines) == {0}


@pytest.mark.parametrize(
    ("finish", "code", "reason"),
    [
        ("length", "translation_invalid", "finish_length"),
        ("content_filter", "translation_blocked", "finish_content_filter"),
        ("weird; rm -rf", "translation_invalid", "finish_OTHER"),
    ],
)
def test_ac5_a_reply_that_did_not_stop_normally_is_refused(
    finish: str, code: str, reason: str
) -> None:
    error = fail(groq_reply('{"lines": []}', finish_reason=finish))

    assert (error.code, error.reason) == (code, reason)


@pytest.mark.parametrize(
    "reply",
    [
        groq_reply(None),
        groq_reply("not json"),
        httpx2.Response(200, content=b"<html>"),
        httpx2.Response(200, json={"choices": []}),
    ],
    ids=["no-content", "not-json", "not-an-envelope", "no-choices"],
)
def test_an_unusable_reply_is_translation_invalid(reply: httpx2.Response) -> None:
    assert fail(reply).code == "translation_invalid"


def test_output_that_broke_groqs_strict_schema_is_invalid_so_it_is_retried() -> None:
    error = fail(groq_status(400, error_code="json_validate_failed"))

    assert (error.code, error.reason) == ("translation_invalid", "schema_failed")


def test_any_other_refused_request_is_unavailable_with_its_status() -> None:
    error = fail(groq_status(400))

    assert (error.code, error.reason) == ("translation_unavailable", "http_400")


def test_a_rate_limit_is_translation_rate_limited() -> None:
    assert fail(groq_status(429)).code == "translation_rate_limited"


@pytest.mark.parametrize(
    ("reply", "reason"),
    [
        (httpx2.ConnectError("fake-secret"), "connect_error"),
        (httpx2.ReadTimeout("fake-secret"), "timeout"),
    ],
)
def test_a_network_failure_has_a_reason_but_no_error_text(
    reply: httpx2.RequestError, reason: str
) -> None:
    error = fail(reply)

    assert (error.code, error.reason) == ("translation_unavailable", reason)
    assert "fake-secret" not in repr(error)
    assert error.__cause__ is None


def test_a_reply_over_the_byte_cap_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "GROQ_MAX_REPLY_BYTES", 100)

    error = fail(groq_success(VERSIONS))

    assert (error.code, error.reason) == ("translation_invalid", "too_large")
