"""Tests for the fake Claude client's reply queue, used when one request makes two calls."""

import anthropic
import httpx2
import pytest
from fake_claude import FakeClaudeClient, fake_message


def call(client: FakeClaudeClient, label: str) -> str:
    with client.messages.stream(system=label) as stream:
        return "".join(
            block.text for block in stream.get_final_message().content if block.type == "text"
        )


def test_reply_queue_returns_one_reply_per_call_in_order() -> None:
    client = FakeClaudeClient()
    client.messages.replies = [fake_message('{"lyricLines": [2]}'), fake_message('{"lines": []}')]

    assert call(client, "select") == '{"lyricLines": [2]}'
    assert call(client, "readings") == '{"lines": []}'
    assert [request["system"] for request in client.messages.calls] == ["select", "readings"]
    assert client.messages.replies == []


def test_reply_queue_raises_a_queued_exception_after_recording_the_call() -> None:
    client = FakeClaudeClient()
    error = anthropic.APIConnectionError(request=httpx2.Request("POST", "https://api.example"))
    client.messages.replies = [fake_message('{"lyricLines": [0]}'), error]

    call(client, "select")
    with pytest.raises(anthropic.APIConnectionError):
        call(client, "readings")
    assert len(client.messages.calls) == 2


def test_reply_queue_falls_back_to_final_message_when_empty() -> None:
    client = FakeClaudeClient()
    client.messages.replies = [fake_message("first")]
    client.messages.final_message = fake_message("fallback")

    assert call(client, "one") == "first"
    assert call(client, "two") == "fallback"
