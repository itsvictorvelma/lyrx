"""Tests for the server settings in one place: the bind address, caps, hosts, and the key."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

from subbed import config

SETTING_NAMES = (
    "SUBBED_HOST",
    "SUBBED_ALLOWED_HOSTS",
    "SUBBED_DATABASE_PATH",
    "SUBBED_SECURE_COOKIES",
    "SUBBED_TRUSTED_PROXY",
    "SUBBED_PAGE_DIR",
)


@pytest.fixture
def no_settings(monkeypatch: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    for name in SETTING_NAMES:
        monkeypatch.delenv(name, raising=False)
    return monkeypatch


def test_ac31_configured_bind_host_is_loopback_only(no_settings: pytest.MonkeyPatch) -> None:
    assert config.read_host() == "127.0.0.1"


def test_spec020_ac1_without_settings_the_values_are_the_local_ones(
    no_settings: pytest.MonkeyPatch,
) -> None:
    assert config.read_host() == "127.0.0.1"
    assert config.read_allowed_hosts() == {"127.0.0.1", "localhost"}
    assert config.read_database_path() == config.REPO_ROOT / "data" / "subbed.db"
    assert config.read_secure_cookies() is False
    assert config.read_trusted_proxy() is None
    assert config.read_page_dir() is None


def test_spec020_an_empty_setting_counts_as_unset(no_settings: pytest.MonkeyPatch) -> None:
    for name in SETTING_NAMES:
        no_settings.setenv(name, " ")
    assert config.read_host() == "127.0.0.1"
    assert config.read_allowed_hosts() == {"127.0.0.1", "localhost"}
    assert config.read_page_dir() is None


def test_spec020_server_values_are_read(no_settings: pytest.MonkeyPatch, tmp_path: Path) -> None:
    (tmp_path / "index.html").write_text("<html></html>")
    no_settings.setenv("SUBBED_HOST", "0.0.0.0")
    no_settings.setenv("SUBBED_ALLOWED_HOSTS", "Subbed.Example, www.subbed.example")
    no_settings.setenv("SUBBED_DATABASE_PATH", "/data/subbed.db")
    no_settings.setenv("SUBBED_SECURE_COOKIES", "TRUE")
    no_settings.setenv("SUBBED_TRUSTED_PROXY", "172.30.0.10")
    no_settings.setenv("SUBBED_PAGE_DIR", str(tmp_path))

    assert config.read_host() == "0.0.0.0"
    assert config.read_allowed_hosts() == {"subbed.example", "www.subbed.example"}
    assert config.read_database_path() == Path("/data/subbed.db")
    assert config.read_secure_cookies() is True
    assert config.read_trusted_proxy() == "172.30.0.10"
    assert config.read_page_dir() == tmp_path.resolve()


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("SUBBED_HOST", "everywhere"),
        ("SUBBED_ALLOWED_HOSTS", ","),
        ("SUBBED_ALLOWED_HOSTS", "https://subbed.example"),
        ("SUBBED_ALLOWED_HOSTS", "subbed.example:443"),
        ("SUBBED_ALLOWED_HOSTS", "subbed example"),
        ("SUBBED_SECURE_COOKIES", "yes"),
        ("SUBBED_TRUSTED_PROXY", "caddy"),
        ("SUBBED_PAGE_DIR", "no/such/folder"),
    ],
)
def test_spec020_ac3_a_bad_value_raises_naming_only_the_setting(
    no_settings: pytest.MonkeyPatch, name: str, value: str
) -> None:
    no_settings.setenv(name, value)
    readers = {
        "SUBBED_HOST": config.read_host,
        "SUBBED_ALLOWED_HOSTS": config.read_allowed_hosts,
        "SUBBED_SECURE_COOKIES": config.read_secure_cookies,
        "SUBBED_TRUSTED_PROXY": config.read_trusted_proxy,
        "SUBBED_PAGE_DIR": config.read_page_dir,
    }

    with pytest.raises(config.SettingError) as caught:
        readers[name]()

    assert str(caught.value) == name


def test_spec020_ac3_a_bad_value_stops_the_start_without_showing_the_value() -> None:
    secret_looking = "not-a-boolean-s3cr3t"
    environment = {key: value for key, value in os.environ.items() if key not in SETTING_NAMES}
    environment["SUBBED_SECURE_COOKIES"] = secret_looking

    started = subprocess.run(
        [sys.executable, "-c", "import subbed.config"],
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert started.returncode == 1
    assert "SUBBED_SECURE_COOKIES" in started.stderr
    assert secret_looking not in started.stderr + started.stdout
    assert "Traceback" not in started.stderr


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
