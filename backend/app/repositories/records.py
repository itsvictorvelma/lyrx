"""Song values passed between the repository and the services.

These are ordinary data. They are not database rows.
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class TrackRecord:
    id: str
    title: str
    artist: str
    source_language: str
    target_language: str
    duration_seconds: float | None
    status: str
    media_key: str | None
    media_checksum: str | None


@dataclass(frozen=True)
class LyricVersionRecord:
    content_version: str
    lines_json: str


@dataclass(frozen=True)
class TrackWrite:
    id: str
    title: str
    artist: str
    source_language: str
    target_language: str
    duration_seconds: float
    status: str
    media_key: str
    media_checksum: str
    created_at: datetime


@dataclass(frozen=True)
class VersionWrite:
    track_id: str
    source_language: str
    target_language: str
    content_version: str
    schema_version: int
    lines_json: str
    status: str
    created_at: datetime
