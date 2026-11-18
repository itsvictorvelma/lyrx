"""Tests for the request log: one line per request with only codes, counts, time, and tokens."""

import logging
import re

import pytest

from lyrx.errors import ApiError
from lyrx.request_log import logged_request
from lyrx.schemas import GeminiVersions, TokenUsage

REQUEST_LOGGER = "lyrx.request_log"
# The request line is written as `name=value` fields, e.g. `status=200 lines=4 ...`.
LOG_FIELD = re.compile(r"(\w+)=(\S+)")
SECRET_MESSAGE = "/Users/someone/private 君の声が test-key-not-real"


def only_request_line(caplog: pytest.LogCaptureFixture) -> dict[str, str]:
    """The fields of the one request-log record written."""
    records = [record for record in caplog.records if record.name == REQUEST_LOGGER]
    assert len(records) == 1, [record.getMessage() for record in records]
    return dict(LOG_FIELD.findall(records[0].getMessage()))


def test_ac33_success_writes_one_line_with_status_counts_duration_and_tokens(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A block that finishes logs status 200, its counts, its duration, and the tokens added."""
    caplog.set_level(logging.DEBUG)

    with logged_request("/api/test", lines=4, characters=21) as log:
        log.add_gemini(GeminiVersions(lines={}, usage=TokenUsage(100, 50), calls=2))
        log.add("results", 7)

    fields = only_request_line(caplog)
    assert fields["route"] == "/api/test"
    assert fields["status"] == "200"
    assert fields["gemini_calls"] == "2"
    assert fields["results"] == "7"
    assert fields["lines"] == "4"
    assert fields["characters"] == "21"
    assert fields["duration_ms"].isdecimal()
    assert fields["input_tokens"] == "100"
    assert fields["output_tokens"] == "50"
    assert "code" not in fields


def test_ac33_api_error_is_reraised_unchanged_and_logged_with_its_status_and_code(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """An ApiError leaves the block as the same object; its line has status and code, no tokens."""
    caplog.set_level(logging.DEBUG)
    error = ApiError("song_not_japanese")

    with pytest.raises(ApiError) as raised, logged_request("/api/test", lines=2, characters=15):
        raise error

    assert raised.value is error
    fields = only_request_line(caplog)
    assert fields["status"] == "422"
    assert fields["code"] == "song_not_japanese"
    assert fields["lines"] == "2"
    assert fields["characters"] == "15"
    assert fields["duration_ms"].isdecimal()
    assert "input_tokens" not in fields
    assert "output_tokens" not in fields


def test_ac33_other_exception_becomes_internal_error_without_its_cause(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Any other exception is replaced by internal_error, with no chained cause or context."""
    caplog.set_level(logging.DEBUG)

    with pytest.raises(ApiError) as raised, logged_request("/api/test", lines=3, characters=10):
        raise RuntimeError(SECRET_MESSAGE)

    assert raised.value.code == "internal_error"
    assert raised.value.__cause__ is None
    assert raised.value.__suppress_context__ is True


def test_ac33_other_exception_is_logged_by_class_name_never_by_message(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The line says status=500 code=internal_error exception=<class>; the message never appears."""
    caplog.set_level(logging.DEBUG)

    with pytest.raises(ApiError), logged_request("/api/test", lines=3, characters=10):
        raise RuntimeError(SECRET_MESSAGE)

    fields = only_request_line(caplog)
    assert fields["status"] == "500"
    assert fields["code"] == "internal_error"
    assert fields["exception"] == "RuntimeError"
    record = next(record for record in caplog.records if record.name == REQUEST_LOGGER)
    record_text = logging.Formatter().format(record) + repr(record.__dict__)
    for secret in [SECRET_MESSAGE, "/Users/someone", "君の声が", "test-key-not-real"]:
        assert secret not in record_text
