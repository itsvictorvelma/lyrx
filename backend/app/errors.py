"""Failures raised by song rules.

The HTTP status is chosen later, when the response is built.
"""

from app.contracts import ErrorDetail


class DomainError(Exception):
    def __init__(self, code: str, message: str, details: list[ErrorDetail] | None = None) -> None:
        self.code = code
        self.message = message
        self.details = details
        super().__init__(message)
