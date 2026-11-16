"""Data shapes for the API: the request body and the error response."""

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
