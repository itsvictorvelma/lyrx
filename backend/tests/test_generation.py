import json

import pytest

from app.contracts import LyricDraft
from app.errors import DomainError
from app.generation import completion_body, completion_limit, user_message
from app.lyrics import draft_from_model
from app.services.generation import GenerationService


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


def test_fetched_lines_keep_local_readings(monkeypatch: pytest.MonkeyPatch) -> None:
    def search(title: str, artist: str) -> str:
        assert (title, artist) == ("Ame", "Example")
        return "雨\n[Chorus]\n空\nIt doesn't matter if it's Sunday"

    monkeypatch.setattr("app.services.generation.search_plain", search)

    class Echo:
        def complete(self, body: dict[str, object]) -> dict[str, object]:
            assert body["temperature"] == 0
            schema = body["response_format"]
            assert isinstance(schema, dict)
            assert schema["json_schema"]["name"] == "line_meanings"
            return {
                "status_code": 200,
                "data": {
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(
                                    {"meanings": ["rain", "sky", "It doesn't matter if it's Sunday"]}
                                )
                            }
                        }
                    ]
                },
            }

    result = GenerationService(Echo(), "openai/gpt-oss-120b").generate("Ame by Example", None)

    assert [line.originalText for line in result.draft.lines] == ["雨", "空", "It doesn't matter if it's Sunday"]
    assert [(line.readingHiragana, line.pronunciationRomaji) for line in result.draft.lines] == [
        ("あめ", "ame"),
        ("そら", "sora"),
        ("It doesn't matter if it's Sunday", "It doesn't matter if it's Sunday"),
    ]
    assert result.draft.lines[0].translationEnglish == "rain"
    assert result.message == "Ame, 3 lines"


def test_a_repeated_original_keeps_the_first_meaning(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.services.generation.search_plain", lambda title, artist: "雨\n雨")

    class Echo:
        def complete(self, body: dict[str, object]) -> dict[str, object]:
            return {
                "status_code": 200,
                "data": {"choices": [{"message": {"content": json.dumps({"meanings": ["rain", "precipitation"]})}}]},
            }

    result = GenerationService(Echo(), "openai/gpt-oss-120b").generate("Ame by Example", None)

    assert [line.translationEnglish for line in result.draft.lines] == ["rain", "rain"]


def test_a_short_meaning_list_is_sent_again(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.services.generation.search_plain", lambda title, artist: "雨\n空")

    class Flaky:
        def __init__(self) -> None:
            self.calls = 0

        def complete(self, body: dict[str, object]) -> dict[str, object]:
            self.calls += 1
            meanings = ["rain"] if self.calls == 1 else ["rain", "sky"]
            return {"status_code": 200, "data": {"choices": [{"message": {"content": json.dumps({"meanings": meanings})}}]}}

    client = Flaky()
    result = GenerationService(client, "openai/gpt-oss-120b").generate("Ame by Example", None)

    assert client.calls == 2
    assert [line.translationEnglish for line in result.draft.lines] == ["rain", "sky"]


def test_a_rate_limit_while_translating_is_not_retried(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.services.generation.search_plain", lambda title, artist: "雨")
    client = FakeGroq({"status_code": 429, "data": {"error": {"code": "rate_limit_exceeded"}}})

    with pytest.raises(DomainError) as error:
        GenerationService(client, "openai/gpt-oss-120b").generate("Ame by Example", None)

    assert error.value.code == "groq_rate_limited"
    assert client.calls == 1


def test_one_completion_returns_the_draft() -> None:
    payload = sample_payload()
    payload["lines"][0]["pronunciationRomaji"] = "xxx"
    client = FakeGroq(
        {
            "status_code": 200,
            "data": {"choices": [{"message": {"content": json.dumps(payload)}}]},
        }
    )

    result = GenerationService(client, "openai/gpt-oss-120b").generate("Ame", None)

    assert client.calls == 1
    assert result.message == "Ame, 1 line"
    assert result.draft.lines[0].translationEnglish == "rain"
    assert result.draft.lines[0].readingHiragana == "あめ"
    assert result.draft.lines[0].pronunciationRomaji == "ame"


def test_rate_limit_does_not_parse_a_draft() -> None:
    client = FakeGroq({"status_code": 429, "data": {"error": {"code": "rate_limit_exceeded"}}})

    with pytest.raises(DomainError) as error:
        GenerationService(client, "openai/gpt-oss-120b").generate("Ame", None)

    assert error.value.code == "groq_rate_limited"
    assert client.calls == 1
