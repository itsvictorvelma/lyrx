"""Shared pytest fixtures: the fake Claude client, a test app, and a client for the server."""

from collections.abc import Iterator

import pytest
from fake_claude import FakeClaudeClient
from fastapi import FastAPI
from fastapi.testclient import TestClient

from lyrx.app import create_app

ALLOWED_TEST_BASE_URL = "http://127.0.0.1:8000"


@pytest.fixture
def fake_claude_client() -> FakeClaudeClient:
    return FakeClaudeClient()


@pytest.fixture
def app(fake_claude_client: FakeClaudeClient) -> FastAPI:
    return create_app(claude_client=fake_claude_client)


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    """A client whose default Host is allowed, and which returns 500s instead of raising them."""
    with TestClient(
        app, base_url=ALLOWED_TEST_BASE_URL, raise_server_exceptions=False
    ) as test_client:
        yield test_client
