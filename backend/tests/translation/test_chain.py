"""Tests for chain.py: which translators are ready, and walking down the chain (spec 010)."""

import logging

import httpx2
import pytest
from conftest import SHIPPED_TRANSLATORS
from fake_clock import trickled, use_clock
from fake_gemini import FakeGemini, answer_with_placeholders, status, success
from fake_groq import (
    FakeGroq,
    groq_answer_with_placeholders,
    groq_reply,
    groq_status,
    groq_success,
)
from fake_lrclib import FakeLrclib, json_reply, record
from fastapi.testclient import TestClient

from lyrx import config
from lyrx.app import SONG_VERSIONS_PATH
from lyrx.errors import ApiError
from lyrx.translation.chain import ReadyTranslator, ready_translators, request_versions
from lyrx.translation.gemini import make_gemini_client
from lyrx.translation.groq import make_groq_client
from lyrx.translation.results import ChunkReply

GROQ_KEY = "fake-groq-key-not-real-4567"
GEMINI_KEY = "fake-gemini-key-not-real-0123"
# Invented lines.
LINES = [(0, "君の声が"), (1, "空へ飛ぶ")]
VERSIONS = {
    0: ("きみ の こえ が", "kimi no koe ga", "Your voice"),
    1: ("そら へ とぶ", "sora e tobu", "Flying to the sky"),
}
FULL_CHAIN = (
    config.Translator("groq-a", "groq", "groq-model-a"),
    config.Translator("gemini-a", "gemini", "gemini-model-a"),
    config.Translator("gemini-b", "gemini", "gemini-model-b"),
)
ScriptedReply = httpx2.Response | httpx2.RequestError


def chain(groq: FakeGroq, gemini: FakeGemini) -> list[ReadyTranslator]:
    """Every translator in the configured chain, talking to the fakes."""
    clients = {
        "groq": make_groq_client(groq.make_transport()),
        "gemini": make_gemini_client(gemini.make_transport()),
    }
    keys = {"groq": GROQ_KEY, "gemini": GEMINI_KEY}
    return [
        ReadyTranslator(t.name, t.service, t.model, keys[t.service], clients[t.service])
        for t in config.TRANSLATORS
    ]


def ask(
    groq_replies: list[ScriptedReply], gemini_replies: list[ScriptedReply]
) -> tuple[FakeGroq, FakeGemini, ChunkReply | ApiError]:
    groq, gemini = FakeGroq(), FakeGemini()
    groq.script(*groq_replies)
    gemini.script(*gemini_replies)
    try:
        return groq, gemini, request_versions(LINES, LINES, chain(groq, gemini))
    except ApiError as error:
        return groq, gemini, error


# --- Which translators are ready (AC-6) -------------------------------------------------------


def names(translators: list[ReadyTranslator]) -> list[str]:
    return [translator.name for translator in translators]


CLIENTS = {"groq": httpx2.Client(), "gemini": httpx2.Client()}


@pytest.mark.usefixtures("groq_key", "gemini_key")
def test_ac6_with_both_keys_groq_comes_first() -> None:
    assert names(ready_translators(CLIENTS)) == ["groq-gpt-oss-120b", "gemini-3.5-flash-lite"]


@pytest.mark.usefixtures("groq_key")
def test_ac6_with_only_the_groq_key_only_groq_is_used() -> None:
    assert names(ready_translators(CLIENTS)) == ["groq-gpt-oss-120b"]


@pytest.mark.usefixtures("gemini_key")
def test_ac6_with_only_the_gemini_key_only_gemini_is_used() -> None:
    assert names(ready_translators(CLIENTS)) == ["gemini-3.5-flash-lite"]


@pytest.mark.parametrize("value", [None, "", "   "])
def test_ac6_with_no_key_the_server_is_not_configured(
    monkeypatch: pytest.MonkeyPatch, value: str | None
) -> None:
    if value is not None:
        monkeypatch.setenv(config.GROQ_API_KEY_ENV_VAR, value)

    with pytest.raises(ApiError) as caught:
        ready_translators(CLIENTS)

    assert caught.value.code == "server_not_configured"


@pytest.mark.usefixtures("groq_key")
def test_a_ready_translator_never_shows_its_key() -> None:
    assert GROQ_KEY not in repr(ready_translators(CLIENTS))


# --- Walking down the chain (AC-2, AC-3, AC-7) ------------------------------------------------


@pytest.mark.parametrize(
    "busy",
    [
        groq_status(429),
        groq_status(413, error_code="rate_limit_exceeded"),
        groq_status(503),
        httpx2.ConnectError("x"),
        httpx2.ReadTimeout("x"),
    ],
    ids=["429", "413-over-minute-limit", "503", "connect", "timeout"],
)
def test_ac2_a_busy_groq_hands_the_request_to_gemini(busy: ScriptedReply) -> None:
    groq, gemini, result = ask([busy], [success(VERSIONS)])

    assert isinstance(result, ChunkReply)
    assert result.translator == "gemini-3.5-flash-lite"
    assert (len(groq.requests), len(gemini.requests)) == (1, 1)


def test_spec019_ac5_a_groq_reply_past_the_deadline_hands_the_request_to_gemini(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Groq starts at 0 s and its second piece arrives at 50 s, past the 45 s deadline.
    use_clock(monkeypatch, 0.0, 10.0, 50.0)

    groq, gemini, result = ask([trickled(groq_success(VERSIONS))], [success(VERSIONS)])

    assert isinstance(result, ChunkReply)
    assert result.translator == "gemini-3.5-flash-lite"
    assert (len(groq.requests), len(gemini.requests)) == (1, 1)


@pytest.mark.parametrize(
    "refused",
    [groq_status(400), groq_reply("{}", finish_reason="content_filter"), groq_reply("not json")],
    ids=["refused-400", "blocked", "unusable"],
)
def test_ac3_a_refused_blocked_or_unusable_reply_does_not_move_on(refused: ScriptedReply) -> None:
    _, gemini, result = ask([refused], [])

    assert isinstance(result, ApiError)
    assert gemini.requests == []


@pytest.mark.parametrize(
    ("groq_busy", "gemini_busy", "code"),
    [
        (groq_status(503), status(429), "translation_rate_limited"),
        (groq_status(429), status(503), "translation_unavailable"),
    ],
)
def test_ac7_when_every_translator_is_busy_the_last_error_counts(
    groq_busy: ScriptedReply, gemini_busy: ScriptedReply, code: str
) -> None:
    _, _, result = ask([groq_busy], [gemini_busy])

    assert isinstance(result, ApiError)
    assert result.code == code


def test_the_full_chain_is_tried_in_order(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "TRANSLATORS", FULL_CHAIN)

    groq, gemini, result = ask([groq_status(503)], [status(503), success(VERSIONS)])

    assert isinstance(result, ChunkReply)
    assert result.translator == "gemini-b"
    assert [request.url.rsplit("/", 1)[-1] for request in gemini.requests] == [
        "gemini-model-a:generateContent",
        "gemini-model-b:generateContent",
    ]
    assert groq.requests[0].body["model"] == "groq-model-a"


def test_the_shipped_chain_is_groq_then_two_gemini_flash_lite_models() -> None:
    shipped = [
        ("groq-gpt-oss-120b", "groq", "openai/gpt-oss-120b"),
        ("gemini-3.5-flash-lite", "gemini", "gemini-3.5-flash-lite"),
        ("gemini-3.1-flash-lite", "gemini", "gemini-3.1-flash-lite"),
    ]
    assert [tuple(translator) for translator in SHIPPED_TRANSLATORS] == shipped


# --- Through the route (AC-6, AC-8) -----------------------------------------------------------


@pytest.mark.usefixtures("groq_key")
def test_ac6_a_song_opens_with_only_the_groq_key(
    client: TestClient, fake_lrclib: FakeLrclib, fake_groq: FakeGroq, fake_gemini: FakeGemini
) -> None:
    fake_lrclib.script(json_reply(record()))
    fake_groq.answer = groq_answer_with_placeholders

    response = client.post(SONG_VERSIONS_PATH, json={"id": 101})

    assert response.status_code == 200
    assert fake_gemini.requests == []


@pytest.mark.usefixtures("groq_key", "gemini_key")
def test_ac8_the_log_names_the_translator_and_never_the_key_or_reply(
    client: TestClient,
    fake_lrclib: FakeLrclib,
    fake_groq: FakeGroq,
    fake_gemini: FakeGemini,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO)
    fake_lrclib.script(json_reply(record()), json_reply(record(record_id=202)))
    fake_groq.answer = groq_answer_with_placeholders
    client.post(SONG_VERSIONS_PATH, json={"id": 101})
    fake_groq.answer = None
    fake_groq.script(groq_status(503))
    fake_gemini.answer = answer_with_placeholders
    client.post(SONG_VERSIONS_PATH, json={"id": 202})

    lines = [r.getMessage() for r in caplog.records if r.name == "lyrx.server.request_log"]
    assert "translator=groq-gpt-oss-120b " in lines[0]
    assert "translator=gemini-3.5-flash-lite " in lines[1]
    assert GROQ_KEY not in caplog.text
    assert GEMINI_KEY not in caplog.text
    assert "English 0" not in caplog.text
