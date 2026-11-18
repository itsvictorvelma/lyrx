"""Writes the one log line for each API request: route, status, counts, time, and tokens."""

import logging
import time
from collections.abc import Iterator
from contextlib import contextmanager
from http import HTTPStatus

from lyrx.errors import ApiError
from lyrx.translation.results import SongTranslation

logger = logging.getLogger(__name__)

LogFields = dict[str, int | str]


class RequestLog:
    """The fields of one request's log line, filled in as the request runs.

    Only codes and counts ever go in: never text from the request or the reply.
    """

    def __init__(self, route: str, lines: int, characters: int) -> None:
        self.started = time.monotonic()
        self.route = route
        self.fields: LogFields = {"lines": lines, "characters": characters}

    def count_lines(self, lines: list[str]) -> None:
        """The counts of the song's lines; characters as if joined by one `\\n` each."""
        self.fields["lines"] = len(lines)
        self.fields["characters"] = len("\n".join(lines))

    def add_translation(self, versions: SongTranslation) -> None:
        """Which translators answered, how many calls it took, and the tokens they used."""
        if versions.translators:
            self.fields["translator"] = "+".join(versions.translators)
        self.fields["translator_calls"] = versions.calls
        self.fields["translator_retries"] = versions.retries
        self.fields["translator_ms"] = versions.elapsed_ms
        self.fields["missing_lines"] = versions.missing_lines
        self.fields["input_tokens"] = versions.usage.input_tokens
        self.fields["output_tokens"] = versions.usage.output_tokens

    def add(self, name: str, value: int | str) -> None:
        """One more field for the line: a count, such as `results`, or a fixed word."""
        self.fields[name] = value

    def write(self, status: int, outcome: LogFields) -> None:
        duration_ms = round((time.monotonic() - self.started) * 1000)
        line = {
            "route": self.route,
            "status": status,
            **outcome,
            **self.fields,
            "duration_ms": duration_ms,
        }
        logger.info(" ".join(f"{name}={value}" for name, value in line.items()))


@contextmanager
def logged_request(route: str, lines: int = 0, characters: int = 0) -> Iterator[RequestLog]:
    """Times the `with` block and writes its one log line, whether it succeeds or fails.

    The counts start at `lines` and `characters`; `count_lines` replaces them once known.

    An `ApiError` is logged with its status and code, then re-raised. Any other exception
    becomes `internal_error`, logged with only its class name, never its message. The
    `CrashGuard` layer is the backstop for errors outside this block.
    """
    log = RequestLog(route, lines, characters)
    try:
        yield log
    except ApiError as error:
        outcome: LogFields = {"code": error.code}
        if error.reason is not None:
            outcome["reason"] = error.reason
        log.write(error.status, outcome)
        raise
    except Exception as error:
        internal_error = ApiError("internal_error")
        log.write(
            internal_error.status,
            {"code": internal_error.code, "exception": type(error).__name__},
        )
        raise internal_error from None
    log.write(HTTPStatus.OK.value, {})
