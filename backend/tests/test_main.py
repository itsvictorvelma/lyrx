"""Tests for the `python -m subbed` entry point: uvicorn on the configured address and proxy."""

from typing import Any

import pytest
import uvicorn

from subbed import config


def run_main(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """The options `python -m subbed` passes to uvicorn, without starting it."""
    uvicorn_calls: list[dict[str, Any]] = []

    def record_uvicorn_run(*arguments: Any, **options: Any) -> None:
        uvicorn_calls.append(options)

    monkeypatch.setattr(uvicorn, "run", record_uvicorn_run)
    from subbed.__main__ import main

    main()

    assert len(uvicorn_calls) == 1
    return uvicorn_calls[0]


def test_ac31_entry_point_starts_uvicorn_on_loopback(monkeypatch: pytest.MonkeyPatch) -> None:
    options = run_main(monkeypatch)

    assert options["host"] == "127.0.0.1"
    assert options["host"] == config.HOST
    assert options["port"] == config.PORT


def test_spec020_ac6_without_a_trusted_proxy_uvicorn_ignores_forwarded_headers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(config, "TRUSTED_PROXY", None)

    assert run_main(monkeypatch)["proxy_headers"] is False


def test_spec020_ac6_uvicorn_trusts_forwarded_headers_only_from_the_proxy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(config, "TRUSTED_PROXY", "172.30.0.10")

    options = run_main(monkeypatch)

    assert options["proxy_headers"] is True
    assert options["forwarded_allow_ips"] == "172.30.0.10"
