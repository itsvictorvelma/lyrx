"""Tests for the server settings in one place: the bind address, caps, hosts, and the key."""

import pytest

from lyrx import config


def test_ac31_configured_bind_host_is_loopback_only() -> None:
    assert config.HOST == "127.0.0.1"


def test_spec003_ac65_request_body_cap_is_256_kib() -> None:
    assert config.MAX_BODY_BYTES == 262_144


@pytest.mark.parametrize("removed", ["MAX_CHARACTERS", "MAX_LINES", "MAX_LINE_CHARACTERS"])
def test_spec003_ac33_spec_001_size_limits_are_gone(removed: str) -> None:
    """Spec 003: the security caps are the only size limits."""
    assert not hasattr(config, removed)


def test_ac9_lrclib_gemini_and_groq_addresses_are_fixed_https_hosts() -> None:
    assert config.LRCLIB_SEARCH_URL == "https://lrclib.net/api/search"
    assert config.LRCLIB_RECORD_URL == "https://lrclib.net/api/get/{id}"
    assert config.GEMINI_URL_TEMPLATE.startswith("https://generativelanguage.googleapis.com/")
    assert config.GROQ_URL == "https://api.groq.com/openai/v1/chat/completions"


def test_an_empty_gemini_key_counts_as_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(config.GEMINI_API_KEY_ENV_VAR, "")
    assert config.read_api_key(config.GEMINI_API_KEY_ENV_VAR) is None
