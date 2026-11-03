"""Lyrx API.

GET /api/health is always available.
GET /api/songs lists published songs.
GET /api/songs/{song_id} returns one song and its lyric lines.
POST /api/songs/{song_id}/line-times saves a start time for one or more lines.
POST /api/songs/{song_id}/scan reads the audio and sets a start time on each line.
POST /api/import exists only in development when import is enabled.
"""

from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings, get_settings
from app.contracts import ErrorResponse, LineTimeRequest, SongDetail, SongSummary
from app.database import make_engine
from app.errors import ApiError
from app.importer import ImportRequest, import_song
from app.songs import get_song, list_songs, replace_line_starts, scan_saved_song

IMPORT_PATH = "/api/import"


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved = settings or get_settings()
    if resolved.environment == "production" and resolved.import_enabled:
        raise RuntimeError("import cannot be enabled when environment is production")

    app = FastAPI(title="Lyrx", version="0.1.0")
    app.state.settings = resolved
    app.state.engine = make_engine(resolved.database_url)
    sessions = sessionmaker(bind=app.state.engine)

    def open_session():
        session = sessions()
        try:
            yield session
        finally:
            session.close()

    @app.exception_handler(ApiError)
    def api_error(_request, exc: ApiError) -> JSONResponse:
        payload = ErrorResponse(code=exc.code, message=exc.message, details=exc.details)
        return JSONResponse(status_code=exc.status_code, content=payload.model_dump(exclude_none=True))

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/songs", response_model=list[SongSummary])
    def read_songs(session: Session = Depends(open_session)) -> list[SongSummary]:
        return list_songs(session)

    @app.get("/api/songs/{song_id}", response_model=SongDetail, response_model_exclude_none=True)
    def read_song(song_id: str, session: Session = Depends(open_session)) -> SongDetail:
        return get_song(session, song_id, resolved.public_media_base_url)

    @app.post("/api/songs/{song_id}/line-times", response_model=SongDetail, response_model_exclude_none=True)
    def write_line_times(
        song_id: str,
        body: LineTimeRequest,
        session: Session = Depends(open_session),
    ) -> SongDetail:
        return replace_line_starts(session, song_id, body.lines, resolved.public_media_base_url)

    @app.post("/api/songs/{song_id}/scan", response_model=SongDetail, response_model_exclude_none=True)
    def scan_song(song_id: str, session: Session = Depends(open_session)) -> SongDetail:
        return scan_saved_song(session, resolved, song_id)

    if resolved.environment == "development" and resolved.import_enabled:

        @app.post(IMPORT_PATH, response_model=SongDetail, response_model_exclude_none=True)
        async def import_bundle(
            title: str = Form(),
            artist: str = Form(),
            sourceLanguage: str = Form(),
            targetLanguage: str = Form(),
            replace: bool = Form(False),
            original: UploadFile = File(),
            pronunciation: UploadFile = File(),
            translation: UploadFile = File(),
            audio: UploadFile = File(),
            session: Session = Depends(open_session),
        ) -> JSONResponse:
            request = ImportRequest(
                title=title,
                artist=artist,
                source_language=sourceLanguage,
                target_language=targetLanguage,
                replace=replace,
                original_name=original.filename or "",
                pronunciation_name=pronunciation.filename or "",
                translation_name=translation.filename or "",
                audio_name=audio.filename or "",
                original=await _read_limited(original, resolved.max_import_bytes),
                pronunciation=await _read_limited(pronunciation, resolved.max_import_bytes),
                translation=await _read_limited(translation, resolved.max_import_bytes),
                audio=await _read_limited(audio, resolved.max_import_bytes),
            )
            song, status_code = import_song(session, resolved, request)
            return JSONResponse(status_code=status_code, content=song.model_dump(exclude_none=True))

    if resolved.environment == "development":
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[resolved.allowed_development_origin],
            allow_credentials=False,
            allow_methods=["GET", "POST"],
            allow_headers=["Content-Type"],
        )

    media_root = Path(resolved.media_root)
    media_root.mkdir(parents=True, exist_ok=True)
    app.mount("/media", StaticFiles(directory=media_root), name="media")
    return app


async def _read_limited(upload: UploadFile, limit: int) -> bytes:
    chunks: list[bytes] = []
    size = 0
    while True:
        chunk = await upload.read(1024 * 1024)
        if not chunk:
            break
        size += len(chunk)
        if size > limit:
            raise ApiError(413, "file_too_large", f"{upload.filename or 'A file'} is larger than the import limit.")
        chunks.append(chunk)
    return b"".join(chunks)
