"""Tests for chunks.py: chunks sent at the same time, asking bad lines again, and retries."""

import contextlib
import threading
import time
from collections.abc import Callable

import pytest
from fake_gemini import (
    FakeGemini,
    ScriptedReply,
    SeenGeminiRequest,
    answer_with_placeholders,
    context_indexes,
    placeholder_versions,
    sent_indexes,
    status,
    success,
    success_for,
)

from lyrx import config
from lyrx.errors import ApiError, ErrorCode
from lyrx.translation.chain import ReadyTranslator
from lyrx.translation.chunks import MISSING, request_in_chunks, with_retries
from lyrx.translation.gemini import make_gemini_client
from lyrx.translation.results import SongTranslation

API_KEY = "fake-gemini-key-not-real-0123"
# Ten invented Japanese lines; index 5 was blank, so it is left out.
INDEXES = [0, 1, 2, 3, 4, 6, 7, 8, 9, 10]
LINES = [(index, f"空の歌{index}") for index in INDEXES]


def run(fake: FakeGemini, lines: list[tuple[int, str]] = LINES) -> SongTranslation:
    gemini = next(t for t in config.TRANSLATORS if t.service == "gemini")
    client = make_gemini_client(fake.make_transport())
    translator = ReadyTranslator(gemini.name, gemini.service, gemini.model, API_KEY, client)
    return request_in_chunks(lines, [translator])


def chunks_sent(fake: FakeGemini) -> list[list[int]]:
    return sorted(sent_indexes(request) for request in fake.requests)


def test_chunks_run_at_the_same_time_but_never_more_than_the_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(config, "CHUNK_LINES", 1)
    limit = config.PARALLEL_REQUESTS
    # Each of the first `limit` requests waits until all of them are in flight together.
    barrier = threading.Barrier(limit, timeout=5)
    in_flight = 0
    most_in_flight = 0
    counter_lock = threading.Lock()

    def answer(request: SeenGeminiRequest) -> ScriptedReply:
        nonlocal in_flight, most_in_flight
        with counter_lock:
            in_flight += 1
            most_in_flight = max(most_in_flight, in_flight)
        try:
            if sent_indexes(request)[0] < INDEXES[limit]:
                barrier.wait()
            return answer_with_placeholders(request)
        finally:
            with counter_lock:
                in_flight -= 1

    fake = FakeGemini(answer=answer)
    # The fake's own lock would serialize the answers, so answer outside it.
    fake.lock = contextlib.nullcontext()  # type: ignore[assignment]

    run(fake)

    assert most_in_flight == limit


def test_a_failing_chunk_stops_the_song_and_unsent_chunks_are_never_sent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(config, "CHUNK_LINES", 2)
    monkeypatch.setattr(config, "PARALLEL_REQUESTS", 1)
    fake = FakeGemini()
    fake.script(status(429))

    with pytest.raises(ApiError) as caught:
        run(fake)

    assert caught.value.code == "translation_rate_limited"
    assert len(fake.requests) == 1


def test_chunks_cover_every_line_once_and_each_carries_the_whole_song(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(config, "CHUNK_LINES", 4)
    fake = FakeGemini(answer=answer_with_placeholders)

    result = run(fake)

    assert chunks_sent(fake) == [[0, 1, 2, 3], [4, 6, 7, 8], [9, 10]]
    assert all(context_indexes(request) == INDEXES for request in fake.requests)
    assert {index: line.english for index, line in result.lines.items()} == {
        index: f"English {index}" for index in INDEXES
    }
    assert result.calls == 3
    assert result.usage.input_tokens == 360


def test_a_very_long_song_sends_each_chunk_without_the_whole_song(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(config, "CHUNK_LINES", 5)
    monkeypatch.setattr(config, "CONTEXT_MAX_CHARACTERS", 10)
    fake = FakeGemini(answer=answer_with_placeholders)

    run(fake)

    assert all(context_indexes(r) == sent_indexes(r) for r in fake.requests)


def test_a_line_longer_than_the_character_size_goes_in_a_chunk_alone(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(config, "CHUNK_CHARACTERS", 10)
    lines = [(0, "短い"), (1, "とても長い長い長い長い長い歌詞の行"), (2, "短い"), (3, "短い")]
    fake = FakeGemini(answer=answer_with_placeholders)

    run(fake, lines)

    assert chunks_sent(fake) == [[0], [1], [2, 3]]


def test_an_overloaded_request_is_retried_and_then_works() -> None:
    fake = FakeGemini()
    fake.script(status(503), status(503), success_for(INDEXES))

    result = run(fake)

    assert len(fake.requests) == 3
    assert result.retries == 2
    assert result.missing_lines == 0


def test_after_all_retries_the_song_fails_with_the_last_error() -> None:
    fake = FakeGemini()
    fake.script(status(503), status(503), status(503))

    with pytest.raises(ApiError) as caught:
        run(fake)

    assert caught.value.code == "translation_unavailable"
    assert len(fake.requests) == 1 + len(config.RETRY_WAIT_SECONDS)


@pytest.mark.parametrize(
    ("code", "expected"), [(429, "translation_rate_limited"), (400, "translation_unavailable")]
)
def test_a_rate_limit_or_a_refused_request_is_never_retried(code: int, expected: str) -> None:
    fake = FakeGemini()
    fake.script(status(code))

    with pytest.raises(ApiError) as caught:
        run(fake)

    assert caught.value.code == expected
    assert len(fake.requests) == 1


def test_bad_lines_are_asked_again_on_their_own() -> None:
    first = {index: placeholder_versions(index) for index in INDEXES}
    first[2] = ("空", "sora", "Sky")  # kanji in the hiragana
    fake = FakeGemini()
    fake.script(success(first), success({2: ("そら", "sora", "Sky")}))

    result = run(fake)

    assert [sent_indexes(request) for request in fake.requests] == [INDEXES, [2]]
    assert result.lines[2].hiragana == "そら"
    assert result.missing_lines == 0


def test_a_line_still_bad_after_asking_again_is_shown_without_versions() -> None:
    first = {index: placeholder_versions(index) for index in INDEXES if index != 2}

    def answer(request: SeenGeminiRequest) -> ScriptedReply:
        return success({}) if sent_indexes(request) == [2] else success(first)

    result = run(FakeGemini(answer=answer))

    assert result.lines[2] == MISSING
    assert result.missing_lines == 1
    assert result.lines[3].english == "English 3"


def test_a_typical_song_takes_two_calls_with_the_default_sizes() -> None:
    """Fewer, larger chunks spend less of the free tier's request limits (spec 009)."""
    song = [(index, f"君の声が遠くまで{index}") for index in range(60)]
    fake = FakeGemini(answer=answer_with_placeholders)

    run(fake, song)

    assert len(fake.requests) == 2


# --- Retries --------------------------------------------------------------------------------


def failing_then(errors: list[ApiError]) -> Callable[[], str]:
    """A request that raises the given errors in turn, then returns "done"."""
    remaining = list(errors)

    def request() -> str:
        if remaining:
            raise remaining.pop(0)
        return "done"

    return request


@pytest.fixture
def waits(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    """The configured waits restored, and every sleep recorded instead of slept."""
    monkeypatch.setattr(config, "RETRY_WAIT_SECONDS", (1.0, 3.0))
    slept: list[float] = []
    monkeypatch.setattr(time, "sleep", slept.append)
    return slept


@pytest.mark.parametrize(
    ("code", "reason"),
    [
        ("translation_unavailable", "timeout"),
        ("translation_unavailable", "connect_error"),
        ("translation_unavailable", "http_500"),
        ("translation_invalid", "bad_json"),
        ("translation_invalid", "finish_MAX_TOKENS"),
    ],
)
def test_a_temporary_failure_is_retried_after_the_configured_waits(
    waits: list[float], code: ErrorCode, reason: str
) -> None:
    error = ApiError(code, reason=reason)

    result, retries = with_retries(failing_then([error, error]))

    assert (result, retries) == ("done", 2)
    assert waits == [1.0, 3.0]


def test_after_the_last_retry_the_error_propagates(waits: list[float]) -> None:
    errors = [ApiError("translation_unavailable", reason="http_503") for _ in range(3)]

    with pytest.raises(ApiError):
        with_retries(failing_then(errors))

    assert waits == [1.0, 3.0]


@pytest.mark.parametrize(
    ("code", "reason"),
    [
        ("translation_rate_limited", "http_429"),
        ("translation_unavailable", "http_400"),
        ("translation_blocked", "finish_RECITATION"),
    ],
)
def test_a_lasting_failure_is_never_retried(
    waits: list[float], code: ErrorCode, reason: str
) -> None:
    with pytest.raises(ApiError) as caught:
        with_retries(failing_then([ApiError(code, reason=reason)]))

    assert caught.value.code == code
    assert waits == []


def test_success_first_time_takes_no_retry(waits: list[float]) -> None:
    assert with_retries(failing_then([])) == ("done", 0)
    assert waits == []
