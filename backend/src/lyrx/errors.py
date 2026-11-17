"""The API error, the table of error codes with their HTTP status and message, and its response."""

from collections.abc import Mapping
from typing import Any, Literal

from fastapi.responses import JSONResponse

from lyrx import config
from lyrx.schemas import ErrorResponse

ErrorCode = Literal[
    "invalid_request",
    "empty_input",
    "no_japanese",
    "input_too_large",
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

SizeLimitName = Literal["maxCharacters", "maxLines", "maxLineCharacters"]

ERROR_TABLE: dict[ErrorCode, tuple[int, str]] = {
    "invalid_request": (400, "The request body must be JSON with a string field `lyrics`."),
    "empty_input": (400, "Paste some lyrics first."),
    "no_japanese": (400, "No Japanese text found. Paste Japanese lyrics."),
    "input_too_large": (
        413,
        f"The lyrics are too long. The limit is {config.MAX_CHARACTERS:,} characters,"
        f" {config.MAX_LINES} lines, and {config.MAX_LINE_CHARACTERS} characters per line.",
    ),
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


def size_limit_details() -> dict[str, Any]:
    """The paste limits: every `input_too_large` error's `details` hold them."""
    return {
        "maxCharacters": config.MAX_CHARACTERS,
        "maxLines": config.MAX_LINES,
        "maxLineCharacters": config.MAX_LINE_CHARACTERS,
    }


class ApiError(Exception):
    """An error the API returns to the caller as `{code, message, details?}`.

    `message` replaces the table's message for this code when given.
    """

    def __init__(
        self,
        code: ErrorCode,
        details: dict[str, Any] | None = None,
        message: str | None = None,
    ) -> None:
        super().__init__(code)
        self.code = code
        self.status, default_message = ERROR_TABLE[code]
        self.message = message or default_message
        self.details = details


def limit_hit_details(
    limit_hit: SizeLimitName, measured: int, line_number: int | None = None
) -> dict[str, Any]:
    """The `details` of a paste over a size limit: the limits, the one hit, what was measured."""
    details = {**size_limit_details(), "limitHit": limit_hit, "measured": measured}
    if line_number is not None:
        details["lineNumber"] = line_number
    return details


def too_many_characters_error(measured: int) -> ApiError:
    message = (
        f"The lyrics are too long: {measured:,} characters."
        f" The limit is {config.MAX_CHARACTERS:,} characters."
    )
    details = limit_hit_details("maxCharacters", measured)
    return ApiError("input_too_large", details=details, message=message)


def too_many_lines_error(measured: int) -> ApiError:
    message = (
        f"The lyrics have too many lines: {measured:,}. The limit is {config.MAX_LINES:,} lines."
    )
    details = limit_hit_details("maxLines", measured)
    return ApiError("input_too_large", details=details, message=message)


def line_too_long_error(line_number: int, measured: int) -> ApiError:
    message = (
        f"Line {line_number:,} is too long: {measured:,} characters."
        f" The limit is {config.MAX_LINE_CHARACTERS:,} characters per line."
        " The lyrics may have lost their line breaks."
    )
    details = limit_hit_details("maxLineCharacters", measured, line_number)
    return ApiError("input_too_large", details=details, message=message)


def error_response(error: ApiError, headers: Mapping[str, str] | None = None) -> JSONResponse:
    """The one error shape: `code`, `message`, and `details` only when there are any."""
    body = ErrorResponse(code=error.code, message=error.message, details=error.details)
    return JSONResponse(
        status_code=error.status, content=body.model_dump(exclude_none=True), headers=headers
    )
