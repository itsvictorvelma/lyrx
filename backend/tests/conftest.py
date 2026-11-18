"""Shared pytest fixtures: the network guard, the fakes, a test app, and a client for it."""

from collections.abc import Iterator

import pytest
from fake_gemini import FakeGemini
from fake_lrclib import FakeLrclib
from fastapi import FastAPI
from fastapi.testclient import TestClient

from lyrx import config
from lyrx.app import create_app

# `network_guard`: the autouse guard, every test fails if it reaches the real network.
# `pytester`: lets test_network_guard run a small inner test session.
pytest_plugins = ["network_guard", "pytester"]

ALLOWED_TEST_BASE_URL = "http://127.0.0.1:8000"
TEST_GEMINI_KEY = "fake-gemini-key-not-real-0123"


@pytest.fixture(autouse=True)
def no_retry_waits(monkeypatch: pytest.MonkeyPatch) -> None:
    """Retries happen at once in tests; the number of retries stays the configured one."""
    waits = tuple(0.0 for _ in config.GEMINI_RETRY_WAIT_SECONDS)
    monkeypatch.setattr(config, "GEMINI_RETRY_WAIT_SECONDS", waits)


@pytest.fixture
def fake_gemini() -> FakeGemini:
    return FakeGemini()


@pytest.fixture
def fake_lrclib() -> FakeLrclib:
    return FakeLrclib()


@pytest.fixture
def gemini_key(monkeypatch: pytest.MonkeyPatch) -> str:
    """Sets a fake Gemini key in the environment for one test."""
    monkeypatch.setenv(config.GEMINI_API_KEY_ENV_VAR, TEST_GEMINI_KEY)
    return TEST_GEMINI_KEY


@pytest.fixture
def app(fake_gemini: FakeGemini, fake_lrclib: FakeLrclib) -> FastAPI:
    return create_app(
        lrclib_transport=fake_lrclib.make_transport(),
        gemini_transport=fake_gemini.make_transport(),
    )


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    """A client whose default Host is allowed, and which returns 500s instead of raising them."""
    with TestClient(
        app, base_url=ALLOWED_TEST_BASE_URL, raise_server_exceptions=False
    ) as test_client:
        yield test_client
