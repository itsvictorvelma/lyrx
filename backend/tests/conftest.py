"""Shared pytest fixtures: the network guard, the fakes, a test app, and a client for it."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from fake_gemini import FakeGemini
from fake_groq import FakeGroq
from fake_lrclib import FakeLrclib
from fastapi import FastAPI
from fastapi.testclient import TestClient

from lyrx import config
from lyrx.app import create_app

# `network_guard`: the autouse guard, every test fails if it reaches the real network.
# `pytester`: lets test_network_guard run a small inner test session.
pytest_plugins = ["network_guard", "pytester"]

# The real library path, read before any test replaces it.
REAL_DATABASE_PATH = config.DATABASE_PATH
# The shipped translator chain, read before any test shortens it.
SHIPPED_TRANSLATORS = config.TRANSLATORS

ALLOWED_TEST_BASE_URL = "http://127.0.0.1:8000"
# The page's own Origin, which every POST, PUT, and DELETE must carry (spec 014).
ALLOWED_TEST_ORIGIN = "http://127.0.0.1:5173"
TEST_PASSWORD = "correct horse battery"
TEST_GEMINI_KEY = "fake-gemini-key-not-real-0123"
TEST_GROQ_KEY = "fake-groq-key-not-real-4567"


@pytest.fixture(autouse=True)
def temporary_database(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Every test gets its own empty library file; the real one is never touched."""
    path = tmp_path / "data" / "lyrx.db"
    monkeypatch.setattr(config, "DATABASE_PATH", path)
    return path


@pytest.fixture(autouse=True)
def no_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    """No key from the developer's shell reaches a test; each test sets the keys it needs."""
    monkeypatch.delenv(config.GEMINI_API_KEY_ENV_VAR, raising=False)
    monkeypatch.delenv(config.GROQ_API_KEY_ENV_VAR, raising=False)


@pytest.fixture(autouse=True)
def one_translator_per_service(monkeypatch: pytest.MonkeyPatch) -> None:
    """The first Groq and the first Gemini translator only, so a scripted failure is one
    request per service; test_translators tests longer chains."""
    first: dict[str, config.Translator] = {}
    for translator in config.TRANSLATORS:
        first.setdefault(translator.service, translator)
    monkeypatch.setattr(config, "TRANSLATORS", tuple(first.values()))


@pytest.fixture(autouse=True)
def no_retry_waits(monkeypatch: pytest.MonkeyPatch) -> None:
    """Retries happen at once in tests; the number of retries stays the configured one."""
    waits = tuple(0.0 for _ in config.RETRY_WAIT_SECONDS)
    monkeypatch.setattr(config, "RETRY_WAIT_SECONDS", waits)


@pytest.fixture(autouse=True)
def cheap_scrypt(monkeypatch: pytest.MonkeyPatch) -> None:
    """A tiny scrypt cost, so tests that sign up stay fast; the stored hash records the cost."""
    monkeypatch.setattr(config, "SCRYPT_COST", (2**4, 1, 1))


@pytest.fixture
def fake_gemini() -> FakeGemini:
    return FakeGemini()


@pytest.fixture
def fake_groq() -> FakeGroq:
    return FakeGroq()


@pytest.fixture
def fake_lrclib() -> FakeLrclib:
    return FakeLrclib()


@pytest.fixture
def gemini_key(monkeypatch: pytest.MonkeyPatch) -> str:
    """Sets a fake Gemini key in the environment for one test."""
    monkeypatch.setenv(config.GEMINI_API_KEY_ENV_VAR, TEST_GEMINI_KEY)
    return TEST_GEMINI_KEY


@pytest.fixture
def groq_key(monkeypatch: pytest.MonkeyPatch) -> str:
    """Sets a fake Groq key in the environment for one test."""
    monkeypatch.setenv(config.GROQ_API_KEY_ENV_VAR, TEST_GROQ_KEY)
    return TEST_GROQ_KEY


@pytest.fixture
def app(fake_gemini: FakeGemini, fake_groq: FakeGroq, fake_lrclib: FakeLrclib) -> FastAPI:
    return create_app(
        lrclib_transport=fake_lrclib.make_transport(),
        gemini_transport=fake_gemini.make_transport(),
        groq_transport=fake_groq.make_transport(),
    )


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    """A guest client whose Host and Origin are allowed, and which returns 500s instead of
    raising them."""
    with make_client(app) as test_client:
        yield test_client


def make_client(app: FastAPI) -> TestClient:
    """A new client with its own cookies, like a second browser."""
    return TestClient(
        app,
        base_url=ALLOWED_TEST_BASE_URL,
        headers={"Origin": ALLOWED_TEST_ORIGIN},
        raise_server_exceptions=False,
    )


def sign_up(client: TestClient, username: str = "mika") -> None:
    """Creates an account in this client, which then stays signed in."""
    response = client.post(
        "/api/account/sign-up", json={"username": username, "password": TEST_PASSWORD}
    )
    assert response.status_code == 200, response.text


@pytest.fixture
def signed_in_client(client: TestClient) -> TestClient:
    """The client, signed in to a new account."""
    sign_up(client)
    return client
