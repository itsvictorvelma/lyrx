"""Tests for the `python -m lyrx` entry point: it starts uvicorn on the configured local address."""

from typing import Any

import pytest
import uvicorn

from lyrx import config


def test_ac31_entry_point_starts_uvicorn_on_loopback(monkeypatch: pytest.MonkeyPatch) -> None:
    uvicorn_calls: list[dict[str, Any]] = []

    def record_uvicorn_run(*arguments: Any, **options: Any) -> None:
        uvicorn_calls.append(options)

    monkeypatch.setattr(uvicorn, "run", record_uvicorn_run)
    from lyrx.__main__ import main

    main()

    assert len(uvicorn_calls) == 1
    assert uvicorn_calls[0]["host"] == "127.0.0.1"
    assert uvicorn_calls[0]["host"] == config.HOST
    assert uvicorn_calls[0]["port"] == config.PORT
