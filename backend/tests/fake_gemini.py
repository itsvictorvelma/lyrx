"""A fake Gemini API served through an `httpx2.MockTransport`.

`FakeGemini.script(...)` queues one reply per expected request, used in order. For chunks sent
at the same time, `answer` replies by the request's content instead. Every request is recorded
(URL, headers, timeout, parsed JSON body) before it is answered. A request with no scripted
reply and no `answer` fails the test, so an unexpected extra call is caught.
"""

import json
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import httpx2

# One scripted reply: a response, or an httpx2 exception to raise.
ScriptedReply = httpx2.Response | httpx2.RequestError


class UnscriptedGeminiCallError(AssertionError):
    """The fake Gemini got a request with no reply left in its script."""


@dataclass(frozen=True)
class SeenGeminiRequest:
    """One request the fake Gemini received. `body` is the parsed JSON body."""

    method: str
    url: str
    headers: httpx2.Headers
    timeout: dict[str, Any]
    body: dict[str, Any]


@dataclass
class FakeGemini:
    """Scripted replies, used once each, in order. `requests` records every request seen."""

    requests: list[SeenGeminiRequest] = field(default_factory=list)
    replies: list[ScriptedReply] = field(default_factory=list)
    # Replies to any request once the script is used up, chosen from the request itself.
    answer: Callable[["SeenGeminiRequest"], ScriptedReply] | None = None
    lock: threading.Lock = field(default_factory=threading.Lock)

    def script(self, *replies: ScriptedReply) -> None:
        """Queues one reply per expected request."""
        self.replies.extend(replies)

    def make_transport(self) -> httpx2.MockTransport:
        return httpx2.MockTransport(self.handle)

    def handle(self, request: httpx2.Request) -> httpx2.Response:
        timeout = request.extensions.get("timeout")
        seen = SeenGeminiRequest(
            method=request.method,
            url=str(request.url),
            headers=request.headers,
            timeout=dict(timeout) if isinstance(timeout, dict) else {},
            body=json.loads(request.content),
        )
        with self.lock:
            self.requests.append(seen)
            if self.replies:
                reply = self.replies.pop(0)
            elif self.answer is not None:
                reply = self.answer(seen)
            else:
                raise UnscriptedGeminiCallError(f"unscripted Gemini call #{len(self.requests)}")
        if isinstance(reply, httpx2.RequestError):
            raise reply
        return reply


def envelope(body: dict[str, Any], status: int = 200) -> httpx2.Response:
    """A Gemini reply with the given JSON envelope."""
    return httpx2.Response(status, json=body)


def candidate_reply(
    text: str,
    finish_reason: str = "STOP",
    usage: dict[str, int] | None = None,
) -> httpx2.Response:
    """A reply whose one candidate holds `text`, split over two parts as Gemini may send it."""
    middle = len(text) // 2
    body: dict[str, Any] = {
        "candidates": [
            {
                "content": {
                    "role": "model",
                    "parts": [{"text": text[:middle]}, {"text": text[middle:]}],
                },
                "finishReason": finish_reason,
            }
        ]
    }
    if usage is not None:
        body["usageMetadata"] = usage
    return envelope(body)


def lines_text(items: list[dict[str, Any]]) -> str:
    """The reply text for the given `lines` items, as JSON."""
    return json.dumps({"lines": items}, ensure_ascii=False)


Versions = tuple[str, str, str]


def success(
    versions: dict[int, Versions], prompt_tokens: int = 120, output_tokens: int = 45
) -> httpx2.Response:
    """A valid reply: one (hiragana, romaji, english) item per index, in the dict's order."""
    items = [
        {"index": index, "hiragana": hiragana, "romaji": romaji, "english": english}
        for index, (hiragana, romaji, english) in versions.items()
    ]
    usage = {"promptTokenCount": prompt_tokens, "candidatesTokenCount": output_tokens}
    return candidate_reply(lines_text(items), usage=usage)


def placeholder_versions(index: int) -> Versions:
    """Valid invented versions for any line: kana, romaji, and English naming the index."""
    return ("かな", "kana", f"English {index}")


def success_for(indexes: list[int]) -> httpx2.Response:
    """A valid reply with placeholder versions for the given line indexes."""
    return success({index: placeholder_versions(index) for index in indexes})


def user_text(request: "SeenGeminiRequest") -> str:
    return str(request.body["contents"][0]["parts"][0]["text"])


def sent_indexes(request: "SeenGeminiRequest") -> list[int]:
    """The line numbers a request asks for, from the user message's last line."""
    last_line = user_text(request).rsplit("\n", 1)[-1]
    numbers = last_line.removeprefix("Line numbers: ")
    return [int(number) for number in numbers.split(", ")]


def context_indexes(request: "SeenGeminiRequest") -> list[int]:
    """The line numbers of the song lines sent as context inside the lyrics delimiter."""
    lines = user_text(request).split("\n")
    return [int(line[1 : line.index("]")]) for line in lines if line.startswith("[")]


def answer_with_placeholders(request: "SeenGeminiRequest") -> httpx2.Response:
    """For `FakeGemini.answer`: valid placeholder versions for whatever lines were asked."""
    return success_for(sent_indexes(request))


def blocked_prompt(reason: str = "SAFETY") -> httpx2.Response:
    """Gemini blocked the prompt itself: a block reason and no candidates."""
    return envelope({"promptFeedback": {"blockReason": reason}})


def stopped(finish_reason: str, text: str = "") -> httpx2.Response:
    """A reply that ended for `finish_reason`, holding `text` (often empty) so far."""
    return candidate_reply(text, finish_reason=finish_reason)


def status(code: int) -> httpx2.Response:
    """An error reply with the given HTTP status and a small JSON error body."""
    return envelope({"error": {"code": code, "message": "fake error", "status": "FAKE"}}, code)


def raw_envelope(content: bytes) -> httpx2.Response:
    """A 200 reply whose body is exactly `content`, JSON or not."""
    return httpx2.Response(200, content=content, headers={"Content-Type": "application/json"})
