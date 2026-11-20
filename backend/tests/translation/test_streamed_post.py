"""Tests for the overall deadline on one translator request (streamed_post.py, spec 019)."""

import httpx2
import pytest
from fake_clock import trickled, use_clock
from fake_gemini import FakeGemini, success
from fake_groq import FakeGroq, groq_success

from lyrx import config
from lyrx.errors import ApiError
from lyrx.translation.chain import ReadyTranslator, request_versions
from lyrx.translation.gemini import make_gemini_client
from lyrx.translation.groq import make_groq_client
from lyrx.translation.results import ChunkReply

# Invented lines.
LINES = [(0, "君の声が")]
VERSIONS = {0: ("きみ の こえ が", "kimi no koe ga", "Your voice")}
# Start, first piece, second piece: the second piece arrives after the 45 s deadline.
TOO_SLOW = (0.0, 10.0, 50.0)
IN_TIME = (0.0, 10.0, 40.0)


def translator(service: str, fake: FakeGemini) -> ReadyTranslator:
    """The first shipped translator of `service`, talking to `fake` (FakeGroq subclasses it)."""
    chosen = next(t for t in config.TRANSLATORS if t.service == service)
    make_client = make_groq_client if service == "groq" else make_gemini_client
    client = make_client(fake.make_transport())
    return ReadyTranslator(chosen.name, chosen.service, chosen.model, "fake-key", client)


def ask(service: str, reply: httpx2.Response) -> ChunkReply:
    """Sends one request to `service`, whose fake streams `reply` in two pieces."""
    fake = FakeGroq() if service == "groq" else FakeGemini()
    fake.script(trickled(reply))
    return request_versions(LINES, LINES, [translator(service, fake)])


REPLIES = [("groq", groq_success(VERSIONS)), ("gemini", success(VERSIONS))]


@pytest.mark.parametrize(("service", "reply"), REPLIES, ids=["ac1-groq", "ac2-gemini"])
def test_a_reply_still_arriving_after_the_deadline_is_abandoned(
    monkeypatch: pytest.MonkeyPatch, service: str, reply: httpx2.Response
) -> None:
    use_clock(monkeypatch, *TOO_SLOW)

    with pytest.raises(ApiError) as caught:
        ask(service, reply)

    assert (caught.value.code, caught.value.reason) == ("translation_unavailable", "deadline")


@pytest.mark.parametrize(("service", "reply"), REPLIES, ids=["groq", "gemini"])
def test_a_slow_reply_that_ends_before_the_deadline_is_used(
    monkeypatch: pytest.MonkeyPatch, service: str, reply: httpx2.Response
) -> None:
    use_clock(monkeypatch, *IN_TIME)

    assert sorted(ask(service, reply).lines) == sorted(VERSIONS)
