"""Tests for the server settings in one place: the bind address."""

from lyrx import config


def test_ac31_configured_bind_host_is_loopback_only() -> None:
    assert config.HOST == "127.0.0.1"
