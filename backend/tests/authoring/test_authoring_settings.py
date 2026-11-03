import pytest
from pydantic import ValidationError

from authoring.settings import AuthoringSettings

KEY_VARIABLES = ("AUTHORING_MODEL", "GOOGLE_API_KEY", "GROQ_API_KEY", "AUTHORING_OUTPUT_DIR")


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in KEY_VARIABLES:
        monkeypatch.delenv(name, raising=False)


def authoring_settings(**values: object) -> AuthoringSettings:
    return AuthoringSettings(_env_file=None, **values)


def test_google_model_with_key_is_accepted() -> None:
    settings = authoring_settings(authoring_model="google_genai:flash", google_api_key="key")

    assert settings.provider == "google_genai"


def test_model_requires_provider_prefix() -> None:
    with pytest.raises(ValidationError, match="provider:model-id"):
        authoring_settings(authoring_model="flash", google_api_key="key")


def test_unknown_provider_is_rejected() -> None:
    with pytest.raises(ValidationError, match="provider must be one of"):
        authoring_settings(authoring_model="openai:gpt", google_api_key="key")


@pytest.mark.parametrize("key", [None, ""])
def test_provider_key_is_required(key: str | None) -> None:
    with pytest.raises(ValidationError, match="google_api_key is required"):
        authoring_settings(authoring_model="google_genai:flash", google_api_key=key)


def test_groq_needs_its_own_key() -> None:
    with pytest.raises(ValidationError, match="groq_api_key is required"):
        authoring_settings(authoring_model="groq:model", google_api_key="key")
