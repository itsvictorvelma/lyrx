"""Read published songs."""

import json
import logging
from pathlib import Path
from typing import Protocol

from app.contracts import LyricLine, SongDetail, SongSummary
from app.core.context import request_id_var
from app.errors import DomainError
from app.lyrics import load_lines
from app.repositories.protocols import SongRepository
from app.repositories.records import LyricVersionRecord, TrackRecord

logger = logging.getLogger(__name__)


class SongReader(Protocol):
    def get_song(self, song_id: str, media_base_url: str) -> SongDetail: ...


class SongService:
    def __init__(self, repo: SongRepository) -> None:
        self._repo = repo

    def list_songs(self) -> list[SongSummary]:
        return [_summary(track) for track in self._repo.list_published()]

    def get_song(self, song_id: str, media_base_url: str) -> SongDetail:
        found = self._repo.published_song(song_id)
        if found is None or not found[0].media_key:
            raise DomainError("song_not_found", "That song is not available.")
        track, version = found
        try:
            lines = load_lines(json.loads(version.lines_json))
            return _detail(track, version, lines, media_base_url)
        except (ValueError, TypeError) as exc:
            logger.warning(
                "stored lyrics could not be read",
                extra={
                    "song_id": song_id,
                    "content_version": version.content_version,
                    "request_id": request_id_var.get(),
                },
            )
            raise DomainError("invalid_song", "This song's lyrics could not be read.") from exc


def _summary(track: TrackRecord) -> SongSummary:
    return SongSummary(
        id=track.id,
        title=track.title,
        artist=track.artist,
        sourceLanguage=track.source_language,
        targetLanguage=track.target_language,
        durationSeconds=track.duration_seconds,
        status="published",
    )


def _detail(
    track: TrackRecord,
    version: LyricVersionRecord,
    lines: list[LyricLine],
    media_base_url: str,
) -> SongDetail:
    media_name = Path(track.media_key or "").name
    return SongDetail(
        id=track.id,
        title=track.title,
        artist=track.artist,
        sourceLanguage=track.source_language,
        targetLanguage=track.target_language,
        durationSeconds=track.duration_seconds,
        status="published",
        audioUrl=f"{media_base_url.rstrip('/')}/{media_name}",
        contentVersion=version.content_version,
        lines=lines,
    )
