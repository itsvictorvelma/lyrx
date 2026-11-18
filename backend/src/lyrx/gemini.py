"""One Gemini request for some lines of a song: build it, send it, and read the reply text."""

import json
import re
from typing import Any

import httpx2
from pydantic import ValidationError

from lyrx import config
from lyrx.errors import ApiError
from lyrx.schemas import GeminiEnvelope, TokenUsage, TranslatorReply
from lyrx.translation_prompt import (
    REPLY_SCHEMA,
    SYSTEM_INSTRUCTION,
    NumberedLines,
    build_user_message,
)

# Finish reasons where Gemini's own filters stopped the reply.
BLOCKED_FINISH_REASONS = frozenset(
    {"SAFETY", "RECITATION", "PROHIBITED_CONTENT", "BLOCKLIST", "SPII"}
)
HTTP_RATE_LIMITED = 429
# Gemini's reason words go into the log only if they look like its own UPPER_CASE names.
REASON_WORD = re.compile(r"[A-Z_]{1,40}")


def ask_gemini(
    model: str,
    api_key: str,
    client: httpx2.Client,
    context: NumberedLines,
    wanted: NumberedLines,
) -> TranslatorReply:
    """Gemini's reply text for the `wanted` lines, with `context` as the song around them.

    Any failure raises an `ApiError` with a code and a short log reason, never error text.
    """
    response = send_request(model, api_key, client, json.dumps(build_body(context, wanted)))
    envelope = parse_envelope(response)
    usage = envelope.usage_metadata
    return TranslatorReply(
        text=reply_text(envelope),
        usage=TokenUsage(
            input_tokens=usage.prompt_token_count if usage else 0,
            output_tokens=usage.candidates_token_count if usage else 0,
        ),
    )


def build_body(context: NumberedLines, wanted: NumberedLines) -> dict[str, Any]:
    """The `generateContent` request body: instruction, lyrics, and the JSON reply schema."""
    return {
        "systemInstruction": {"parts": [{"text": SYSTEM_INSTRUCTION}]},
        "contents": [{"role": "user", "parts": [{"text": build_user_message(context, wanted)}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseJsonSchema": REPLY_SCHEMA,
            "maxOutputTokens": config.GEMINI_MAX_OUTPUT_TOKENS,
            "thinkingConfig": {"thinkingLevel": config.GEMINI_THINKING_LEVEL},
        },
        "store": False,
    }


def send_request(model: str, api_key: str, client: httpx2.Client, content: str) -> httpx2.Response:
    """Exactly one POST to one model."""
    # ponytail: the reply is read with no byte cap. It is bounded by maxOutputTokens and comes
    # from a fixed host; stream it with a cap if that ever changes.
    # ponytail: the timeout applies to each step (connect, read), not the whole request, so a
    # reply that trickles in can take longer than 45 s; add a total deadline if that shows up.
    try:
        response = client.post(
            config.GEMINI_URL_TEMPLATE.format(model=model),
            headers={"x-goog-api-key": api_key},
            content=content,
        )
    except httpx2.TimeoutException:
        raise ApiError("translation_unavailable", reason="timeout") from None
    except httpx2.RequestError:
        raise ApiError("translation_unavailable", reason="connect_error") from None
    if response.status_code == HTTP_RATE_LIMITED:
        raise ApiError("translation_rate_limited", reason="http_429")
    if not response.is_success:
        raise ApiError("translation_unavailable", reason=f"http_{response.status_code}")
    return response


def parse_envelope(response: httpx2.Response) -> GeminiEnvelope:
    """The reply around the text; anything that is not the expected JSON is invalid."""
    try:
        return GeminiEnvelope.model_validate_json(response.content)
    except (ValidationError, RecursionError):
        raise ApiError("translation_invalid", reason="bad_envelope") from None


def reply_text(envelope: GeminiEnvelope) -> str:
    """The first candidate's text parts joined, after the block and finish-reason checks."""
    if envelope.prompt_feedback and envelope.prompt_feedback.block_reason:
        reason = log_word(envelope.prompt_feedback.block_reason)
        raise ApiError("translation_blocked", reason=f"block_{reason}")
    if not envelope.candidates:
        raise ApiError("translation_invalid", reason="no_candidates")
    candidate = envelope.candidates[0]
    finish = log_word(candidate.finish_reason or "NONE")
    if candidate.finish_reason in BLOCKED_FINISH_REASONS:
        raise ApiError("translation_blocked", reason=f"finish_{finish}")
    if candidate.finish_reason != "STOP" or candidate.content is None:
        raise ApiError("translation_invalid", reason=f"finish_{finish}")
    return "".join(part.text for part in candidate.content.parts)


def log_word(word: str) -> str:
    """Gemini's reason word if it looks like one of its UPPER_CASE names, else OTHER."""
    return word if REASON_WORD.fullmatch(word) else "OTHER"
