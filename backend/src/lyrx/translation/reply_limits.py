"""Reading a translator's streamed reply within a byte cap and one overall deadline."""

import time

import httpx2

from lyrx import config
from lyrx.errors import ApiError


def deadline_from_now() -> float:
    """The `time.monotonic()` value after which a request is abandoned."""
    return time.monotonic() + config.TRANSLATOR_DEADLINE_SECONDS


def read_within_limits(response: httpx2.Response, max_bytes: int, deadline: float) -> bytes:
    """The body, refused as soon as it passes `max_bytes` or the deadline."""
    # ponytail: the deadline is checked between chunks, so one slow read can still run for the
    # per-step timeout past it; a worker thread with a hard stop would close that gap.
    content = bytearray()
    for piece in response.iter_bytes():
        content.extend(piece)
        if len(content) > max_bytes:
            raise ApiError("translation_invalid", reason="too_large")
        if time.monotonic() > deadline:
            raise ApiError("translation_unavailable", reason="deadline")
    return bytes(content)
