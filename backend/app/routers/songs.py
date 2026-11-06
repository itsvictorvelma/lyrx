"""Saved songs: list, read, save, and attach one MP3."""

from fastapi import APIRouter, Depends, File, Form, Response, UploadFile

from app.contracts import LyricDraft, SongDetail, SongSummary
from app.core.deps import get_audio_limit, get_library_service, get_media_base_url, get_song_service
from app.errors import DomainError
from app.services.library import LibraryService
from app.services.songs import SongService

router = APIRouter()


@router.get("/api/songs", response_model=list[SongSummary])
def read_songs(service: SongService = Depends(get_song_service)) -> list[SongSummary]:
    return service.list_songs()


@router.get("/api/songs/{song_id}", response_model=SongDetail, response_model_exclude_none=True)
def read_song(
    song_id: str,
    service: SongService = Depends(get_song_service),
    media_base_url: str = Depends(get_media_base_url),
) -> SongDetail:
    return service.get_song(song_id, media_base_url)


@router.post("/api/songs", response_model=SongDetail, response_model_exclude_none=True, status_code=201)
def create_song(
    draft: LyricDraft,
    service: LibraryService = Depends(get_library_service),
) -> SongDetail:
    return service.save_draft(draft)


@router.post("/api/songs/{song_id}/audio", response_model=SongDetail, response_model_exclude_none=True)
async def attach_audio(
    song_id: str,
    response: Response,
    replace: bool = Form(False),
    audio: UploadFile = File(),
    service: LibraryService = Depends(get_library_service),
    limit: int = Depends(get_audio_limit),
) -> SongDetail:
    saved = service.attach_audio(song_id, await _read_limited(audio, limit), replace)
    response.status_code = 200
    return saved


async def _read_limited(upload: UploadFile, limit: int) -> bytes:
    chunks: list[bytes] = []
    size = 0
    while True:
        chunk = await upload.read(1024 * 1024)
        if not chunk:
            break
        size += len(chunk)
        if size > limit:
            raise DomainError("file_too_large", "The audio file is larger than the upload limit.")
        chunks.append(chunk)
    return b"".join(chunks)
