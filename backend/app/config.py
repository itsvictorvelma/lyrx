"""Settings read from backend/.env.

Audio files and temporary uploads must be different directories.
GROQ_MODEL selects the lyric model. The Groq key stays in Swytchcode.
"""

from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

EnvironmentName = Literal["development", "production", "test"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parent.parent / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: EnvironmentName
    database_url: str = Field(min_length=1)
    media_root: str = Field(min_length=1)
    public_media_base_url: str = Field(min_length=1)
    groq_model: str = Field(default="openai/gpt-oss-120b", min_length=1)
    max_audio_bytes: int = Field(default=20_000_000, gt=0)
    allowed_development_origin: str = "http://localhost:5173"
    audio_staging_root: str = "./uploads"

    @model_validator(mode="after")
    def validate_runtime_boundaries(self) -> "Settings":
        media_root = Path(self.media_root).expanduser().resolve()
        audio_staging_root = Path(self.audio_staging_root).expanduser().resolve()
        if media_root == audio_staging_root:
            raise ValueError("media_root and audio_staging_root must be different directories")
        return self


def get_settings() -> Settings:
    return Settings()
