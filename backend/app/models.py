"""Song storage tables.

There are two tables: tracks and lyric_versions.
Lyric text is stored as JSON text.
There is no timing column.
"""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

STATUS_CHECK = "status IN ('draft', 'published')"


class Track(Base):
    __tablename__ = "tracks"
    __table_args__ = (CheckConstraint(STATUS_CHECK, name="ck_tracks_status"),)

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    title: Mapped[str] = mapped_column(String(300))
    artist: Mapped[str] = mapped_column(String(300))
    source_language: Mapped[str] = mapped_column(String(16))
    target_language: Mapped[str] = mapped_column(String(16))
    duration_seconds: Mapped[float | None] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(32), server_default="draft", index=True)
    media_key: Mapped[str | None] = mapped_column(String(255))
    media_checksum: Mapped[str | None] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class LyricVersion(Base):
    __tablename__ = "lyric_versions"
    __table_args__ = (
        UniqueConstraint("track_id", "content_version", name="uq_lyric_versions_track_content"),
        CheckConstraint(STATUS_CHECK, name="ck_lyric_versions_status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    track_id: Mapped[str] = mapped_column(ForeignKey("tracks.id"), index=True)
    source_language: Mapped[str] = mapped_column(String(16))
    target_language: Mapped[str] = mapped_column(String(16))
    content_version: Mapped[str] = mapped_column(String(64))
    schema_version: Mapped[int] = mapped_column(Integer, server_default="1")
    lines_json: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), server_default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
