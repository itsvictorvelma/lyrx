"""Gemini: its client, one request for some lines of a song, and the reply shape."""

import json
import re
from typing import Any

import httpx2
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from lyrx import config
from lyrx.errors import ApiError
from lyrx.translation.prompt import (
    REPLY_SCHEMA,
    SYSTEM_INSTRUCTION,
    NumberedLines,
    build_user_message,
)
from lyrx.translation.results import TokenUsage, TranslatorReply
from lyrx.translation.streamed_post import post_within_limits

# Finish reasons where Gemini's own filters stopped the reply.
BLOCKED_FINISH_REASONS = frozenset(
    {"SAFETY", "RECITATION", "PROHIBITED_CONTENT", "BLOCKLIST", "SPII"}
)
HTTP_RATE_LIMITED = 429
# Gemini's reason words go into the log only if they look like its own UPPER_CASE names.
REASON_WORD = re.compile(r"[A-Z_]{1,40}")


class GeminiPart(BaseModel):
    """One part of a Gemini candidate's content. A part may hold no text."""

    model_config = ConfigDict(strict=True)

    text: str = ""


class GeminiContent(BaseModel):
    """A Gemini candidate's content: its parts, in order."""

    model_config = ConfigDict(strict=True)

    parts: list[GeminiPart] = []


class GeminiCandidate(BaseModel):
    """One Gemini candidate. A blocked or empty candidate may have no content."""

    model_config = ConfigDict(strict=True)

    content: GeminiContent | None = None
    finish_reason: str | None = Field(default=None, alias="finishReason")


class GeminiPromptFeedback(BaseModel):
    """Gemini's verdict on the prompt; a block reason means the prompt was blocked."""

    model_config = ConfigDict(strict=True)

    block_reason: str | None = Field(default=None, alias="blockReason")


class GeminiUsage(BaseModel):
    """The token counts Gemini reports. A missing count is zero."""

    model_config = ConfigDict(strict=True)

    prompt_token_count: int = Field(default=0, alias="promptTokenCount")
    candidates_token_count: int = Field(default=0, alias="candidatesTokenCount")


class GeminiEnvelope(BaseModel):
    """The `generateContent` reply around the text. Fields Lyrx does not read are ignored."""

    model_config = ConfigDict(strict=True)

    candidates: list[GeminiCandidate] = []
    prompt_feedback: GeminiPromptFeedback | None = Field(default=None, alias="promptFeedback")
    usage_metadata: GeminiUsage | None = Field(default=None, alias="usageMetadata")


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
    content = send_request(model, api_key, client, json.dumps(build_body(context, wanted)))
    envelope = parse_envelope(content)
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


def send_request(model: str, api_key: str, client: httpx2.Client, content: str) -> bytes:
    """Exactly one POST to one model; the reply body, refused as soon as it passes a limit."""
    response, body = post_within_limits(
        client,
        config.GEMINI_URL_TEMPLATE.format(model=model),
        {"x-goog-api-key": api_key},
        content,
        config.GEMINI_MAX_REPLY_BYTES,
    )
    if response.status_code == HTTP_RATE_LIMITED:
        raise ApiError("translation_rate_limited", reason="http_429")
    if not response.is_success:
        raise ApiError("translation_unavailable", reason=f"http_{response.status_code}")
    return body


def parse_envelope(content: bytes) -> GeminiEnvelope:
    """The reply around the text; anything that is not the expected JSON is invalid."""
    try:
        return GeminiEnvelope.model_validate_json(content)
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


def make_gemini_client(transport: httpx2.BaseTransport) -> httpx2.Client:
    """No proxies from the environment; the timeout applies to each step of a request."""
    return httpx2.Client(
        transport=transport, timeout=config.GEMINI_TIMEOUT_SECONDS, trust_env=False
    )
