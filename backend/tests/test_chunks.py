"""Tests for chunks.py: a song's lines split into chunks, one Gemini call each, in order."""

import pytest
from fake_gemini import FakeGemini, sent_indexes, status, success_for

from lyrx import config
from lyrx.chunks import request_in_chunks
from lyrx.errors import ApiError
from lyrx.schemas import GeminiVersions

API_KEY = "fake-gemini-key-not-real-0123"
# Ten invented Japanese lines; index 5 was blank, so it is left out.
INDEXES = [0, 1, 2, 3, 4, 6, 7, 8, 9, 10]
LINES = [(index, f"空の歌{index}") for index in INDEXES]


def english_for(indexes: list[int]) -> dict[int, str]:
    return {index: f"English {index}" for index in indexes}


def english_of(result: GeminiVersions) -> dict[int, str]:
    return {index: line.english for index, line in result.lines.items()}


def chunks_sent(fake: FakeGemini) -> list[list[int]]:
    return [sent_indexes(request) for request in fake.requests]


def script_chunks(fake: FakeGemini, chunks: list[list[int]]) -> None:
    for chunk in chunks:
        reply = success_for(chunk)
        fake.script(reply)


def translate(fake: FakeGemini, lines: list[tuple[int, str]] = LINES) -> GeminiVersions:
    return request_in_chunks(lines, API_KEY, fake.make_transport())


def test_default_chunk_sizes() -> None:
    assert config.GEMINI_CHUNK_LINES == 100
    assert config.GEMINI_CHUNK_CHARACTERS == 4000


def test_chunks_keep_order_and_indexes_across_a_gap(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "GEMINI_CHUNK_LINES", 4)
    fake = FakeGemini()
    expected = [[0, 1, 2, 3], [4, 6, 7, 8], [9, 10]]
    script_chunks(fake, expected)

    result = translate(fake)

    assert chunks_sent(fake) == expected
    assert english_of(result) == english_for(INDEXES)


def test_a_song_at_the_chunk_size_makes_one_call(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "GEMINI_CHUNK_LINES", len(LINES))
    fake = FakeGemini()
    script_chunks(fake, [INDEXES])

    result = translate(fake)

    assert chunks_sent(fake) == [INDEXES]
    assert english_of(result) == english_for(INDEXES)


def test_a_song_under_the_chunk_size_makes_one_call() -> None:
    fake = FakeGemini()
    script_chunks(fake, [INDEXES])

    translate(fake)

    assert len(fake.requests) == 1


def test_a_line_longer_than_the_character_size_goes_in_a_chunk_alone(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(config, "GEMINI_CHUNK_CHARACTERS", 10)
    lines = [(0, "短い"), (1, "とても長い長い長い長い長い歌詞の行"), (2, "短い"), (3, "短い")]
    fake = FakeGemini()
    script_chunks(fake, [[0], [1], [2, 3]])

    result = translate(fake, lines)

    assert chunks_sent(fake) == [[0], [1], [2, 3]]
    assert english_of(result) == english_for([0, 1, 2, 3])


def test_chunks_are_packed_as_full_as_the_character_size_allows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Texts joined by "\n": three 3-character lines take 3 + 1 + 3 + 1 + 3 = 11 characters.
    monkeypatch.setattr(config, "GEMINI_CHUNK_CHARACTERS", 11)
    lines = [(index, "あいう") for index in range(7)]
    fake = FakeGemini()
    script_chunks(fake, [[0, 1, 2], [3, 4, 5], [6]])

    translate(fake, lines)

    assert chunks_sent(fake) == [[0, 1, 2], [3, 4, 5], [6]]


def test_chunks_are_packed_as_full_as_the_line_size_allows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(config, "GEMINI_CHUNK_LINES", 3)
    fake = FakeGemini()
    script_chunks(fake, [[0, 1, 2], [3, 4, 6], [7, 8, 9], [10]])

    translate(fake)

    assert chunks_sent(fake) == [[0, 1, 2], [3, 4, 6], [7, 8, 9], [10]]


def test_token_usage_is_summed_over_the_chunks(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "GEMINI_CHUNK_LINES", 4)
    fake = FakeGemini()
    script_chunks(fake, [[0, 1, 2, 3], [4, 6, 7, 8], [9, 10]])

    result = translate(fake)

    assert result.usage.input_tokens == 360
    assert result.usage.output_tokens == 135
    assert result.calls == 3


def test_a_failing_chunk_stops_the_song_and_returns_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(config, "GEMINI_CHUNK_LINES", 4)
    fake = FakeGemini()
    fake.script(success_for([0, 1, 2, 3]), status(429))

    with pytest.raises(ApiError) as caught:
        translate(fake)

    assert caught.value.code == "translation_rate_limited"
    assert len(fake.requests) == 2
