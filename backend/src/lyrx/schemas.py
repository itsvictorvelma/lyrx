"""Data shapes: the request body, the error response, and Claude's reply."""

from typing import Any

from pydantic import BaseModel, ConfigDict


class VersionsRequest(BaseModel):
    """The body of `POST /api/versions`. A non-string `lyrics` is rejected, not coerced."""

    model_config = ConfigDict(strict=True)

    lyrics: str


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
