"""Settings read from backend/.env.authoring.

Kept apart from app/config.py so the API never needs model keys.
AUTHORING_MODEL uses init_chat_model's "provider:model" form.
"""

from pathlib import Path

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROVIDER_KEY_FIELDS = {"google_genai": "google_api_key", "groq": "groq_api_key"}


class AuthoringSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env.authoring",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    authoring_model: str = Field(min_length=1)
    google_api_key: SecretStr | None = None
    groq_api_key: SecretStr | None = None
    authoring_output_dir: Path = BACKEND_DIR / "drafts"

    @property
    def provider(self) -> str:
        return self.authoring_model.split(":", 1)[0]

    @model_validator(mode="after")
    def require_provider_key(self) -> "AuthoringSettings":
        if ":" not in self.authoring_model:
            raise ValueError("authoring_model must look like provider:model-id")

        key_field = PROVIDER_KEY_FIELDS.get(self.provider)
        if key_field is None:
            raise ValueError(f"authoring_model provider must be one of {sorted(PROVIDER_KEY_FIELDS)}")

        key: SecretStr | None = getattr(self, key_field)
        if key is None or not key.get_secret_value():
            raise ValueError(f"{key_field} is required when authoring_model uses {self.provider}")
        return self


def get_authoring_settings() -> AuthoringSettings:
    return AuthoringSettings()
