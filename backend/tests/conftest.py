"""Shared pytest fixtures: a fake Claude client and a test app and client for the server."""

from collections.abc import Iterator
from types import TracebackType
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

ALLOWED_TEST_BASE_URL = "http://127.0.0.1:8000"


class FakeMessageStream:
    """Stands in for the SDK's message stream: a context manager that hands back a set reply."""

    def __init__(self, final_message: object) -> None:
        self.final_message = final_message

    def __enter__(self) -> "FakeMessageStream":
        return self

    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        return None

    def get_final_message(self) -> object:
        return self.final_message


class FakeMessages:
    """Stands in for `client.messages`. Records every `stream(...)` call's keyword arguments.

    If `error` is set, `stream(...)` records the call and then raises it.
    Otherwise it returns a stream whose `get_final_message()` gives `final_message`.
    """

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.error: BaseException | None = None
        self.final_message: object = None

    def stream(self, **request: Any) -> FakeMessageStream:
        self.calls.append(request)
        if self.error is not None:
            raise self.error
        return FakeMessageStream(self.final_message)


class FakeClaudeClient:
    """Stands in for `anthropic.Anthropic`. No test ever reaches the Claude API or the network.

    Records: `messages.calls`, one dict of keyword arguments per `messages.stream(...)` call.
    Configure: `messages.error` (raised on call) or `messages.final_message` (returned reply).
    """

    def __init__(self) -> None:
        self.messages = FakeMessages()


@pytest.fixture
def fake_claude_client() -> FakeClaudeClient:
    return FakeClaudeClient()


@pytest.fixture
def app(fake_claude_client: FakeClaudeClient) -> FastAPI:
    from lyrx.app import create_app

    return create_app(claude_client=fake_claude_client)


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    """A client whose default Host is allowed, and which returns 500s instead of raising them."""
    with TestClient(
        app, base_url=ALLOWED_TEST_BASE_URL, raise_server_exceptions=False
    ) as test_client:
        yield test_client
