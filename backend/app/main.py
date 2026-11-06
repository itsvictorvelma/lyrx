"""Lyrx API.

GET /api/health is always available.
GET /api/songs lists published songs.
GET /api/songs/{song_id} returns one song and its lyric lines.
POST /api/generations asks Groq for a lyric draft and does not save it.
POST /api/songs saves a draft.
POST /api/songs/{song_id}/audio attaches one MP3.
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import Settings, get_settings
from app.core.context import bind_request_id
from app.core.responses import guard_unexpected, register_exception_handlers
from app.database import open_database
from app.routers.generations import router as generations_router
from app.routers.health import router as health_router
from app.routers.songs import router as songs_router


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved = settings or get_settings()

    app = FastAPI(title="Lyrx", version="0.1.0")
    app.state.settings = resolved
    app.state.engine, app.state.sessions = open_database(resolved.database_url)
    register_exception_handlers(app)
    app.middleware("http")(guard_unexpected)
    app.middleware("http")(bind_request_id)

    app.include_router(health_router)
    app.include_router(songs_router)
    app.include_router(generations_router)

    if resolved.environment == "development":
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[resolved.allowed_development_origin],
            allow_credentials=False,
            allow_methods=["GET", "POST"],
            allow_headers=["Content-Type", "X-Request-ID"],
        )

    media_root = Path(resolved.media_root)
    media_root.mkdir(parents=True, exist_ok=True)
    app.mount("/media", StaticFiles(directory=media_root), name="media")
    return app
