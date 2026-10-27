"""Read songs stored by the importer."""

import hashlib
import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.orm import Session

from app.contracts import TIMING_FIELDS, LyricLine, SongDetail, SongSummary
from app.errors import ApiError
from app.models import LyricVersion, Track


def list_songs(session: Session) -> list[SongSummary]:
    try:
        tracks = session.scalars(select(Track).where(Track.status == "published").order_by(Track.title, Track.id))
    except (OperationalError, ProgrammingError) as exc:
        raise database_not_ready() from exc
    return [
        SongSummary(
            id=track.id,
            title=track.title,
            artist=track.artist,
            sourceLanguage=track.source_language,
            targetLanguage=track.target_language,
            durationSeconds=track.duration_seconds,
            status="published",
        )
        for track in tracks
    ]


def get_song(session: Session, song_id: str, media_base_url: str) -> SongDetail:
    try:
        track = session.get(Track, song_id)
        version = None
        if track is not None and track.status == "published":
            version = session.scalar(
                select(LyricVersion).where(LyricVersion.track_id == song_id).order_by(LyricVersion.id.desc())
            )
    except (OperationalError, ProgrammingError) as exc:
        raise database_not_ready() from exc

    if track is None or track.status != "published" or version is None or not track.media_key:
        raise ApiError(404, "song_not_found", "That song is not available.")

    try:
        lines = load_lines(json.loads(version.lines_json))
    except (ValueError, TypeError) as exc:
        raise ApiError(500, "invalid_song", "This song's lyrics could not be read.") from exc

    return SongDetail(
        id=track.id,
        title=track.title,
        artist=track.artist,
        sourceLanguage=track.source_language,
        targetLanguage=track.target_language,
        durationSeconds=track.duration_seconds,
        status="published",
        audioUrl=f"{media_base_url.rstrip('/')}/{Path(track.media_key).name}",
        contentVersion=version.content_version,
        lines=lines,
    )


def database_not_ready() -> ApiError:
    return ApiError(503, "database_unavailable", "The song database is not ready. Run alembic upgrade head.")


def load_lines(raw_lines: object) -> list[LyricLine]:
    if not isinstance(raw_lines, list):
        raise ValueError("lyric lines must be a list")
    lines: list[LyricLine] = []
    for raw in raw_lines:
        if isinstance(raw, dict):
            raw = {key: value for key, value in raw.items() if key not in TIMING_FIELDS}
        lines.append(LyricLine.model_validate(raw))
    return lines


def dump_lines(lines: list[LyricLine]) -> str:
    return json.dumps([line.model_dump(mode="json") for line in lines], ensure_ascii=False)


def content_hash(lines_json: str) -> str:
    return hashlib.sha256(lines_json.encode("utf-8")).hexdigest()
