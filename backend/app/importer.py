"""Save a development song bundle.

The four files are original.txt, pronunciation.txt, translation.txt, and audio.mp3.
A successful import is published immediately so the song list can return it.
"""

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from mutagen.mp3 import MP3, HeaderNotFoundError
from sqlalchemy import select
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.orm import Session

from app.config import Settings
from app.contracts import LyricLine, SongDetail
from app.errors import ApiError
from app.lyrics import align_lyrics, decode_lyric_file
from app.models import LyricVersion, Track
from app.songs import database_not_ready, get_song

SONG_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
FILE_NAMES = {
    "original": "original.txt",
    "pronunciation": "pronunciation.txt",
    "translation": "translation.txt",
    "audio": "audio.mp3",
}


@dataclass(frozen=True)
class ImportRequest:
    title: str
    artist: str
    source_language: str
    target_language: str
    replace: bool
    original_name: str
    pronunciation_name: str
    translation_name: str
    audio_name: str
    original: bytes
    pronunciation: bytes
    translation: bytes
    audio: bytes


def import_song(session: Session, settings: Settings, request: ImportRequest) -> tuple[SongDetail, int]:
    metadata = _metadata(request)
    _check_names(request)
    _check_size(request, settings.max_import_bytes)
    lines = _lines(request, metadata["song_id"])
    duration, checksum = _audio(request, Path(settings.import_staging_root))
    lines_json = json.dumps([line.model_dump() for line in lines], ensure_ascii=False)
    content_version = hashlib.sha256(lines_json.encode("utf-8")).hexdigest()

    try:
        existing = session.get(Track, metadata["song_id"])
    except (OperationalError, ProgrammingError) as exc:
        raise database_not_ready() from exc
    if existing is not None:
        same_audio = existing.media_checksum == checksum
        same_lines = _latest_lines(session, existing.id) == lines_json
        if same_audio and same_lines:
            return get_song(session, existing.id, settings.public_media_base_url), 200
        if not request.replace:
            raise ApiError(
                409,
                "song_conflict",
                "A song with this title is already saved with different content. Check replace to update it.",
            )

    media_root = Path(settings.media_root)
    media_root.mkdir(parents=True, exist_ok=True)
    media_key = f"{uuid4().hex}.mp3"
    destination = media_root / media_key
    destination.write_bytes(request.audio)
    previous_key = existing.media_key if existing is not None else None
    now = datetime.now(UTC)

    try:
        if existing is None:
            session.add(
                Track(
                    id=metadata["song_id"],
                    title=metadata["title"],
                    artist=metadata["artist"],
                    source_language=metadata["source_language"],
                    target_language=metadata["target_language"],
                    duration_seconds=duration,
                    status="published",
                    media_key=media_key,
                    media_checksum=checksum,
                    created_at=now,
                )
            )
        else:
            existing.title = metadata["title"]
            existing.artist = metadata["artist"]
            existing.source_language = metadata["source_language"]
            existing.target_language = metadata["target_language"]
            existing.duration_seconds = duration
            existing.status = "published"
            existing.media_key = media_key
            existing.media_checksum = checksum

        already_saved = session.scalar(
            select(LyricVersion).where(
                LyricVersion.track_id == metadata["song_id"],
                LyricVersion.content_version == content_version,
            )
        )
        if already_saved is None:
            session.add(
                LyricVersion(
                    track_id=metadata["song_id"],
                    source_language=metadata["source_language"],
                    target_language=metadata["target_language"],
                    content_version=content_version,
                    schema_version=1,
                    lines_json=lines_json,
                    status="published",
                    created_at=now,
                )
            )
        session.commit()
    except Exception:
        session.rollback()
        destination.unlink(missing_ok=True)
        raise

    if previous_key and previous_key != media_key:
        (media_root / Path(previous_key).name).unlink(missing_ok=True)
    return get_song(session, metadata["song_id"], settings.public_media_base_url), 201


def song_id_from_title(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.casefold()).strip("-")[:80].strip("-")
    if SONG_ID.fullmatch(slug):
        return slug
    return f"song-{hashlib.sha256(title.casefold().encode()).hexdigest()[:8]}"


def _metadata(request: ImportRequest) -> dict[str, str]:
    title = request.title.strip()
    artist = request.artist.strip()
    source_language = request.source_language.strip()
    target_language = request.target_language.strip()
    if not title or not artist or not source_language or not target_language:
        raise ApiError(400, "invalid_metadata", "Title, artist, and both languages are required.")
    if len(source_language) > 16 or len(target_language) > 16:
        raise ApiError(400, "invalid_metadata", "Language codes must be 16 characters or fewer.")
    return {
        "song_id": song_id_from_title(title),
        "title": title,
        "artist": artist,
        "source_language": source_language,
        "target_language": target_language,
    }


def _check_names(request: ImportRequest) -> None:
    actual = {
        "original": request.original_name,
        "pronunciation": request.pronunciation_name,
        "translation": request.translation_name,
        "audio": request.audio_name,
    }
    wrong = [expected for key, expected in FILE_NAMES.items() if actual[key] != expected]
    if wrong:
        names = ", ".join(wrong)
        raise ApiError(400, "wrong_filename", f"Use these exact file names: {names}.")


def _check_size(request: ImportRequest, limit: int) -> None:
    for name, data in (
        ("original.txt", request.original),
        ("pronunciation.txt", request.pronunciation),
        ("translation.txt", request.translation),
        ("audio.mp3", request.audio),
    ):
        if len(data) > limit:
            raise ApiError(413, "file_too_large", f"{name} is larger than the import limit.")


def _lines(request: ImportRequest, song_id: str) -> list[LyricLine]:
    original = decode_lyric_file(request.original, "original.txt")
    pronunciation = decode_lyric_file(request.pronunciation, "pronunciation.txt")
    translation = decode_lyric_file(request.translation, "translation.txt")
    return [
        LyricLine(
            id=f"{song_id}-{index}",
            index=index,
            originalText=original_text,
            pronunciationRomaji=pronunciation_text,
            translationEnglish=translation_text,
        )
        for index, (original_text, pronunciation_text, translation_text) in enumerate(
            align_lyrics(original, pronunciation, translation)
        )
    ]


def _audio(request: ImportRequest, staging_root: Path) -> tuple[float, str]:
    staging_root.mkdir(parents=True, exist_ok=True)
    temporary = staging_root / f"{uuid4().hex}.mp3"
    temporary.write_bytes(request.audio)
    try:
        try:
            duration = float(MP3(temporary).info.length)
        except HeaderNotFoundError as exc:
            raise ApiError(400, "invalid_audio", "audio.mp3 is not a readable MP3.") from exc
    finally:
        temporary.unlink(missing_ok=True)
    if duration <= 0:
        raise ApiError(400, "invalid_audio", "audio.mp3 does not have a duration.")
    return duration, hashlib.sha256(request.audio).hexdigest()


def _latest_lines(session: Session, song_id: str) -> str | None:
    version = session.scalar(select(LyricVersion).where(LyricVersion.track_id == song_id).order_by(LyricVersion.id.desc()))
    if version is None:
        return None
    return version.lines_json
