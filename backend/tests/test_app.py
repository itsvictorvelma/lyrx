from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.config import Settings
from app.main import create_app


def settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "environment": "development",
        "database_url": "sqlite:///./lyrx.db",
        "media_root": "./media",
        "public_media_base_url": "http://localhost:8000/media",
        "groq_model": "openai/gpt-oss-120b",
    }
    values.update(overrides)
    return Settings(**values)


def test_health() -> None:
    response = TestClient(create_app(settings())).get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_import_route_is_absent() -> None:
    paths = create_app(settings()).openapi()["paths"]

    assert "/api/import" not in paths
    assert "/api/generations" in paths
    assert "/api/songs/{song_id}/audio" in paths


def test_line_timing_routes_are_absent() -> None:
    paths = create_app(settings()).openapi()["paths"]

    assert "/api/songs/{song_id}/line-times" not in paths
    assert "/api/songs/{song_id}/scan" not in paths


def test_unknown_route_uses_the_error_envelope(tmp_path: Path) -> None:
    response = TestClient(create_app(settings(database_url=f"sqlite:///{tmp_path / 'lyrx.db'}"))).get("/api/missing")

    assert response.status_code == 404
    body = response.json()
    assert body["code"] == "not_found"
    assert body["requestId"]


def test_unexpected_failure_uses_the_safe_envelope(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def explode(self: object, song_id: str, media_base_url: str) -> None:
        raise RuntimeError(f"sqlite:///{tmp_path}/secret.db")

    monkeypatch.setattr("app.services.songs.SongService.get_song", explode)
    response = TestClient(create_app(settings(database_url=f"sqlite:///{tmp_path / 'lyrx.db'}"))).get("/api/songs/missing")

    assert response.status_code == 500
    body = response.json()
    assert body["code"] == "internal_error"
    assert body["message"] == "The request failed."
    assert "secret" not in response.text
    assert body["requestId"]


def test_routes_and_services_stay_out_of_sqlalchemy() -> None:
    root = Path(__file__).parents[1] / "app"
    for path in (root / "routers").glob("*.py"):
        text = path.read_text()
        assert "sqlalchemy" not in text
        assert "app.models" not in text
        assert "app.repositories" not in text
    for path in (root / "services").glob("*.py"):
        text = path.read_text()
        assert "sqlalchemy" not in text
        assert "HTTPException" not in text
        assert "app.models" not in text


def test_settings_reject_shared_storage_roots() -> None:
    with pytest.raises(ValidationError, match="must be different directories"):
        settings(audio_staging_root="./media")
