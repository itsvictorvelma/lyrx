"""The API error, the table of error codes with their HTTP status and message, and its response."""

from collections.abc import Mapping
from typing import Any, Literal

from fastapi.responses import JSONResponse

from lyrx.schemas import ErrorResponse

ErrorCode = Literal[
    "invalid_request",
    "empty_input",
    "no_japanese",
    "not_lyrics",
    "host_not_allowed",
    "not_found",
    "method_not_allowed",
    "model_refused",
    "model_output_truncated",
    "model_output_invalid",
    "model_unavailable",
    "server_not_configured",
    "internal_error",
]

ERROR_TABLE: dict[ErrorCode, tuple[int, str]] = {
    "invalid_request": (400, "The request body must be JSON with a string field `lyrics`."),
    "empty_input": (400, "Paste some lyrics first."),
    "no_japanese": (400, "No Japanese text found. Paste Japanese lyrics."),
    "not_lyrics": (413, "This doesn't look like song lyrics."),
    "host_not_allowed": (403, "This server only answers on 127.0.0.1 or localhost."),
    "not_found": (404, "There is nothing at this address."),
    "method_not_allowed": (405, "This address does not accept that method."),
    "model_refused": (502, "Claude declined these lyrics. No result was made."),
    "model_output_truncated": (502, "The reply was cut off. Try a shorter part of the song."),
    "model_output_invalid": (502, "Claude's reply did not pass the checks. No result was made."),
    "model_unavailable": (503, "Claude could not be reached. Try again."),
    "server_not_configured": (503, "The server has no Claude API key."),
    "internal_error": (500, "Something went wrong on the server."),
}


class ApiError(Exception):
    """An error the API returns to the caller as `{code, message, details?}`."""

    def __init__(self, code: ErrorCode, details: dict[str, Any] | None = None) -> None:
        super().__init__(code)
        self.code = code
        self.status, self.message = ERROR_TABLE[code]
        self.details = details


def error_response(error: ApiError, headers: Mapping[str, str] | None = None) -> JSONResponse:
    """The one error shape: `code`, `message`, and `details` only when there are any."""
    body = ErrorResponse(code=error.code, message=error.message, details=error.details)
    return JSONResponse(
        status_code=error.status, content=body.model_dump(exclude_none=True), headers=headers
    )
