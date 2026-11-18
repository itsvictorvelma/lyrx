"""Data shapes: the request body, the response, the error response, and the model replies."""

from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class VersionsRequest(BaseModel):
    """The body of `POST /api/versions`. A non-string `lyrics` is rejected, not coerced."""

    model_config = ConfigDict(strict=True)

    lyrics: str


class VersionLine(BaseModel):
    """One line of the paste in its four versions."""

    index: int
    original: str
    hiragana: str
    romaji: str
    english: str
    reading_verified: bool = Field(serialization_alias="readingVerified")


class VersionsResponse(BaseModel):
    """The body of a successful `POST /api/versions`: every line of the paste, in order."""

    lines: list[VersionLine]


class ErrorResponse(BaseModel):
    """The one error shape every failed request returns."""

    code: str
    message: str
    details: dict[str, Any] | None = None


class ReplyLine(BaseModel):
    """One line of Claude's reply. Strict: no coercion and no extra fields."""

    model_config = ConfigDict(strict=True, extra="forbid")

    index: int
    reading: str
    english: str


class ClaudeReply(BaseModel):
    """Claude's whole reply: one entry per sent line. Strict: no coercion and no extra fields."""

    model_config = ConfigDict(strict=True, extra="forbid")

    lines: list[ReplyLine]


EnglishErrorCode = Literal[
    "translation_blocked",
    "translation_invalid",
    "translation_rate_limited",
    "translation_unavailable",
]


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


class GeminiLine(BaseModel):
    """One line of Gemini's English. Strict: no coercion and no extra fields."""

    model_config = ConfigDict(strict=True, extra="forbid")

    index: int
    english: str


class GeminiReply(BaseModel):
    """Gemini's reply text as JSON: one entry per sent line. Strict, no extra fields."""

    model_config = ConfigDict(strict=True, extra="forbid")

    lines: list[GeminiLine]


# The shapes below are internal: the server builds them from text it has already checked,
# so they are plain frozen dataclasses, never validated, unlike the Pydantic shapes above.


@dataclass(frozen=True)
class TokenUsage:
    """The tokens a model (Claude or Gemini) reports for one call."""

    input_tokens: int
    output_tokens: int


@dataclass(frozen=True)
class ClaudeReadings:
    """Claude's reply after every check in `claude.py`, and the tokens the call used.

    A dataclass, not a Pydantic model: it is never validated, since its lines already were.
    """

    lines: list[ReplyLine]
    usage: TokenUsage


@dataclass(frozen=True)
class GeminiTranslation:
    """Gemini's English after every check in `gemini.py`, by line index, and the tokens used."""

    english: dict[int, str]
    usage: TokenUsage
