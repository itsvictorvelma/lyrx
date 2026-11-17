"""Shared pytest fixtures: the network guard, the fakes, a test app, and a client for it."""

from collections.abc import Iterator

import pytest
from fake_claude import FakeClaudeClient
from fake_network import FakeNetwork
from fastapi import FastAPI
from fastapi.testclient import TestClient

from lyrx.app import create_app

# `network_guard`: the autouse guard, every test fails if it reaches the real network (AC-57).
# `pytester`: lets test_network_guard run a small inner test session.
pytest_plugins = ["network_guard", "pytester"]

ALLOWED_TEST_BASE_URL = "http://127.0.0.1:8000"


@pytest.fixture
def fake_network() -> FakeNetwork:
    return FakeNetwork()


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
