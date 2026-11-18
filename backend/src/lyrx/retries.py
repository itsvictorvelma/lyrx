"""Runs one Gemini request again after a short wait when the failure is likely temporary."""

import time
from collections.abc import Callable

from lyrx import config
from lyrx.errors import ApiError

# Overloaded, timed out, or an unusable reply: worth one more try. A rate limit (429) is not,
# since every retry would spend more of the free quota; a block is Google's decision; and a
# refused request (another 4xx) would be refused again.
RETRYABLE_CODES = frozenset({"translation_unavailable", "translation_invalid"})


def is_temporary(error: ApiError) -> bool:
    refused = error.reason is not None and error.reason.startswith("http_4")
    return error.code in RETRYABLE_CODES and not refused


def with_retries[Result](request: Callable[[], Result]) -> tuple[Result, int]:
    """The request's result and how many retries it took; the last error propagates."""
    for retries, wait_seconds in enumerate(config.GEMINI_RETRY_WAIT_SECONDS):
        try:
            return request(), retries
        except ApiError as error:
            if not is_temporary(error):
                raise
        time.sleep(wait_seconds)
    return request(), len(config.GEMINI_RETRY_WAIT_SECONDS)
