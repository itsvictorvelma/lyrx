"""A fake LRCLIB: scripted replies served in order through an `httpx2.MockTransport`.

Every request is recorded before it is answered. A request with no reply left fails the test.
All lyrics here are invented.
"""

from dataclasses import dataclass, field
from typing import Any

import httpx2

# One scripted reply: a response, or an httpx2 exception to raise.
ScriptedReply = httpx2.Response | httpx2.RequestError

JAPANESE_LYRICS = "君の声が聞こえる\n夜空に星が光る\n\nWe sing tonight\nまた会える日まで"
ENGLISH_LYRICS = "We walk along the river\nThe night is warm and long"


class UnscriptedLrclibCallError(AssertionError):
    """The fake LRCLIB got a request with no reply left in its script."""


@dataclass
class FakeLrclib:
    """Scripted replies, used once each, in order. `requests` records every request seen."""

    requests: list[httpx2.Request] = field(default_factory=list)
    replies: list[ScriptedReply] = field(default_factory=list)

    def script(self, *replies: ScriptedReply) -> None:
        self.replies.extend(replies)

    def make_transport(self) -> httpx2.MockTransport:
        return httpx2.MockTransport(self.handle)

    def handle(self, request: httpx2.Request) -> httpx2.Response:
        self.requests.append(request)
        if not self.replies:
            raise UnscriptedLrclibCallError(f"unscripted LRCLIB call #{len(self.requests)}")
        reply = self.replies.pop(0)
        if isinstance(reply, httpx2.RequestError):
            raise reply
        return reply


def record(
    record_id: int = 101,
    track: str = "星の歌",
    artist: str = "ミナト",
    lyrics: str | None = JAPANESE_LYRICS,
    duration: float = 214.4,
    instrumental: bool = False,
    album: str | None = "夜の窓",
    synced: str | None = None,
) -> dict[str, Any]:
    """One LRCLIB record as JSON, with invented values."""
    return {
        "id": record_id,
        "name": track,
        "trackName": track,
        "artistName": artist,
        "albumName": album,
        "duration": duration,
        "instrumental": instrumental,
        "plainLyrics": lyrics,
        "syncedLyrics": synced,
    }


def json_reply(body: Any, status: int = 200) -> httpx2.Response:
    return httpx2.Response(status, json=body)
