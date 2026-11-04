"""SQLAlchemy queries for songs.

This is the only application module that queries the song tables.
"""

from sqlalchemy import select
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.orm import Session

from app.errors import DomainError
from app.models import LyricVersion, Track
from app.repositories.records import LyricVersionRecord, TrackRecord, TrackWrite, VersionWrite


def _unavailable() -> DomainError:
    return DomainError("database_unavailable", "The song database is not ready. Run alembic upgrade head.")


def _track_record(track: Track) -> TrackRecord:
    return TrackRecord(
        id=track.id,
        title=track.title,
        artist=track.artist,
        source_language=track.source_language,
        target_language=track.target_language,
        duration_seconds=track.duration_seconds,
        status=track.status,
        media_key=track.media_key,
        media_checksum=track.media_checksum,
    )


def _version_record(version: LyricVersion) -> LyricVersionRecord:
    return LyricVersionRecord(content_version=version.content_version, lines_json=version.lines_json)


class SqlAlchemySongRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_published(self) -> list[TrackRecord]:
        try:
            tracks = self._session.scalars(select(Track).where(Track.status == "published").order_by(Track.title, Track.id))
        except (OperationalError, ProgrammingError) as exc:
            raise _unavailable() from exc
        return [_track_record(track) for track in tracks]

    def published_song(self, song_id: str) -> tuple[TrackRecord, LyricVersionRecord] | None:
        try:
            track = self._session.get(Track, song_id)
            version = None
            if track is not None and track.status == "published":
                version = self._session.scalar(
                    select(LyricVersion).where(LyricVersion.track_id == song_id).order_by(LyricVersion.id.desc())
                )
        except (OperationalError, ProgrammingError) as exc:
            raise _unavailable() from exc
        if track is None or track.status != "published" or version is None:
            return None
        return _track_record(track), _version_record(version)

    def get_track(self, song_id: str) -> TrackRecord | None:
        try:
            track = self._session.get(Track, song_id)
        except (OperationalError, ProgrammingError) as exc:
            raise _unavailable() from exc
        if track is None:
            return None
        return _track_record(track)

    def latest_lines_json(self, song_id: str) -> str | None:
        try:
            version = self._session.scalar(
                select(LyricVersion).where(LyricVersion.track_id == song_id).order_by(LyricVersion.id.desc())
            )
        except (OperationalError, ProgrammingError) as exc:
            raise _unavailable() from exc
        if version is None:
            return None
        return version.lines_json

    def has_content_version(self, song_id: str, content_version: str) -> bool:
        try:
            found = self._session.scalar(
                select(LyricVersion.id).where(
                    LyricVersion.track_id == song_id,
                    LyricVersion.content_version == content_version,
                )
            )
        except (OperationalError, ProgrammingError) as exc:
            raise _unavailable() from exc
        return found is not None

    def save_import(self, track: TrackWrite, version: VersionWrite | None) -> None:
        try:
            stored = self._session.get(Track, track.id)
            if stored is None:
                self._session.add(
                    Track(
                        id=track.id,
                        title=track.title,
                        artist=track.artist,
                        source_language=track.source_language,
                        target_language=track.target_language,
                        duration_seconds=track.duration_seconds,
                        status=track.status,
                        media_key=track.media_key,
                        media_checksum=track.media_checksum,
                        created_at=track.created_at,
                    )
                )
            else:
                stored.title = track.title
                stored.artist = track.artist
                stored.source_language = track.source_language
                stored.target_language = track.target_language
                stored.duration_seconds = track.duration_seconds
                stored.status = track.status
                stored.media_key = track.media_key
                stored.media_checksum = track.media_checksum
            # ponytail: no ORM relationship, so flush the track before the lyric row or the foreign key fails.
            self._session.flush()
            if version is not None:
                self._session.add(
                    LyricVersion(
                        track_id=version.track_id,
                        source_language=version.source_language,
                        target_language=version.target_language,
                        content_version=version.content_version,
                        schema_version=version.schema_version,
                        lines_json=version.lines_json,
                        status=version.status,
                        created_at=version.created_at,
                    )
                )
            self._session.commit()
        except (OperationalError, ProgrammingError) as exc:
            self._session.rollback()
            raise _unavailable() from exc
        except Exception:
            self._session.rollback()
            raise
