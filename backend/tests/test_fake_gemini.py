"""Tests for the fake Gemini: replies come in script order, requests are recorded, extras fail."""

import json

import httpx2
import pytest
from fake_gemini import (
    FakeGemini,
    UnscriptedGeminiCallError,
    blocked_prompt,
    raw_envelope,
    status,
    stopped,
    success,
)

URL = "https://gemini.invalid/v1/generate"


def post(fake: FakeGemini, body: dict[str, object]) -> httpx2.Response:
    with httpx2.Client(transport=fake.make_transport(), timeout=7) as client:
        return client.post(URL, json=body, headers={"x-test": "yes"})


def test_replies_are_served_in_script_order_and_requests_recorded() -> None:
    fake = FakeGemini()
    fake.script(status(429), success({0: ("きみ", "kimi", "You")}))

    first = post(fake, {"n": 1})
    second = post(fake, {"n": 2})

    assert first.status_code == 429
    reply = second.json()
    text = "".join(part["text"] for part in reply["candidates"][0]["content"]["parts"])
    assert json.loads(text) == {
        "lines": [{"index": 0, "hiragana": "きみ", "romaji": "kimi", "english": "You"}]
    }
    assert reply["candidates"][0]["finishReason"] == "STOP"
    assert reply["usageMetadata"] == {"promptTokenCount": 120, "candidatesTokenCount": 45}
    assert [request.body for request in fake.requests] == [{"n": 1}, {"n": 2}]
    assert fake.requests[0].method == "POST"
    assert fake.requests[0].url == URL
    assert fake.requests[0].headers["x-test"] == "yes"
    assert fake.requests[0].timeout["read"] == 7


def test_an_unscripted_call_fails_and_is_still_recorded() -> None:
    fake = FakeGemini()

    with pytest.raises(UnscriptedGeminiCallError):
        post(fake, {})

    assert len(fake.requests) == 1


def test_a_scripted_exception_is_raised() -> None:
    fake = FakeGemini()
    fake.script(httpx2.ConnectError("no route"))

    with pytest.raises(httpx2.ConnectError):
        post(fake, {})


def test_blocked_stopped_and_raw_replies_have_the_expected_shape() -> None:
    fake = FakeGemini()
    fake.script(blocked_prompt("OTHER"), stopped("SAFETY"), raw_envelope(b"not json"))

    assert post(fake, {}).json() == {"promptFeedback": {"blockReason": "OTHER"}}
    assert post(fake, {}).json()["candidates"][0]["finishReason"] == "SAFETY"
    assert post(fake, {}).content == b"not json"
