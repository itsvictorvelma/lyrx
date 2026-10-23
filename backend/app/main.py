from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import Settings, get_settings
from app.contracts import ErrorResponse

IMPORT_PATH = "/api/import"


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved = settings or get_settings()
    if resolved.environment == "production" and resolved.import_enabled:
        raise RuntimeError("import cannot be enabled when environment is production")

    app = FastAPI(title="Lyrx", version="0.1.0")
    app.state.settings = resolved

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    if resolved.environment == "development" and resolved.import_enabled:

        @app.post(
            IMPORT_PATH,
            response_model=ErrorResponse,
            response_model_exclude_none=True,
            status_code=501,
        )
        def import_song() -> ErrorResponse:
            return ErrorResponse(
                code="import_not_implemented",
                message="Song import is not implemented.",
            )

    if resolved.environment == "development":
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[resolved.allowed_development_origin],
            allow_credentials=False,
            allow_methods=["GET", "POST"],
            allow_headers=["Content-Type"],
        )

    return app
