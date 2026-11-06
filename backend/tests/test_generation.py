import json
import re

import pytest

from app.contracts import DraftLine, LyricDraft
from app.errors import DomainError
from app.generation.lrclib import Recording
from app.generation.prompts import completion_limit, prompt_tokens, segment_body, segment_message
from app.generation.service import GenerationService, song_name
from app.lyrics import draft_from_model
from tests.lyric_fixture import AME, search_ame


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


def test_one_completion_stays_inside_the_token_minute() -> None:
    body = segment_body("openai/gpt-oss-120b", "Ame", "Example", ["雨", "空"])

    assert body["model"] == "openai/gpt-oss-120b"
    assert body["temperature"] == 0.6
    assert body["reasoning_effort"] == "low"
    assert body["include_reasoning"] is False
    assert "Authorization" not in body
    assert body["messages"][0]["role"] == "user"
    prompt = body["messages"][0]["content"]
    assert isinstance(prompt, str)
    messages = body["messages"]
    assert messages == [{"role": "user", "content": prompt}]
    assert "Current song" not in prompt
    assert "よみ" not in prompt
    assert "【雨】" in prompt
    schema = body["response_format"]
    assert isinstance(schema, dict)
    assert schema["json_schema"]["name"] == "lyric_slots"
    assert "pronunciationRomaji" not in json.dumps(schema)
    room = 8_000 - prompt_tokens(prompt)
    assert body["max_completion_tokens"] == room
    assert room > 6_000


def test_a_song_that_cannot_fit_does_not_call_groq() -> None:
    prompt = segment_message("Ame", "Example", ["雨" * 200] * 200)

    with pytest.raises(DomainError) as error:
        completion_limit(prompt)

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


def test_a_name_without_by_is_only_a_title() -> None:
    assert song_name("  Ame  ") == ("Ame", "")
    assert song_name("Ame by Example") == ("Ame", "Example")


class FakeGroq:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload
        self.calls = 0
        self.body: dict[str, object] | None = None

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
        lines.append({"readings": readings, "translationEnglish": english, "pronunciationRomaji": "from-the-model"})
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
        assert len(messages) == 1
        content = messages[0]["content"]
        assert isinstance(content, str)
        self.prompts.append(content)
        return lyric_payload(numbered_lines(content), self.reading, self.english)


def test_fetched_lines_are_the_originals_and_romaji_is_spelled() -> None:
    client = PromptGroq()

    result = GenerationService(client, "openai/gpt-oss-120b", search_ame).generate("Ame by Example", None)

    assert client.prompts and len(client.prompts) == 1
    assert [line.originalText for line in result.draft.lines] == ["雨", "空"]
    assert result.draft.title == "Ame"
    assert result.draft.artist == "Example"
    assert result.draft.lines[0].readingHiragana == "あめ"
    assert result.draft.lines[0].pronunciationRomaji == "ame"
    assert result.draft.lines[0].pronunciationRomaji != "from-the-model"
    assert "よみ" not in client.prompts[0]
    assert "from-the-model" not in client.prompts[0]
    assert result.message == "Ame, 2 lines"


def test_one_completion_returns_the_draft() -> None:
    seen: dict[str, str] = {}

    def search(title: str, artist: str) -> Recording | None:
        seen["title"] = title
        seen["artist"] = artist
        return AME

    client = PromptGroq()
    result = GenerationService(client, "openai/gpt-oss-120b", search).generate("ame", None)

    assert seen == {"title": "ame", "artist": ""}
    assert result.draft.title == "Ame"
    assert len(client.prompts) == 1
    assert result.message == "Ame, 2 lines"
    assert result.draft.lines[0].translationEnglish == "rain"


def test_a_miss_does_not_call_groq() -> None:
    client = PromptGroq()

    with pytest.raises(DomainError) as error:
        GenerationService(client, "openai/gpt-oss-120b", lambda _title, _artist: None).generate("Nope", None)

    assert error.value.code == "generation_invalid"
    assert client.prompts == []


def test_a_song_over_the_token_minute_does_not_call_groq() -> None:
    client = PromptGroq()
    text = "\n".join(["雨" * 200] * 200)

    def search(_title: str, _artist: str) -> Recording:
        return Recording(title="Ame", artist="Example", text=text)

    with pytest.raises(DomainError) as error:
        GenerationService(client, "openai/gpt-oss-120b", search).generate("Ame", None)

    assert error.value.code == "generation_too_large"
    assert client.prompts == []


def test_rate_limit_does_not_parse_a_draft() -> None:
    client = FakeGroq({"status_code": 429, "data": {"error": {"code": "rate_limit_exceeded"}}})

    with pytest.raises(DomainError) as error:
        GenerationService(client, "openai/gpt-oss-120b", search_ame).generate("Ame", None)

    assert error.value.code == "groq_rate_limited"
    assert client.calls == 1


def test_kana_is_copied_and_a_dropped_kana_is_not_retried() -> None:
    client = PromptGroq(reading="あめ", english="rain falls")

    def search(_title: str, _artist: str) -> Recording:
        return Recording(title="Ame", artist="Example", text="雨が")

    result = GenerationService(client, "openai/gpt-oss-120b", search).generate("Ame by Example", None)

    assert len(client.prompts) == 1
    assert numbered_lines(client.prompts[0]) == ["【雨】が"]
    assert result.draft.lines[0].readingHiragana == "あめ が"
    assert result.draft.lines[0].pronunciationRomaji == "ame ga"

    class Empty:
        def __init__(self) -> None:
            self.calls = 0

        def complete(self, body: dict[str, object]) -> dict[str, object]:
            self.calls += 1
            return lyric_payload([])

    empty = Empty()
    with pytest.raises(DomainError) as error:
        GenerationService(empty, "openai/gpt-oss-120b", search).generate("Ame by Example", None)

    assert error.value.code == "generation_invalid"
    assert empty.calls == 1


def test_romaji_for_a_kana_line_is_not_taken_from_the_model() -> None:
    def search(_title: str, _artist: str) -> Recording:
        return Recording(title="Ame", artist="Example", text="したたる")

    result = GenerationService(PromptGroq(), "openai/gpt-oss-120b", search).generate("Ame", None)

    assert result.draft.lines[0].readingHiragana == "したたる"
    assert result.draft.lines[0].pronunciationRomaji == "shitataru"


def test_many_lines_are_one_completion() -> None:
    lines = [f"雨{number:02d}" for number in range(13)]

    def search(_title: str, _artist: str) -> Recording:
        return Recording(title="Ame", artist="Example", text="\n".join(lines))

    client = PromptGroq()
    result = GenerationService(client, "openai/gpt-oss-120b", search).generate("Ame by Example", None)

    assert len(client.prompts) == 1
    assert len(numbered_lines(client.prompts[0])) == 13
    assert len(result.draft.lines) == 13


def test_a_repeated_line_stays_in_order() -> None:
    def search(_title: str, _artist: str) -> Recording:
        return Recording(title="Ame", artist="Example", text="雨\n雨")

    client = PromptGroq(english="rain")
    result = GenerationService(client, "openai/gpt-oss-120b", search).generate("Ame by Example", None)

    assert len(client.prompts) == 1
    assert numbered_lines(client.prompts[0]) == ["【雨】", "【雨】"]
    assert [line.translationEnglish for line in result.draft.lines] == ["rain", "rain"]


def _ame_lines(readings: list[object]) -> str:
    return json.dumps(
        {
            "lines": [
                {"readings": reading, "translationEnglish": english}
                for reading, english in zip(readings, ("rain", "sky"), strict=True)
            ]
        },
        ensure_ascii=False,
    )


def test_json_validate_failed_keeps_the_generated_lines() -> None:
    """Groq returns 400 json_validate_failed when the JSON does not finish.

    The lines are in failed_generation. That text is this completion, so it
    becomes the draft. Nothing is asked again.
    """

    client = FakeGroq(
        {
            "status_code": 400,
            "data": {
                "error": {
                    "code": "json_validate_failed",
                    "failed_generation": _ame_lines([["あめ"], ["そら"]]),
                }
            },
        }
    )

    result = GenerationService(client, "openai/gpt-oss-120b", search_ame).generate("Ame", None)

    assert client.calls == 1
    assert [line.readingHiragana for line in result.draft.lines] == ["あめ", "そら"]
    assert [line.pronunciationRomaji for line in result.draft.lines] == ["ame", "sora"]
    assert result.draft.lines[0].translationEnglish == "rain"


def test_a_readings_string_is_not_thrown_away() -> None:
    client = FakeGroq(
        {
            "status_code": 200,
            "data": {"choices": [{"message": {"content": _ame_lines(["あめ", "そら"])}}]},
        }
    )

    result = GenerationService(client, "openai/gpt-oss-120b", search_ame).generate("Ame", None)

    assert client.calls == 1
    assert result.draft.lines[0].readingHiragana == "あめ"
    assert result.draft.lines[0].pronunciationRomaji == "ame"
    assert result.draft.lines[1].pronunciationRomaji == "sora"


def test_pipe_separated_readings_follow_the_brackets() -> None:
    def search(_title: str, _artist: str) -> Recording:
        return Recording(title="Ame", artist="Example", text="鉄の弾")

    client = FakeGroq(
        {
            "status_code": 200,
            "data": {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {"lines": [{"readings": "てつ|たま", "translationEnglish": "an iron bullet"}]},
                                ensure_ascii=False,
                            )
                        }
                    }
                ]
            },
        }
    )

    result = GenerationService(client, "openai/gpt-oss-120b", search).generate("Ame", None)

    assert client.calls == 1
    assert result.draft.lines[0].readingHiragana == "てつ の たま"
    assert result.draft.lines[0].pronunciationRomaji == "tetsu no tama"


def test_an_empty_validation_failure_is_still_rejected() -> None:
    client = FakeGroq(
        {"status_code": 400, "data": {"error": {"code": "json_validate_failed", "failed_generation": ""}}}
    )

    with pytest.raises(DomainError) as error:
        GenerationService(client, "openai/gpt-oss-120b", search_ame).generate("Ame", None)

    assert error.value.code == "generation_invalid"
    assert client.calls == 1


def test_lyrics_after_a_preamble_or_in_reasoning_are_kept() -> None:
    generated = _ame_lines([["あめ"], ["そら"]])
    decoy = json.dumps(
        {"lines": [{"readings": ["よみ"], "translationEnglish": "wrong"}]},
        ensure_ascii=False,
    )
    fenced = FakeGroq(
        {
            "status_code": 200,
            "data": {"choices": [{"message": {"content": f"```json\n{decoy}\n{generated}\n```"}}]},
        }
    )
    reasoned = FakeGroq(
        {
            "status_code": 200,
            "data": {"choices": [{"message": {"content": None, "reasoning": generated}}]},
        }
    )

    fenced_draft = GenerationService(fenced, "openai/gpt-oss-120b", search_ame).generate("Ame", None)
    reasoned_draft = GenerationService(reasoned, "openai/gpt-oss-120b", search_ame).generate("Ame", None)

    assert fenced.calls == 1
    assert reasoned.calls == 1
    assert fenced_draft.draft.lines[0].readingHiragana == "あめ"
    assert reasoned_draft.draft.lines[1].readingHiragana == "そら"


def test_a_saved_draft_does_not_start_another_completion() -> None:
    song = LyricDraft(
        title="Other",
        artist="Other",
        lines=[
            DraftLine(
                originalText="beta",
                readingHiragana="べーた",
                pronunciationRomaji="beta",
                translationEnglish="second line",
            )
        ],
    )
    client = PromptGroq()

    result = GenerationService(client, "openai/gpt-oss-120b", search_ame).generate("Ame by Example", song)

    assert len(client.prompts) == 1
    assert "beta" not in client.prompts[0]
    assert "second line" not in client.prompts[0]
    assert [line.originalText for line in result.draft.lines] == ["雨", "空"]
