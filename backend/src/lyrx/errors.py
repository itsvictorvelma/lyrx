"""The API error and the table of error codes with their HTTP status and message."""

from typing import Any, Literal

ErrorCode = Literal["invalid_request", "host_not_allowed", "internal_error"]

ERROR_TABLE: dict[ErrorCode, tuple[int, str]] = {
    "invalid_request": (400, "The request body must be JSON with a string field `lyrics`."),
    "host_not_allowed": (403, "This server only answers on 127.0.0.1 or localhost."),
    "internal_error": (500, "Something went wrong on the server."),
}


class ApiError(Exception):
    """An error the API returns to the caller as `{code, message, details?}`."""

    def __init__(self, code: ErrorCode, details: dict[str, Any] | None = None) -> None:
        super().__init__(code)
        self.code = code
        self.status, self.message = ERROR_TABLE[code]
        self.details = details
