"""Tests for lyrx.translation: the lines split into chunks, one Gemini call each (AC-53, AC-54)."""

import re

import pytest
from fake_gemini import FakeGemini, status, success

from lyrx import config
from lyrx.gemini import TranslationFailed
from lyrx.schemas import GeminiTranslation
from lyrx.translation import translate_lines

API_KEY = "fake-gemini-key-not-real-0123"
# Ten invented Japanese lines; index 5 was blank in the paste, so it is left out.
INDEXES = [0, 1, 2, 3, 4, 6, 7, 8, 9, 10]
LINES = [(index, f"空の歌{index}") for index in INDEXES]


def english_for(indexes: list[int]) -> dict[int, str]:
    return {index: f"English {index}" for index in indexes}


def sent_indexes(fake: FakeGemini) -> list[list[int]]:
    """The line indexes each request carried, read from its user message."""
    sent = []
    for request in fake.requests:
        text = request.body["contents"][0]["parts"][0]["text"]
        sent.append([int(found) for found in re.findall(r"^\[(\d+)\] ", text, re.MULTILINE)])
    return sent


def script_chunks(fake: FakeGemini, chunks: list[list[int]]) -> None:
    for chunk in chunks:
        fake.script(success(english_for(chunk), prompt_tokens=100, output_tokens=10))


def translate(fake: FakeGemini, lines: list[tuple[int, str]] = LINES) -> GeminiTranslation:
    return translate_lines(lines, API_KEY, fake.make_transport())


def test_ac53_default_chunk_sizes() -> None:
    assert config.GEMINI_CHUNK_LINES == 200
    assert config.GEMINI_CHUNK_CHARACTERS == 8000


def test_ac53_chunks_keep_order_and_indexes_across_a_gap(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "GEMINI_CHUNK_LINES", 4)
    fake = FakeGemini()
    expected = [[0, 1, 2, 3], [4, 6, 7, 8], [9, 10]]
    script_chunks(fake, expected)

    result = translate(fake)

    assert sent_indexes(fake) == expected
    assert result.english == english_for(INDEXES)


def test_ac53_a_song_at_the_chunk_size_makes_one_call(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "GEMINI_CHUNK_LINES", len(LINES))
    fake = FakeGemini()
    script_chunks(fake, [INDEXES])

    result = translate(fake)

    assert sent_indexes(fake) == [INDEXES]
    assert result.english == english_for(INDEXES)


def test_ac53_a_song_under_the_chunk_size_makes_one_call() -> None:
    fake = FakeGemini()
    script_chunks(fake, [INDEXES])

    translate(fake)

    assert len(fake.requests) == 1


def test_ac53_a_line_longer_than_the_character_size_goes_in_a_chunk_alone(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(config, "GEMINI_CHUNK_CHARACTERS", 10)
    lines = [(0, "短い"), (1, "とても長い長い長い長い長い歌詞の行"), (2, "短い"), (3, "短い")]
    fake = FakeGemini()
    script_chunks(fake, [[0], [1], [2, 3]])

    result = translate(fake, lines)

    assert sent_indexes(fake) == [[0], [1], [2, 3]]
    assert result.english == english_for([0, 1, 2, 3])


def test_ac53_chunks_are_packed_as_full_as_the_character_size_allows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Texts joined by "\n": three 3-character lines take 3 + 1 + 3 + 1 + 3 = 11 characters.
    monkeypatch.setattr(config, "GEMINI_CHUNK_CHARACTERS", 11)
    lines = [(index, "あいう") for index in range(7)]
    fake = FakeGemini()
    script_chunks(fake, [[0, 1, 2], [3, 4, 5], [6]])

    translate(fake, lines)

    assert sent_indexes(fake) == [[0, 1, 2], [3, 4, 5], [6]]


def test_ac53_chunks_are_packed_as_full_as_the_line_size_allows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(config, "GEMINI_CHUNK_LINES", 3)
    fake = FakeGemini()
    script_chunks(fake, [[0, 1, 2], [3, 4, 6], [7, 8, 9], [10]])

    translate(fake)

    assert sent_indexes(fake) == [[0, 1, 2], [3, 4, 6], [7, 8, 9], [10]]


def test_ac53_token_usage_is_summed_over_the_chunks(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "GEMINI_CHUNK_LINES", 4)
    fake = FakeGemini()
    script_chunks(fake, [[0, 1, 2, 3], [4, 6, 7, 8], [9, 10]])

    result = translate(fake)

    assert result.usage.input_tokens == 300
    assert result.usage.output_tokens == 30


def test_ac54_a_failing_chunk_stops_the_song_and_returns_no_english(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(config, "GEMINI_CHUNK_LINES", 4)
    fake = FakeGemini()
    fake.script(success(english_for([0, 1, 2, 3])), status(429))

    with pytest.raises(TranslationFailed) as caught:
        translate(fake)

    assert caught.value.code == "translation_rate_limited"
    assert len(fake.requests) == 2
