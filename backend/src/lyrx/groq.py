"""One Groq request for some lines of a song: build it, send it, and read the reply text."""

import json
from typing import Any

import httpx2
from pydantic import ValidationError

from lyrx import config
from lyrx.errors import ApiError
from lyrx.schemas import GroqReply, TokenUsage, TranslatorReply
from lyrx.translation_prompt import (
    REPLY_SCHEMA,
    SYSTEM_INSTRUCTION,
    NumberedLines,
    build_user_message,
)

HTTP_BAD_REQUEST = 400
HTTP_RATE_LIMITED = 429
# Groq answers 413 when one request alone is larger than its per-minute token limit allows.
HTTP_TOO_LARGE_FOR_LIMIT = 413
# Groq answers 400 with this code when the model's output broke the strict schema: a bad reply
# worth retrying, not a refused request.
SCHEMA_FAILED_CODE = b"json_validate_failed"
# Finish reasons that get their own log word; any other is logged as OTHER.
KNOWN_FINISH_REASONS = frozenset({"stop", "length", "content_filter", "tool_calls"})


def ask_groq(
    model: str,
    api_key: str,
    client: httpx2.Client,
    context: NumberedLines,
    wanted: NumberedLines,
) -> TranslatorReply:
    """Groq's reply text for the `wanted` lines, with `context` as the song around them.

    Any failure raises an `ApiError` with a code and a short log reason, never error text.
    """
    content = send_request(api_key, client, json.dumps(build_body(model, context, wanted)))
    reply = parse_reply(content)
    usage = reply.usage
    return TranslatorReply(
        text=reply_text(reply),
        usage=TokenUsage(
            input_tokens=usage.prompt_tokens if usage else 0,
            output_tokens=usage.completion_tokens if usage else 0,
        ),
    )


def build_body(model: str, context: NumberedLines, wanted: NumberedLines) -> dict[str, Any]:
    """The chat-completions body: instruction, lyrics, and the reply shape as a strict schema."""
    return {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_INSTRUCTION},
            {"role": "user", "content": build_user_message(context, wanted)},
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": "line_versions", "strict": True, "schema": REPLY_SCHEMA},
        },
        "temperature": 0,
        "max_completion_tokens": config.GROQ_MAX_OUTPUT_TOKENS,
    }


def send_request(api_key: str, client: httpx2.Client, content: str) -> bytes:
    """Exactly one POST; the reply body, refused as soon as it passes the byte cap."""
    # ponytail: the timeout applies to each step (connect, read), not the whole request, so a
    # reply that trickles in can take longer than 45 s; add a total deadline if that shows up.
    try:
        with client.stream(
            "POST",
            config.GROQ_URL,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            content=content,
        ) as response:
            body = read_capped(response)
    except httpx2.TimeoutException:
        raise ApiError("translation_unavailable", reason="timeout") from None
    except httpx2.RequestError:
        raise ApiError("translation_unavailable", reason="connect_error") from None
    if response.status_code in (HTTP_RATE_LIMITED, HTTP_TOO_LARGE_FOR_LIMIT):
        raise ApiError("translation_rate_limited", reason="http_429")
    if response.status_code == HTTP_BAD_REQUEST and SCHEMA_FAILED_CODE in body:
        raise ApiError("translation_invalid", reason="schema_failed")
    if not response.is_success:
        raise ApiError("translation_unavailable", reason=f"http_{response.status_code}")
    return body


def read_capped(response: httpx2.Response) -> bytes:
    """The body, refused as soon as it passes `config.GROQ_MAX_REPLY_BYTES`."""
    content = bytearray()
    for piece in response.iter_bytes():
        content.extend(piece)
        if len(content) > config.GROQ_MAX_REPLY_BYTES:
            raise ApiError("translation_invalid", reason="too_large")
    return bytes(content)


def parse_reply(content: bytes) -> GroqReply:
    """The reply around the text; anything that is not the expected JSON is invalid."""
    try:
        return GroqReply.model_validate_json(content)
    except (ValidationError, RecursionError):
        raise ApiError("translation_invalid", reason="bad_envelope") from None


def reply_text(reply: GroqReply) -> str:
    """The first choice's text, after the finish-reason checks."""
    if not reply.choices:
        raise ApiError("translation_invalid", reason="no_candidates")
    choice = reply.choices[0]
    finish = choice.finish_reason or "none"
    word = finish if finish in KNOWN_FINISH_REASONS else "OTHER"
    if finish == "content_filter":
        raise ApiError("translation_blocked", reason=f"finish_{word}")
    if finish != "stop" or choice.message is None or choice.message.content is None:
        raise ApiError("translation_invalid", reason=f"finish_{word}")
    return choice.message.content
