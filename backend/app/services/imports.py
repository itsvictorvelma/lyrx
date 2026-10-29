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

from app.config import Settings
from app.contracts import LyricLine, SongDetail
from app.errors import DomainError
from app.lyrics import align_lyrics, content_hash, decode_lyric_file, dump_lines
from app.repositories.protocols import SongRepository
from app.repositories.records import TrackRecord, TrackWrite, VersionWrite
from app.services.songs import SongReader

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


@dataclass(frozen=True)
class ImportResult:
    song: SongDetail
    created: bool


class ImportService:
    def __init__(self, repo: SongRepository, songs: SongReader, settings: Settings) -> None:
        self._repo = repo
        self._songs = songs
        self._settings = settings

    def import_song(self, request: ImportRequest) -> ImportResult:
        metadata = _metadata(request)
        _check_names(request)
        _check_size(request, self._settings.max_import_bytes)
        lines = _lines(request, metadata["song_id"])
        staging = Path(self._settings.import_staging_root)
        staging.mkdir(parents=True, exist_ok=True)
        temporary = staging / f"{uuid4().hex}.mp3"
        temporary.write_bytes(request.audio)
        existing: TrackRecord | None = None
        try:
            duration, checksum = _audio_file(temporary, request.audio)
            existing = self._repo.get_track(metadata["song_id"])
            if existing is not None:
                same_audio = existing.media_checksum == checksum
                same_lines = _same_text(self._repo.latest_lines_json(existing.id), lines)
                if same_audio and same_lines:
                    song = self._songs.get_song(existing.id, self._settings.public_media_base_url)
                    return ImportResult(song=song, created=False)
                if not request.replace:
                    raise DomainError(
                        "song_conflict",
                        "A song with this title is already saved with different content. Check replace to update it.",
                    )
        finally:
            temporary.unlink(missing_ok=True)

        lines_json = dump_lines(lines)
        content_version = content_hash(lines_json)
        media_root = Path(self._settings.media_root)
        media_root.mkdir(parents=True, exist_ok=True)
        media_key = f"{uuid4().hex}.mp3"
        destination = media_root / media_key
        destination.write_bytes(request.audio)
        previous_key = existing.media_key if existing is not None else None
        now = datetime.now(UTC)
        try:
            version = None
            if not self._repo.has_content_version(metadata["song_id"], content_version):
                version = VersionWrite(
                    track_id=metadata["song_id"],
                    source_language=metadata["source_language"],
                    target_language=metadata["target_language"],
                    content_version=content_version,
                    schema_version=1,
                    lines_json=lines_json,
                    status="published",
                    created_at=now,
                )
            self._repo.save_import(
                TrackWrite(
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
                ),
                version,
            )
        except Exception:
            destination.unlink(missing_ok=True)
            raise

        if previous_key and previous_key != media_key:
            (media_root / Path(previous_key).name).unlink(missing_ok=True)
        song = self._songs.get_song(metadata["song_id"], self._settings.public_media_base_url)
        return ImportResult(song=song, created=True)


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
        raise DomainError("invalid_metadata", "Title, artist, and both languages are required.")
    if len(source_language) > 16 or len(target_language) > 16:
        raise DomainError("invalid_metadata", "Language codes must be 16 characters or fewer.")
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
        raise DomainError("wrong_filename", f"Use these exact file names: {names}.")


def _check_size(request: ImportRequest, limit: int) -> None:
    for name, data in (
        ("original.txt", request.original),
        ("pronunciation.txt", request.pronunciation),
        ("translation.txt", request.translation),
        ("audio.mp3", request.audio),
    ):
        if len(data) > limit:
            raise DomainError("file_too_large", f"{name} is larger than the import limit.")


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


def _audio_file(path: Path, audio: bytes) -> tuple[float, str]:
    try:
        duration = float(MP3(path).info.length)
    except HeaderNotFoundError as exc:
        raise DomainError("invalid_audio", "audio.mp3 is not a readable MP3.") from exc
    if duration <= 0:
        raise DomainError("invalid_audio", "audio.mp3 does not have a duration.")
    return duration, hashlib.sha256(audio).hexdigest()


def _same_text(lines_json: str | None, lines: list[LyricLine]) -> bool:
    if lines_json is None:
        return False
    return _fingerprint_json(lines_json) == _fingerprint_lines(lines)


def _fingerprint_lines(lines: list[LyricLine]) -> str:
    rows = [[line.originalText, line.pronunciationRomaji, line.translationEnglish] for line in lines]
    return json.dumps(rows, ensure_ascii=False)


def _fingerprint_json(lines_json: str) -> str | None:
    try:
        raw = json.loads(lines_json)
        rows = [[line["originalText"], line["pronunciationRomaji"], line["translationEnglish"]] for line in raw]
    except (TypeError, KeyError, json.JSONDecodeError):
        return None
    return json.dumps(rows, ensure_ascii=False)
