"""Save a generated song and attach one MP3.

Lyric text files are not accepted. The only upload is the audio file.
"""

import hashlib
import re
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from mutagen.mp3 import MP3, HeaderNotFoundError

from app.config import Settings
from app.contracts import LyricDraft, SongDetail
from app.errors import DomainError
from app.lyrics import SCHEMA_VERSION, content_hash, dump_lines, lines_for_song
from app.repositories.protocols import SongRepository
from app.repositories.records import TrackWrite, VersionWrite
from app.services.songs import SongReader

SONG_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class LibraryService:
    def __init__(self, repo: SongRepository, songs: SongReader, settings: Settings) -> None:
        self._repo = repo
        self._songs = songs
        self._settings = settings

    def save_draft(self, draft: LyricDraft) -> SongDetail:
        title = draft.title.strip()
        artist = draft.artist.strip()
        if not title or not artist:
            raise DomainError("invalid_metadata", "Title and artist are required.")
        song_id = fresh_song_id(self._repo, title)
        lines = lines_for_song(song_id, draft)
        lines_json = dump_lines(lines)
        now = datetime.now(UTC)
        self._repo.save_song(
            TrackWrite(
                id=song_id,
                title=title,
                artist=artist,
                source_language="ja",
                target_language="en",
                duration_seconds=None,
                status="published",
                media_key=None,
                media_checksum=None,
                created_at=now,
            ),
            VersionWrite(
                track_id=song_id,
                source_language="ja",
                target_language="en",
                content_version=content_hash(lines_json),
                schema_version=SCHEMA_VERSION,
                lines_json=lines_json,
                status="published",
                created_at=now,
            ),
        )
        return self._songs.get_song(song_id, self._settings.public_media_base_url)

    def attach_audio(self, song_id: str, audio: bytes, replace: bool) -> SongDetail:
        if len(audio) > self._settings.max_audio_bytes:
            raise DomainError("file_too_large", "The audio file is larger than the upload limit.")
        track = self._repo.get_track(song_id)
        if track is None or track.status != "published":
            raise DomainError("song_not_found", "That song is not available.")
        if track.media_key and not replace:
            raise DomainError(
                "song_conflict",
                "This song already has audio. Check replace to update it.",
            )
        staging = Path(self._settings.audio_staging_root)
        staging.mkdir(parents=True, exist_ok=True)
        temporary = staging / f"{uuid4().hex}.mp3"
        temporary.write_bytes(audio)
        try:
            duration, checksum = _audio_file(temporary, audio)
        finally:
            temporary.unlink(missing_ok=True)
        if track.media_checksum == checksum and track.media_key:
            return self._songs.get_song(song_id, self._settings.public_media_base_url)

        media_root = Path(self._settings.media_root)
        media_root.mkdir(parents=True, exist_ok=True)
        media_key = f"{uuid4().hex}.mp3"
        destination = media_root / media_key
        destination.write_bytes(audio)
        previous_key = track.media_key
        try:
            self._repo.save_song(
                TrackWrite(
                    id=track.id,
                    title=track.title,
                    artist=track.artist,
                    source_language=track.source_language,
                    target_language=track.target_language,
                    duration_seconds=duration,
                    status="published",
                    media_key=media_key,
                    media_checksum=checksum,
                    created_at=datetime.now(UTC),
                ),
                None,
            )
        except Exception:
            destination.unlink(missing_ok=True)
            raise
        if previous_key and previous_key != media_key:
            (media_root / Path(previous_key).name).unlink(missing_ok=True)
        return self._songs.get_song(song_id, self._settings.public_media_base_url)


def song_id_from_title(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.casefold()).strip("-")[:80].strip("-")
    if SONG_ID.fullmatch(slug):
        return slug
    return f"song-{hashlib.sha256(title.casefold().encode()).hexdigest()[:8]}"


def fresh_song_id(repo: SongRepository, title: str) -> str:
    base = song_id_from_title(title)
    if repo.get_track(base) is None:
        return base
    suffix = hashlib.sha256(f"{title}:{uuid4().hex}".encode()).hexdigest()[:6]
    return f"{base}-{suffix}"[:80]


def _audio_file(path: Path, audio: bytes) -> tuple[float, str]:
    try:
        duration = float(MP3(path).info.length)
    except HeaderNotFoundError as exc:
        raise DomainError("invalid_audio", "The audio file is not a readable MP3.") from exc
    if duration <= 0:
        raise DomainError("invalid_audio", "The audio file does not have a duration.")
    return duration, hashlib.sha256(audio).hexdigest()
