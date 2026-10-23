import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.config import Settings
from app.main import IMPORT_PATH, create_app


def settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "environment": "development",
        "database_url": "sqlite:///./lyrx.db",
        "media_root": "./media",
        "public_media_base_url": "http://localhost:8000/media",
        "frontend_api_base_url": "http://localhost:8000",
        "import_enabled": False,
    }
    values.update(overrides)
    return Settings(**values)


def test_health() -> None:
    response = TestClient(create_app(settings())).get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_production_settings_reject_import_flag() -> None:
    with pytest.raises(ValidationError, match="import cannot be enabled"):
        settings(environment="production", import_enabled=True)


def test_production_openapi_has_no_import_route() -> None:
    app = create_app(settings(environment="production"))

    assert IMPORT_PATH not in app.openapi()["paths"]


def test_forced_production_import_flag_does_not_boot() -> None:
    forced = Settings.model_construct(
        environment="production",
        import_enabled=True,
        allowed_development_origin="http://localhost:5173",
    )

    with pytest.raises(RuntimeError, match="import cannot be enabled"):
        create_app(forced)


def test_development_import_route_requires_explicit_flag() -> None:
    disabled = create_app(settings(import_enabled=False))
    enabled = create_app(settings(import_enabled=True))

    assert IMPORT_PATH not in disabled.openapi()["paths"]
    assert "post" in enabled.openapi()["paths"][IMPORT_PATH]


def test_development_import_reports_not_implemented() -> None:
    response = TestClient(create_app(settings(import_enabled=True))).post(IMPORT_PATH)

    assert response.status_code == 501
    assert response.json() == {
        "code": "import_not_implemented",
        "message": "Song import is not implemented.",
    }


def test_settings_reject_shared_storage_roots() -> None:
    with pytest.raises(ValidationError, match="must be different directories"):
        settings(import_staging_root="./media")
