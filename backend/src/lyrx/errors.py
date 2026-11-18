"""The API error, the table of error codes with their HTTP status and message, and its response."""

from collections.abc import Mapping
from typing import Literal

from fastapi.responses import JSONResponse

from lyrx.schemas import ErrorResponse

ErrorCode = Literal[
    "invalid_request",
    "empty_input",
    "empty_search",
    "no_japanese",
    "not_lyrics",
    "host_not_allowed",
    "not_found",
    "method_not_allowed",
    "song_not_found",
    "song_not_japanese",
    "lyrics_source_unavailable",
    "translation_rate_limited",
    "translation_blocked",
    "translation_unavailable",
    "translation_invalid",
    "server_not_configured",
    "internal_error",
]

ERROR_TABLE: dict[ErrorCode, tuple[int, str]] = {
    "invalid_request": (400, "The request is not valid."),
    "empty_input": (400, "Paste some lyrics first."),
    "empty_search": (400, "Type a song name first."),
    "no_japanese": (400, "No Japanese text found. Paste Japanese lyrics."),
    "not_lyrics": (413, "This doesn't look like song lyrics."),
    "host_not_allowed": (403, "This server only answers on 127.0.0.1 or localhost."),
    "not_found": (404, "There is nothing at this address."),
    "method_not_allowed": (405, "This address does not accept that method."),
    "song_not_found": (404, "No song found for that name."),
    "song_not_japanese": (422, "Lyrx only supports Japanese songs for now."),
    "lyrics_source_unavailable": (502, "The lyrics site could not be reached. Try again."),
    "translation_rate_limited": (429, "The free Gemini limit was reached. Try again later."),
    "translation_blocked": (502, "Gemini declined these lyrics."),
    "translation_unavailable": (503, "Gemini could not be reached. Try again."),
    "translation_invalid": (502, "Gemini's reply did not pass the checks. Try again."),
    "server_not_configured": (503, "The server has no Gemini API key. See the README."),
    "internal_error": (500, "Something went wrong on the server."),
}


class ApiError(Exception):
    """An error the API returns to the caller as `{code, message}`."""

    def __init__(self, code: ErrorCode) -> None:
        super().__init__(code)
        self.code = code
        self.status, self.message = ERROR_TABLE[code]


def error_response(error: ApiError, headers: Mapping[str, str] | None = None) -> JSONResponse:
    """The one error shape: `code` and `message`."""
    body = ErrorResponse(code=error.code, message=error.message)
    return JSONResponse(status_code=error.status, content=body.model_dump(), headers=headers)
