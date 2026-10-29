"""Development-only song import."""

from fastapi import APIRouter, Depends, File, Form, Response, UploadFile

from app.contracts import SongDetail
from app.core.deps import get_import_limit, get_import_service
from app.errors import DomainError
from app.services.imports import ImportRequest, ImportService

IMPORT_PATH = "/api/import"
router = APIRouter()


async def read_import_form(
    title: str = Form(),
    artist: str = Form(),
    sourceLanguage: str = Form(),
    targetLanguage: str = Form(),
    replace: bool = Form(False),
    original: UploadFile = File(),
    pronunciation: UploadFile = File(),
    translation: UploadFile = File(),
    audio: UploadFile = File(),
    limit: int = Depends(get_import_limit),
) -> ImportRequest:
    return ImportRequest(
        title=title,
        artist=artist,
        source_language=sourceLanguage,
        target_language=targetLanguage,
        replace=replace,
        original_name=original.filename or "",
        pronunciation_name=pronunciation.filename or "",
        translation_name=translation.filename or "",
        audio_name=audio.filename or "",
        original=await _read_limited(original, limit),
        pronunciation=await _read_limited(pronunciation, limit),
        translation=await _read_limited(translation, limit),
        audio=await _read_limited(audio, limit),
    )


async def _read_limited(upload: UploadFile, limit: int) -> bytes:
    chunks: list[bytes] = []
    size = 0
    while True:
        chunk = await upload.read(1024 * 1024)
        if not chunk:
            break
        size += len(chunk)
        if size > limit:
            raise DomainError("file_too_large", f"{upload.filename or 'A file'} is larger than the import limit.")
        chunks.append(chunk)
    return b"".join(chunks)


@router.post(IMPORT_PATH, response_model=SongDetail, response_model_exclude_none=True)
async def import_bundle(
    response: Response,
    bundle: ImportRequest = Depends(read_import_form),
    service: ImportService = Depends(get_import_service),
) -> SongDetail:
    result = service.import_song(bundle)
    response.status_code = 201 if result.created else 200
    return result.song
