"""Data shapes: the request body, the response, the error response, and Claude's reply."""

from dataclasses import dataclass
from typing import Any

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


# The shapes below are internal: the server builds them from text it has already checked,
# so they are plain frozen dataclasses, never validated, unlike the Pydantic shapes above.


@dataclass(frozen=True)
class Paste:
    """The pasted lyrics normalized to NFC, and the same text split into lines."""

    text: str
    lines: list[str]


@dataclass(frozen=True)
class TokenUsage:
    """The tokens Claude reports for the one call."""

    input_tokens: int
    output_tokens: int


@dataclass(frozen=True)
class ClaudeReadings:
    """Claude's reply after every check in `claude.py`, and the tokens the call used.

    A dataclass, not a Pydantic model: it is never validated, since its lines already were.
    """

    lines: list[ReplyLine]
    usage: TokenUsage
