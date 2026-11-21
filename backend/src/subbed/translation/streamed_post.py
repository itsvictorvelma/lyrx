"""One POST to a translator, its streamed reply read within a byte cap and one overall deadline."""

import time

import httpx2

from subbed import config
from subbed.errors import ApiError


def post_within_limits(
    client: httpx2.Client, url: str, headers: dict[str, str], content: str, max_bytes: int
) -> tuple[httpx2.Response, bytes]:
    """Exactly one POST: the response (for its status) and its body, read within the limits.

    A timeout or a lost connection is `translation_unavailable`, so the next translator may answer.
    """
    deadline = time.monotonic() + config.TRANSLATOR_DEADLINE_SECONDS
    try:
        with client.stream("POST", url, headers=headers, content=content) as response:
            body = read_within_limits(response, max_bytes, deadline)
    except httpx2.TimeoutException:
        raise ApiError("translation_unavailable", reason="timeout") from None
    except httpx2.RequestError:
        raise ApiError("translation_unavailable", reason="connect_error") from None
    return response, body


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
