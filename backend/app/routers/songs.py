"""Published song reads."""

from fastapi import APIRouter, Depends

from app.contracts import SongDetail, SongSummary
from app.core.deps import get_media_base_url, get_song_service
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
