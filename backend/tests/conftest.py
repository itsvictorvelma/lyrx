"""Default tests do not call Groq or LRCLIB."""

import pytest


@pytest.fixture(autouse=True)
def block_live_lyric_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    def blocked(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("default tests do not call Groq or LRCLIB")

    monkeypatch.setattr("app.generation.lrclib.httpx.get", blocked)
    monkeypatch.setattr("app.generation.groq.SwytchcodeGroq.complete", blocked)
