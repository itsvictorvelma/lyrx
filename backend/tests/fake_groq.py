"""A fake Groq API: the same scripted transport as the fake Gemini, with Groq-shaped replies."""

import json
from typing import Any

import httpx2
from fake_gemini import FakeGemini, SeenGeminiRequest, Versions, placeholder_versions


class FakeGroq(FakeGemini):
    """Scripted Groq replies, used once each, in order. `requests` records every request seen."""


def groq_reply(
    text: str | None, finish_reason: str = "stop", usage: dict[str, int] | None = None
) -> httpx2.Response:
    """A chat-completions reply whose one choice holds `text`."""
    body: dict[str, Any] = {
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": text},
                "finish_reason": finish_reason,
            }
        ]
    }
    if usage is not None:
        body["usage"] = usage
    return httpx2.Response(200, json=body)


def groq_success(
    versions: dict[int, Versions], prompt_tokens: int = 200, output_tokens: int = 80
) -> httpx2.Response:
    """A valid reply: one (hiragana, romaji, english) item per index, in the dict's order."""
    items = [
        {"index": index, "hiragana": hiragana, "romaji": romaji, "english": english}
        for index, (hiragana, romaji, english) in versions.items()
    ]
    usage = {"prompt_tokens": prompt_tokens, "completion_tokens": output_tokens}
    return groq_reply(json.dumps({"lines": items}, ensure_ascii=False), usage=usage)


def groq_sent_indexes(request: SeenGeminiRequest) -> list[int]:
    """The line numbers a Groq request asks for, from the user message's last line."""
    last_line = str(request.body["messages"][1]["content"]).rsplit("\n", 1)[-1]
    return [int(number) for number in last_line.removeprefix("Line numbers: ").split(", ")]


def groq_answer_with_placeholders(request: SeenGeminiRequest) -> httpx2.Response:
    """For `FakeGroq.answer`: valid placeholder versions for whatever lines were asked."""
    return groq_success(
        {index: placeholder_versions(index) for index in groq_sent_indexes(request)}
    )


def groq_status(code: int, error_code: str = "fake_error") -> httpx2.Response:
    """An error reply with the given HTTP status and Groq's error body."""
    body = {"error": {"message": "fake error", "type": "invalid_request_error", "code": error_code}}
    return httpx2.Response(code, json=body)
