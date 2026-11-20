"""A scripted clock for the translator deadline, and a reply that arrives in two pieces."""

from dataclasses import dataclass

import httpx2
import pytest

from lyrx.translation import streamed_post


@dataclass
class FakeClock:
    """`monotonic()` returns each scripted time once, in order, then keeps the last one."""

    times: list[float]

    def monotonic(self) -> float:
        return self.times.pop(0) if len(self.times) > 1 else self.times[0]


def use_clock(monkeypatch: pytest.MonkeyPatch, *times: float) -> None:
    """Makes the deadline code read `times` instead of the real clock."""
    monkeypatch.setattr(streamed_post, "time", FakeClock(list(times)))


def trickled(reply: httpx2.Response) -> httpx2.Response:
    """The same reply, streamed in two pieces, so the deadline is checked twice."""
    body = reply.content
    middle = len(body) // 2
    return httpx2.Response(reply.status_code, content=iter([body[:middle], body[middle:]]))
