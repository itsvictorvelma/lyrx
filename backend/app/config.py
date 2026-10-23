"""Settings read from backend/.env.

Production cannot enable song import. Audio files and temporary uploads
must be different directories.
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
    frontend_api_base_url: str = Field(min_length=1)
    import_enabled: bool = False
    max_import_bytes: int = Field(default=20_000_000, gt=0)
    allowed_development_origin: str = "http://localhost:5173"
    import_staging_root: str = "./uploads"

    @model_validator(mode="after")
    def validate_runtime_boundaries(self) -> "Settings":
        if self.environment == "production" and self.import_enabled:
            raise ValueError("import cannot be enabled when environment is production")

        media_root = Path(self.media_root).expanduser().resolve()
        import_staging_root = Path(self.import_staging_root).expanduser().resolve()
        if media_root == import_staging_root:
            raise ValueError("media_root and import_staging_root must be different directories")
        return self


def get_settings() -> Settings:
    return Settings()
