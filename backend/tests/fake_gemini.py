"""A fake Gemini API: scripted replies served in order through an `httpx2.MockTransport`.

`FakeGemini.script(...)` queues one reply per expected request; `make_transport()` gives the
transport the Gemini client sends through. Every request is recorded (URL, headers, timeout,
parsed JSON body) before it is answered, so a test can count calls. A request with no reply
left fails the test: Lyrx never retries, so an extra call is always a bug.
"""

import json
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

    def script(self, *replies: ScriptedReply) -> None:
        """Queues one reply per expected request."""
        self.replies.extend(replies)

    def make_transport(self) -> httpx2.MockTransport:
        return httpx2.MockTransport(self.handle)

    def handle(self, request: httpx2.Request) -> httpx2.Response:
        timeout = request.extensions.get("timeout")
        self.requests.append(
            SeenGeminiRequest(
                method=request.method,
                url=str(request.url),
                headers=request.headers,
                timeout=dict(timeout) if isinstance(timeout, dict) else {},
                body=json.loads(request.content),
            )
        )
        if not self.replies:
            raise UnscriptedGeminiCallError(f"unscripted Gemini call #{len(self.requests)}")
        reply = self.replies.pop(0)
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


def success(
    english: dict[int, str], prompt_tokens: int = 120, output_tokens: int = 45
) -> httpx2.Response:
    """A valid reply: one item per index, in the dict's order, with token counts."""
    items = [{"index": index, "english": text} for index, text in english.items()]
    usage = {"promptTokenCount": prompt_tokens, "candidatesTokenCount": output_tokens}
    return candidate_reply(lines_text(items), usage=usage)


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
