"""Fill missing hiragana for one saved song.

From backend/: uv run python scripts/fill_hiragana.py <song-id>

One Groq completion reads the kanji. A bad reply is not saved and is not tried again.
"""

import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import get_settings
from app.contracts import LyricDraft, LyricLine
from app.database import open_database
from app.errors import DomainError
from app.generation.groq import SwytchcodeGroq
from app.generation.service import GenerationService
from app.lyrics import SCHEMA_VERSION, content_hash, dump_lines, hiragana_for_lines
from app.repositories.records import TrackWrite, VersionWrite
from app.repositories.songs import SqlAlchemySongRepository
from app.services.songs import SongService


def main() -> None:
    if len(sys.argv) not in {2, 3} or (len(sys.argv) == 3 and sys.argv[2] != "--replace"):
        raise SystemExit("usage: uv run python scripts/fill_hiragana.py <song-id> [--replace]")
    song_id = sys.argv[1]
    replace = len(sys.argv) == 3
    settings = get_settings()
    _engine, sessions = open_database(settings.database_url)
    session = sessions()
    try:
        repository = SqlAlchemySongRepository(session)
        detail = SongService(repository).get_song(song_id, settings.public_media_base_url)
        if not replace and all(line.readingHiragana.strip() for line in detail.lines):
            print(f"{song_id} already has hiragana on {len(detail.lines)} lines")
            return
        readings = _ask(detail.title, detail.artist, detail.lines, settings.groq_model)
        _save(repository, song_id, readings)
        print(f"{song_id} hiragana saved for {len(readings)} lines")
    finally:
        session.close()


def _ask(title: str, artist: str, lines: list[LyricLine], model: str) -> list[str]:
    service = GenerationService(SwytchcodeGroq(), model)
    try:
        filled = service.complete_lines(title, artist, [line.originalText for line in lines])
        draft = LyricDraft(title=title, artist=artist, lines=filled)
        return hiragana_for_lines(lines, draft)
    except DomainError as exc:
        raise SystemExit(exc.message) from exc


def _save(repository: SqlAlchemySongRepository, song_id: str, readings: list[str]) -> None:
    track = repository.get_track(song_id)
    if track is None or repository.published_song(song_id) is None:
        raise SystemExit("That song is not available.")
    stored = SongService(repository).get_song(song_id, "http://localhost")
    lines = [
        line.model_copy(update={"readingHiragana": reading})
        for line, reading in zip(stored.lines, readings, strict=True)
    ]
    lines_json = dump_lines(lines)
    now = datetime.now(UTC)
    repository.save_song(
        TrackWrite(
            id=track.id,
            title=track.title,
            artist=track.artist,
            source_language=track.source_language,
            target_language=track.target_language,
            duration_seconds=track.duration_seconds,
            status=track.status,
            media_key=track.media_key,
            media_checksum=track.media_checksum,
            created_at=now,
        ),
        VersionWrite(
            track_id=song_id,
            source_language=track.source_language,
            target_language=track.target_language,
            content_version=content_hash(lines_json),
            schema_version=SCHEMA_VERSION,
            lines_json=lines_json,
            status=track.status,
            created_at=now,
        ),
    )


if __name__ == "__main__":
    main()
