"""Build the database session and the services each route calls."""

from collections.abc import Iterator

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.config import Settings
from app.groq_client import SwytchcodeGroq
from app.repositories.songs import SqlAlchemySongRepository
from app.services.catalog import CatalogService
from app.services.generation import GenerationService
from app.services.songs import SongService


def get_session(request: Request) -> Iterator[Session]:
    session = request.app.state.sessions()
    try:
        yield session
    finally:
        session.close()


def get_song_service(session: Session = Depends(get_session)) -> SongService:
    return SongService(SqlAlchemySongRepository(session))


def get_catalog_service(request: Request, session: Session = Depends(get_session)) -> CatalogService:
    settings: Settings = request.app.state.settings
    repository = SqlAlchemySongRepository(session)
    return CatalogService(repository, SongService(repository), settings)


def get_generation_service(request: Request) -> GenerationService:
    settings: Settings = request.app.state.settings
    return GenerationService(SwytchcodeGroq(), settings.groq_model)


def get_media_base_url(request: Request) -> str:
    settings: Settings = request.app.state.settings
    return settings.public_media_base_url


def get_import_limit(request: Request) -> int:
    settings: Settings = request.app.state.settings
    return settings.max_import_bytes
