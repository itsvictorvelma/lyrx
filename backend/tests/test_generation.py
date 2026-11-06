import json
import re

import pytest

from app.contracts import DraftLine, LyricDraft
from app.errors import DomainError
from app.generation.prompts import completion_body, completion_limit, segment_body, user_message
from app.generation.service import CHUNK, GenerationService
from app.lyrics import draft_from_model


def sample_payload() -> dict[str, object]:
    return {
        "title": "Ame",
        "artist": "Example",
        "lines": [
            {
                "originalText": "雨",
                "readingHiragana": "あめ",
                "pronunciationRomaji": "ame",
                "translationEnglish": "rain",
            }
        ],
    }


def test_completion_body_stays_inside_the_token_minute() -> None:
    body = completion_body("openai/gpt-oss-120b", "Akuma no Ko", None)

    assert body["model"] == "openai/gpt-oss-120b"
    assert body["temperature"] == 0.6
    assert body["reasoning_effort"] == "low"
    assert body["include_reasoning"] is False
    assert "Authorization" not in body
    prompt = body["messages"][0]["content"]
    assert isinstance(prompt, str)
    assert body["max_completion_tokens"] + 800 + len(prompt) // 4 <= 8000


def test_a_long_revision_is_refused_before_a_call() -> None:
    draft = LyricDraft.model_validate(sample_payload())
    draft.lines = draft.lines * 400

    with pytest.raises(DomainError) as error:
        completion_limit(user_message("add detail", draft))

    assert error.value.code == "generation_too_large"


def test_model_json_becomes_a_draft() -> None:
    draft = draft_from_model(sample_payload())

    assert draft.sourceLanguage == "ja"
    assert draft.lines[0].readingHiragana == "あめ"


def test_timing_in_model_json_is_rejected() -> None:
    payload = sample_payload()
    lines = payload["lines"]
    assert isinstance(lines, list)
    lines[0]["startSeconds"] = 1

    with pytest.raises(DomainError) as error:
        draft_from_model(payload)

    assert error.value.code == "generation_invalid"


class FakeGroq:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload
        self.calls = 0

    def complete(self, body: dict[str, object]) -> dict[str, object]:
        self.calls += 1
        self.body = body
        return self.payload


def numbered_lines(content: str) -> list[str]:
    lines: list[str] = []
    started = False
    for raw in content.splitlines():
        if raw == "Lines:":
            started = True
            continue
        if not started:
            continue
        matched = re.match(r"\d+\. (.*)", raw)
        if matched:
            lines.append(matched.group(1))
    return lines


def lyric_payload(marked_lines: list[str], reading: str = "あめ", english: str = "rain") -> dict[str, object]:
    lines: list[dict[str, object]] = []
    for marked in marked_lines:
        readings: list[str] = []
        for slot in re.findall(r"【([^】]*)】", marked):
            kana = "".join(char for char in slot if "\u3040" <= char <= "\u30ff" or char == "ー")
            readings.append(f"{reading}{kana}")
        lines.append({"readings": readings, "translationEnglish": english})
    return {
        "status_code": 200,
        "data": {"choices": [{"message": {"content": json.dumps({"lines": lines}, ensure_ascii=False)}}]},
    }


class PromptGroq:
    def __init__(self, reading: str = "あめ", english: str = "rain") -> None:
        self.reading = reading
        self.english = english
        self.prompts: list[str] = []

    def complete(self, body: dict[str, object]) -> dict[str, object]:
        messages = body["messages"]
        assert isinstance(messages, list)
        content = messages[0]["content"]
        assert isinstance(content, str)
        self.prompts.append(content)
        return lyric_payload(numbered_lines(content), self.reading, self.english)


def test_fetched_lines_are_all_filled(monkeypatch: pytest.MonkeyPatch) -> None:
    def search(title: str, artist: str) -> str:
        assert (title, artist) == ("Ame", "Example")
        return "雨\n[Chorus]\n空"

    monkeypatch.setattr("app.generation.service.search_plain", search)
    client = PromptGroq()

    result = GenerationService(client, "openai/gpt-oss-120b").generate("Ame by Example", None)

    assert [line.originalText for line in result.draft.lines] == ["雨", "空"]
    assert result.draft.lines[0].pronunciationRomaji == "ame"
    assert "よみ" not in client.prompts[0]
    assert result.message == "Ame, 2 lines"


def test_one_completion_returns_the_draft() -> None:
    client = FakeGroq(
        {
            "status_code": 200,
            "data": {"choices": [{"message": {"content": json.dumps(sample_payload())}}]},
        }
    )

    result = GenerationService(client, "openai/gpt-oss-120b").generate("Ame", None)

    assert client.calls == 1
    assert result.message == "Ame, 1 line"
    assert result.draft.lines[0].translationEnglish == "rain"


def test_rate_limit_does_not_parse_a_draft() -> None:
    client = FakeGroq({"status_code": 429, "data": {"error": {"code": "rate_limit_exceeded"}}})

    with pytest.raises(DomainError) as error:
        GenerationService(client, "openai/gpt-oss-120b").generate("Ame", None)

    assert error.value.code == "groq_rate_limited"
    assert client.calls == 1


def test_romaji_is_spelled_from_the_kana() -> None:
    payload = sample_payload()
    line = payload["lines"]
    assert isinstance(line, list)
    line[0]["originalText"] = "したたる"
    line[0]["readingHiragana"] = "かんじ"
    line[0]["pronunciationRomaji"] = "shitatru"
    client = FakeGroq({"status_code": 200, "data": {"choices": [{"message": {"content": json.dumps(payload)}}]}})

    result = GenerationService(client, "openai/gpt-oss-120b").generate("rain", None)

    assert result.draft.lines[0].readingHiragana == "したたる"
    assert result.draft.lines[0].pronunciationRomaji == "shitataru"


def test_a_reading_that_drops_kana_is_rejected() -> None:
    payload = sample_payload()
    line = payload["lines"]
    assert isinstance(line, list)
    line[0]["originalText"] = "雨が"
    line[0]["readingHiragana"] = "あめ"
    client = FakeGroq({"status_code": 200, "data": {"choices": [{"message": {"content": json.dumps(payload)}}]}})

    with pytest.raises(DomainError) as error:
        GenerationService(client, "openai/gpt-oss-120b").generate("rain", None)

    assert error.value.code == "generation_invalid"
    assert client.calls == 1


def test_a_named_fix_does_not_resend_the_other_lines() -> None:
    song = LyricDraft(
        title="Ame",
        artist="Example",
        lines=[
            DraftLine(originalText="雨が降る", readingHiragana="あめ が ふる", pronunciationRomaji="old", translationEnglish="rain falls"),
            DraftLine(originalText="空を見た", readingHiragana="そら を みた", pronunciationRomaji="old", translationEnglish="saw the sky"),
            DraftLine(originalText="雨が降る", readingHiragana="あめ が ふる", pronunciationRomaji="old", translationEnglish="rain falls"),
        ],
    )
    client = PromptGroq(reading="あめ", english="rain is falling")

    result = GenerationService(client, "openai/gpt-oss-120b").generate("fix 雨が降る", song)

    assert len(client.prompts) == 1
    assert numbered_lines(client.prompts[0]) == ["【雨】が【降る】"]
    assert "空を見た" not in client.prompts[0]
    assert "saw the sky" not in client.prompts[0]
    assert result.draft.lines[1].translationEnglish == "saw the sky"
    assert "が" in result.draft.lines[0].readingHiragana
    assert result.draft.lines[0].translationEnglish == "rain is falling"
    assert result.draft.lines[2].readingHiragana == result.draft.lines[0].readingHiragana


def test_a_line_number_sends_that_line_only() -> None:
    song = LyricDraft(
        title="Ame",
        artist="Example",
        lines=[
            DraftLine(originalText="alpha", readingHiragana="alpha", pronunciationRomaji="alpha", translationEnglish="first line"),
            DraftLine(originalText="beta", readingHiragana="beta", pronunciationRomaji="beta", translationEnglish="second line"),
            DraftLine(originalText="gamma", readingHiragana="gamma", pronunciationRomaji="gamma", translationEnglish="third line"),
        ],
    )
    client = PromptGroq()

    result = GenerationService(client, "openai/gpt-oss-120b").generate("fix line 2", song)

    assert numbered_lines(client.prompts[0]) == ["beta"]
    assert result.draft.lines[0].translationEnglish == "first line"
    assert result.draft.lines[1].originalText == "beta"
    assert result.draft.lines[2].translationEnglish == "third line"


def test_a_missing_line_number_does_not_call_groq() -> None:
    song = LyricDraft.model_validate(sample_payload())
    client = PromptGroq()

    with pytest.raises(DomainError) as error:
        GenerationService(client, "openai/gpt-oss-120b").generate("line 9", song)

    assert error.value.code == "generation_invalid"
    assert client.prompts == []


def test_a_long_revision_is_sent_in_groups() -> None:
    song = LyricDraft(
        title="Ame",
        artist="Example",
        lines=[
            DraftLine(
                originalText=f"雨{number:02d}",
                readingHiragana="あ",
                pronunciationRomaji="a",
                translationEnglish=f"line {number}",
            )
            for number in range(CHUNK + 1)
        ],
    )
    client = PromptGroq()

    result = GenerationService(client, "openai/gpt-oss-120b").generate("more literal", song)

    assert len(client.prompts) == 2
    assert len(numbered_lines(client.prompts[0])) == CHUNK
    assert numbered_lines(client.prompts[1]) == [f"【雨】{CHUNK:02d}"]
    assert "雨00" not in client.prompts[1]
    assert len(result.draft.lines) == CHUNK + 1


def test_a_repeated_line_is_translated_once(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.generation.service.search_plain", lambda title, artist: "雨\n雨")
    client = PromptGroq(english="rain")

    result = GenerationService(client, "openai/gpt-oss-120b").generate("Ame by Example", None)

    assert numbered_lines(client.prompts[0]) == ["【雨】"]
    assert [line.translationEnglish for line in result.draft.lines] == ["rain", "rain"]


def test_a_bad_chunk_retries_without_asking_for_the_next(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.generation.service.search_plain",
        lambda title, artist: "\n".join(f"雨{number:02d}" for number in range(CHUNK + 1)),
    )

    class Empty:
        def __init__(self) -> None:
            self.calls = 0

        def complete(self, body: dict[str, object]) -> dict[str, object]:
            self.calls += 1
            return lyric_payload([])

    client = Empty()
    with pytest.raises(DomainError):
        GenerationService(client, "openai/gpt-oss-120b").generate("Ame by Example", None)

    assert client.calls == 2


def test_dropped_kana_retries_that_chunk(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.generation.service.search_plain", lambda title, artist: "雨が")

    class Flaky:
        def __init__(self) -> None:
            self.calls = 0

        def complete(self, body: dict[str, object]) -> dict[str, object]:
            self.calls += 1
            messages = body["messages"]
            assert isinstance(messages, list)
            content = messages[0]["content"]
            assert isinstance(content, str)
            if self.calls == 1:
                return lyric_payload([], "あめ", "rain falls")
            return lyric_payload(numbered_lines(content), "あめ", "rain falls")

    client = Flaky()
    result = GenerationService(client, "openai/gpt-oss-120b").generate("Ame by Example", None)

    assert client.calls == 2
    assert result.draft.lines[0].readingHiragana == "あめ が"


def test_segment_omits_the_placeholder_and_stays_in_budget() -> None:
    current = [
        DraftLine(originalText="雨", readingHiragana="よみ", pronunciationRomaji="yomi", translationEnglish="rain")
    ]

    body = segment_body("openai/gpt-oss-120b", "fill", "Ame", "Example", ["雨"], None, current)
    prompt = body["messages"][0]["content"]

    assert isinstance(prompt, str)
    assert "よみ" not in prompt
    assert "rain" in prompt
    assert body["temperature"] == 0.6
    assert body["max_completion_tokens"] + 800 + len(prompt) // 4 <= 8000
