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


def test_fetched_lines_are_all_filled(monkeypatch: pytest.MonkeyPatch) -> None:
    def search(title: str, artist: str) -> str:
        assert (title, artist) == ("Ame", "Example")
        return "雨\n[Chorus]\n空"

    monkeypatch.setattr("app.services.generation.search_plain", search)

    class Echo:
        def complete(self, body: dict[str, object]) -> dict[str, object]:
            messages = body["messages"]
            assert isinstance(messages, list)
            content = messages[0]["content"]
            assert isinstance(content, str)
            payload = json.loads(content.split("Current song: ", 1)[1])
            for line in payload["lines"]:
                line["readingHiragana"] = "あめ"
                line["pronunciationRomaji"] = "ame"
                line["translationEnglish"] = "rain"
            return {"status_code": 200, "data": {"choices": [{"message": {"content": json.dumps(payload)}}]}}

    result = GenerationService(Echo(), "openai/gpt-oss-120b").generate("Ame by Example", None)

    assert [line.originalText for line in result.draft.lines] == ["雨", "空"]
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
