"""Writes the one log line for each `POST /api/versions`: status, counts, time, and tokens."""

import logging
import time
from collections.abc import Iterator
from contextlib import contextmanager
from http import HTTPStatus

from lyrx.errors import ApiError
from lyrx.schemas import TokenUsage

logger = logging.getLogger(__name__)

LogFields = dict[str, int | str]


class RequestLog:
    """The fields of one request's log line, filled in as the request runs.

    Only codes and counts ever go in: never text from the request or the reply.
    """

    def __init__(self, lines: int, characters: int) -> None:
        self.started = time.monotonic()
        self.fields: LogFields = {"lines": lines, "characters": characters}

    def add_tokens(self, usage: TokenUsage) -> None:
        self.fields["input_tokens"] = usage.input_tokens
        self.fields["output_tokens"] = usage.output_tokens

    def write(self, status: int, outcome: LogFields) -> None:
        duration_ms = round((time.monotonic() - self.started) * 1000)
        line = {"status": status, **outcome, **self.fields, "duration_ms": duration_ms}
        logger.info(" ".join(f"{name}={value}" for name, value in line.items()))


@contextmanager
def logged_request(lines: int, characters: int) -> Iterator[RequestLog]:
    """Times the `with` block and writes its one log line, whether it succeeds or fails.

    An `ApiError` is logged with its status and code, then re-raised. Any other exception
    becomes `internal_error`, logged with only its class name, never its message. The
    `CrashGuard` layer is the backstop for errors outside this block.
    """
    log = RequestLog(lines, characters)
    try:
        yield log
    except ApiError as error:
        log.write(error.status, {"code": error.code})
        raise
    except Exception as error:
        internal_error = ApiError("internal_error")
        outcome: LogFields = {"code": internal_error.code, "exception": type(error).__name__}
        log.write(internal_error.status, outcome)
        raise internal_error from None
    log.write(HTTPStatus.OK.value, {})
