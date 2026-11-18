"""Tests for the server settings in one place: the bind address, caps, hosts, and the key."""

import pytest

from lyrx import config


def test_ac31_configured_bind_host_is_loopback_only() -> None:
    assert config.HOST == "127.0.0.1"


def test_spec003_ac65_request_body_cap_is_256_kib() -> None:
    assert config.MAX_BODY_BYTES == 262_144


def test_spec003_ac28_cleanup_split_length_is_200_characters() -> None:
    assert config.CLEANUP_SPLIT_LENGTH == 200


@pytest.mark.parametrize("removed", ["MAX_CHARACTERS", "MAX_LINES", "MAX_LINE_CHARACTERS"])
def test_spec003_ac33_spec_001_size_limits_are_gone(removed: str) -> None:
    """Spec 003: the security caps are the only size limits."""
    assert not hasattr(config, removed)


def test_lrclib_and_gemini_addresses_are_fixed_https_hosts() -> None:
    assert config.LRCLIB_SEARCH_URL == "https://lrclib.net/api/search"
    assert config.LRCLIB_RECORD_URL == "https://lrclib.net/api/get/{id}"
    assert config.GEMINI_URL.startswith("https://generativelanguage.googleapis.com/")


def test_an_empty_gemini_key_counts_as_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(config.GEMINI_API_KEY_ENV_VAR, "")
    assert config.read_gemini_key() is None
