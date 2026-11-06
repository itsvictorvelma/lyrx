"""Ask Groq for a lyric draft. This route does not save the song."""

from fastapi import APIRouter, Depends

from app.contracts import GenerationRequest, GenerationResponse
from app.core.deps import get_generation_service
from app.generation.service import GenerationService

router = APIRouter()


@router.post("/api/generations", response_model=GenerationResponse)
def create_generation(
    request: GenerationRequest,
    service: GenerationService = Depends(get_generation_service),
) -> GenerationResponse:
    return service.generate(request.message, request.draft)
