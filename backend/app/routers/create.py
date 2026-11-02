"""Create a song from a lyric draft and attach one MP3."""

from fastapi import APIRouter, Depends, File, Form, Response, UploadFile

from app.contracts import GenerationRequest, GenerationResponse, LyricDraft, SongDetail
from app.core.deps import get_catalog_service, get_generation_service, get_import_limit
from app.errors import DomainError
from app.services.catalog import CatalogService
from app.services.generation import GenerationService

router = APIRouter()


@router.post("/api/generations", response_model=GenerationResponse)
def create_generation(
    request: GenerationRequest,
    service: GenerationService = Depends(get_generation_service),
) -> GenerationResponse:
    return service.generate(request.message, request.draft)


@router.post("/api/songs", response_model=SongDetail, response_model_exclude_none=True, status_code=201)
def create_song(
    draft: LyricDraft,
    service: CatalogService = Depends(get_catalog_service),
) -> SongDetail:
    return service.save_draft(draft)


@router.post("/api/songs/{song_id}/audio", response_model=SongDetail, response_model_exclude_none=True)
async def attach_audio(
    song_id: str,
    response: Response,
    replace: bool = Form(False),
    audio: UploadFile = File(),
    service: CatalogService = Depends(get_catalog_service),
    limit: int = Depends(get_import_limit),
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
