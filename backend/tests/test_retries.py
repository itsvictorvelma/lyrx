"""Tests for retries.py: which failures are tried again, how often, and the waits between."""

import time
from collections.abc import Callable

import pytest

from lyrx import config
from lyrx.errors import ApiError, ErrorCode
from lyrx.retries import with_retries


def failing_then(errors: list[ApiError]) -> Callable[[], str]:
    """A request that raises the given errors in turn, then returns "done"."""
    remaining = list(errors)

    def request() -> str:
        if remaining:
            raise remaining.pop(0)
        return "done"

    return request


@pytest.fixture
def waits(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    """The configured waits restored, and every sleep recorded instead of slept."""
    monkeypatch.setattr(config, "GEMINI_RETRY_WAIT_SECONDS", (1.0, 3.0))
    slept: list[float] = []
    monkeypatch.setattr(time, "sleep", slept.append)
    return slept


@pytest.mark.parametrize(
    ("code", "reason"),
    [
        ("translation_unavailable", "timeout"),
        ("translation_unavailable", "connect_error"),
        ("translation_unavailable", "http_500"),
        ("translation_invalid", "bad_json"),
        ("translation_invalid", "finish_MAX_TOKENS"),
    ],
)
def test_a_temporary_failure_is_retried_after_the_configured_waits(
    waits: list[float], code: ErrorCode, reason: str
) -> None:
    error = ApiError(code, reason=reason)

    result, retries = with_retries(failing_then([error, error]))

    assert (result, retries) == ("done", 2)
    assert waits == [1.0, 3.0]


def test_after_the_last_retry_the_error_propagates(waits: list[float]) -> None:
    errors = [ApiError("translation_unavailable", reason="http_503") for _ in range(3)]

    with pytest.raises(ApiError):
        with_retries(failing_then(errors))

    assert waits == [1.0, 3.0]


@pytest.mark.parametrize(
    ("code", "reason"),
    [
        ("translation_rate_limited", "http_429"),
        ("translation_unavailable", "http_400"),
        ("translation_blocked", "finish_RECITATION"),
    ],
)
def test_a_lasting_failure_is_never_retried(
    waits: list[float], code: ErrorCode, reason: str
) -> None:
    with pytest.raises(ApiError) as caught:
        with_retries(failing_then([ApiError(code, reason=reason)]))

    assert caught.value.code == code
    assert waits == []


def test_success_first_time_takes_no_retry(waits: list[float]) -> None:
    assert with_retries(failing_then([])) == ("done", 0)
    assert waits == []
