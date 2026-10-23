"""Read songs stored by the importer, and save line start times."""

import hashlib
import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.orm import Session

from app.align import assign_line_starts
from app.config import Settings
from app.contracts import LineTimeUpdate, LyricLine, SongDetail, SongSummary
from app.errors import ApiError
from app.models import LyricVersion, Track
from app.transcribe import ScanUnavailable, transcribe_words


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
        raw_lines = json.loads(version.lines_json)
        lines = [LyricLine.model_validate(line) for line in raw_lines]
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


def dump_lines(lines: list[LyricLine]) -> str:
    return json.dumps([line.model_dump(mode="json", exclude_none=True) for line in lines], ensure_ascii=False)


def content_hash(lines_json: str) -> str:
    return hashlib.sha256(lines_json.encode("utf-8")).hexdigest()


def replace_line_starts(
    session: Session,
    song_id: str,
    updates: list[LineTimeUpdate],
    media_base_url: str,
) -> SongDetail:
    track, version, lines = _published_lines(session, song_id)
    by_index = {update.index: update.startSeconds for update in updates}
    if any(index >= len(lines) for index in by_index):
        raise ApiError(400, "invalid_line", "One of those lines is not in this song.")
    limit = (track.duration_seconds if track.duration_seconds is not None else 6 * 60 * 60) + 1
    if any(start > limit for start in by_index.values()):
        raise ApiError(400, "invalid_line", "That time is past the end of the song.")
    revised = [
        line.model_copy(update={"startSeconds": round(by_index[line.index], 3)}) if line.index in by_index else line
        for line in lines
    ]
    _store_lines(session, version, revised)
    return get_song(session, song_id, media_base_url)


def scan_saved_song(session: Session, settings: Settings, song_id: str) -> SongDetail:
    track, version, lines = _published_lines(session, song_id)
    if not track.media_key:
        raise ApiError(404, "song_not_found", "That song is not available.")
    media = Path(settings.media_root) / Path(track.media_key).name
    if not media.is_file():
        raise ApiError(404, "song_not_found", "That song's audio is not available.")
    try:
        words = transcribe_words(media, track.source_language, settings.align_model)
    except ScanUnavailable as exc:
        raise ApiError(503, "scan_unavailable", str(exc)) from exc
    starts = assign_line_starts([line.originalText for line in lines], words)
    revised = [
        line.model_copy(update={"startSeconds": start}) if start is not None else line.model_copy(update={"startSeconds": None})
        for line, start in zip(lines, starts, strict=True)
    ]
    _store_lines(session, version, revised)
    return get_song(session, song_id, settings.public_media_base_url)


def _published_lines(session: Session, song_id: str) -> tuple[Track, LyricVersion, list[LyricLine]]:
    try:
        track = session.get(Track, song_id)
        version = None
        if track is not None and track.status == "published":
            version = session.scalar(
                select(LyricVersion).where(LyricVersion.track_id == song_id).order_by(LyricVersion.id.desc())
            )
    except (OperationalError, ProgrammingError) as exc:
        raise database_not_ready() from exc
    if track is None or track.status != "published" or version is None:
        raise ApiError(404, "song_not_found", "That song is not available.")
    try:
        raw_lines = json.loads(version.lines_json)
        lines = [LyricLine.model_validate(line) for line in raw_lines]
    except (ValueError, TypeError) as exc:
        raise ApiError(500, "invalid_song", "This song's lyrics could not be read.") from exc
    return track, version, lines


def _store_lines(session: Session, version: LyricVersion, lines: list[LyricLine]) -> None:
    payload = dump_lines(lines)
    version.lines_json = payload
    version.content_version = content_hash(payload)
    session.commit()
