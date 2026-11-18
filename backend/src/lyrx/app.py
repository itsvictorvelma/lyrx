"""Builds the FastAPI app: its ASGI layers, the error handlers, and the routes."""

import sqlite3
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from http import HTTPStatus
from typing import Annotated, cast

import httpx2
from fastapi import FastAPI, Path, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from lyrx import config, library
from lyrx.body_limit import BodySizeLimit
from lyrx.crash_guard import CrashGuard
from lyrx.errors import ApiError, ErrorCode, error_response
from lyrx.host_check import HostCheck
from lyrx.http_clients import make_gemini_client, make_groq_client, make_lrclib_client
from lyrx.request_log import RequestLog, logged_request
from lyrx.schemas import (
    SavedSongsResponse,
    SongSearchRequest,
    SongSearchResponse,
    SongVersionsRequest,
    SongVersionsResponse,
)
from lyrx.song_search import search_songs
from lyrx.song_versions import open_song
from lyrx.translators import ready_translators

SONG_SEARCH_PATH = "/api/song-search"
SONG_VERSIONS_PATH = "/api/song-versions"
SAVED_SONGS_PATH = "/api/songs"
SAVED_SONG_PATH = "/api/songs/{song_id}"

ROUTING_ERROR_CODES: dict[int, ErrorCode] = {404: "not_found", 405: "method_not_allowed"}
FIRST_SERVER_ERROR_STATUS = 500


async def handle_api_error(request: Request, error: Exception) -> JSONResponse:
    return error_response(cast(ApiError, error))


async def handle_http_error(request: Request, error: Exception) -> JSONResponse:
    """404 and 405 keep their meaning; other client errors are invalid_request."""
    http_error = cast(HTTPException, error)
    status = http_error.status_code
    if status >= FIRST_SERVER_ERROR_STATUS:
        return error_response(ApiError("internal_error"))
    code = ROUTING_ERROR_CODES.get(status, "invalid_request")
    return error_response(ApiError(code), headers=http_error.headers)


async def handle_invalid_request(request: Request, error: Exception) -> JSONResponse:
    return error_response(ApiError("invalid_request"))


# The routes are sync `def`s on purpose: FastAPI runs them in its threadpool, so the
# blocking HTTP calls and the cleanup never block the event loop.


def find_songs(body: SongSearchRequest, request: Request) -> SongSearchResponse:
    """Search: a short ranked list of songs, without lyrics."""
    with logged_request(SONG_SEARCH_PATH) as log:
        results = search_songs(body.query, request.app.state.lrclib_client)
        log.add("results", len(results))
        return SongSearchResponse(results=results)


def get_song_versions(body: SongVersionsRequest, request: Request) -> SongVersionsResponse:
    """Open a song: from the library if saved; otherwise the keys, LRCLIB, translators, save."""
    with logged_request(SONG_VERSIONS_PATH) as log:
        log.add("lrclib_id", body.id)
        saved = library.find_song_or_none(body.id)
        log.add("from_library", "true" if saved else "false")
        if saved is not None:
            return saved.model_copy(update={"from_library": True})
        # Keys are read per request, so setting one after start works.
        translators = ready_translators(request.app.state.translator_clients)
        song, lines, versions, translation = open_song(
            body.id, translators, request.app.state.lrclib_client
        )
        log.count_lines(lines)
        log.add_translation(translation)
        reply = SongVersionsResponse(song=song, lines=versions)
        if translation.missing_lines == 0:
            save_quietly(reply, log)
        return reply


def save_quietly(reply: SongVersionsResponse, log: RequestLog) -> None:
    """A failed save is logged as `save_failed` and never fails the reply."""
    try:
        library.save_song(reply)
    except sqlite3.Error:
        log.add("save_failed", "true")


def list_saved_songs() -> SavedSongsResponse:
    """The saved songs, most recently opened first, without lines."""
    with logged_request(SAVED_SONGS_PATH) as log:
        songs = library.list_songs()
        log.add("songs", len(songs))
        return SavedSongsResponse(songs=songs)


def remove_saved_song(song_id: Annotated[int, Path(ge=1, le=config.MAX_SONG_ID)]) -> Response:
    """Removes one saved song: 204, or 404 when it was not saved."""
    with logged_request(SAVED_SONG_PATH) as log:
        log.add("lrclib_id", song_id)
        if not library.remove_song(song_id):
            raise ApiError("song_not_found")
        return Response(status_code=HTTPStatus.NO_CONTENT)


def create_app(
    lrclib_transport: httpx2.BaseTransport | None = None,
    gemini_transport: httpx2.BaseTransport | None = None,
    groq_transport: httpx2.BaseTransport | None = None,
) -> FastAPI:
    """The app; tests pass fake transports so nothing reaches the network."""
    lrclib_client = make_lrclib_client(lrclib_transport or httpx2.HTTPTransport())
    translator_clients = {
        "gemini": make_gemini_client(gemini_transport or httpx2.HTTPTransport()),
        "groq": make_groq_client(groq_transport or httpx2.HTTPTransport()),
    }

    @asynccontextmanager
    async def close_clients_on_shutdown(app: FastAPI) -> AsyncIterator[None]:
        yield
        lrclib_client.close()
        for client in translator_clients.values():
            client.close()

    app = FastAPI(
        docs_url=None, redoc_url=None, openapi_url=None, lifespan=close_clients_on_shutdown
    )
    app.state.lrclib_client = lrclib_client
    app.state.translator_clients = translator_clients
    # The last layer added runs first: the crash guard, then the Host check, then the body cap.
    app.add_middleware(BodySizeLimit)
    app.add_middleware(HostCheck)
    app.add_middleware(CrashGuard)
    app.add_exception_handler(ApiError, handle_api_error)
    app.add_exception_handler(HTTPException, handle_http_error)
    app.add_exception_handler(RequestValidationError, handle_invalid_request)
    app.add_api_route(SONG_SEARCH_PATH, find_songs, methods=["POST"])
    app.add_api_route(SONG_VERSIONS_PATH, get_song_versions, methods=["POST"])
    app.add_api_route(SAVED_SONGS_PATH, list_saved_songs, methods=["GET"])
    app.add_api_route(SAVED_SONG_PATH, remove_saved_song, methods=["DELETE"])
    return app
