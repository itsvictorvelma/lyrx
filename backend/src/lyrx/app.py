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
from lyrx.errors import ApiError, ErrorCode, error_response
from lyrx.lyrics.lrclib import make_lrclib_client
from lyrx.lyrics.search import search_songs
from lyrx.schemas import (
    Playback,
    SavedSongsResponse,
    SongSearchRequest,
    SongSearchResponse,
    SongVersionsRequest,
    SongVersionsResponse,
)
from lyrx.server.body_limit import BodySizeLimit
from lyrx.server.crash_guard import CrashGuard
from lyrx.server.host_check import HostCheck
from lyrx.server.request_log import RequestLog, logged_request
from lyrx.song import fill_missing_lines, missing_lines, open_song
from lyrx.translation.chain import ready_translators
from lyrx.translation.gemini import make_gemini_client
from lyrx.translation.groq import make_groq_client

SONG_SEARCH_PATH = "/api/song-search"
SONG_VERSIONS_PATH = "/api/song-versions"
SAVED_SONGS_PATH = "/api/songs"
SAVED_SONG_PATH = "/api/songs/{song_id}/saved"
PLAYBACK_PATH = "/api/songs/{song_id}/playback"

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
# blocking HTTP calls and the database never block the event loop.


def find_songs(body: SongSearchRequest, request: Request) -> SongSearchResponse:
    """Search: a short ranked list of songs, without lyrics."""
    with logged_request(SONG_SEARCH_PATH) as log:
        results = search_songs(body.query, request.app.state.lrclib_client)
        log.add("results", len(results))
        return SongSearchResponse(results=results)


def get_song_versions(body: SongVersionsRequest, request: Request) -> SongVersionsResponse:
    """Open a song: from the cache (missing lines asked again); else LRCLIB, translators, cache."""
    with logged_request(SONG_VERSIONS_PATH) as log:
        log.add("lrclib_id", body.id)
        cached = library.find_song_or_none(body.id)
        log.add("from_library", "true" if cached else "false")
        if cached is not None:
            return refill_quietly(cached, request, log).model_copy(update={"from_library": True})
        # Keys are read per request, so setting one after start works.
        translators = ready_translators(request.app.state.translator_clients)
        song, lines, versions, translation = open_song(
            body.id, translators, request.app.state.lrclib_client
        )
        log.count_lines(lines)
        log.add_translation(translation)
        reply = SongVersionsResponse(song=song, lines=versions)
        cache_quietly(reply, log)
        return reply


def refill_quietly(
    cached: SongVersionsResponse, request: Request, log: RequestLog
) -> SongVersionsResponse:
    """The cached song with its missing lines asked again; any failure returns it as it was."""
    missing = len(missing_lines(cached.lines))
    if missing == 0:
        return cached
    try:
        translators = ready_translators(request.app.state.translator_clients)
        lines, translation = fill_missing_lines(cached.lines, translators)
    except ApiError as error:
        log.add("refill_failed", error.code)
        return cached
    log.add_translation(translation)
    log.add("refilled_lines", missing - translation.missing_lines)
    try:
        library.replace_lines(cached.song.id, lines)
    except sqlite3.Error:
        # The new lines are still shown; they are asked for again on the next open.
        log.add("save_failed", "true")
    return cached.model_copy(update={"lines": lines})


def cache_quietly(reply: SongVersionsResponse, log: RequestLog) -> None:
    """A failed cache write is logged as `save_failed` and never fails the reply."""
    try:
        library.cache_song(reply)
    except sqlite3.Error:
        log.add("save_failed", "true")


def list_saved_songs() -> SavedSongsResponse:
    """The saved songs, most recently opened first, without lines."""
    with logged_request(SAVED_SONGS_PATH) as log:
        songs = library.list_songs()
        log.add("songs", len(songs))
        return SavedSongsResponse(songs=songs)


def save_song(
    song_id: Annotated[int, Path(ge=1, le=config.MAX_SONG_ID)], body: Playback
) -> Response:
    """Puts a cached song in the library with its video and nudge: 204, or 404 when not cached."""
    with logged_request(SAVED_SONG_PATH) as log:
        log.add("lrclib_id", song_id)
        if not library.save_song_to_library(song_id, body):
            raise ApiError("song_not_found")
        return Response(status_code=HTTPStatus.NO_CONTENT)


def unsave_song(song_id: Annotated[int, Path(ge=1, le=config.MAX_SONG_ID)]) -> Response:
    """Takes a song out of the library (it stays cached): 204, or 404 when it was not saved."""
    with logged_request(SAVED_SONG_PATH) as log:
        log.add("lrclib_id", song_id)
        if not library.unsave_song(song_id):
            raise ApiError("song_not_found")
        return Response(status_code=HTTPStatus.NO_CONTENT)


def save_song_playback(
    song_id: Annotated[int, Path(ge=1, le=config.MAX_SONG_ID)], body: Playback
) -> Response:
    """Saves a saved song's YouTube video and sync nudge: 204, or 404 when it is not saved."""
    with logged_request(PLAYBACK_PATH) as log:
        log.add("lrclib_id", song_id)
        if not library.save_playback(song_id, body):
            raise ApiError("song_not_found")
        return Response(status_code=HTTPStatus.NO_CONTENT)


def create_app(
    lrclib_transport: httpx2.BaseTransport | None = None,
    gemini_transport: httpx2.BaseTransport | None = None,
    groq_transport: httpx2.BaseTransport | None = None,
) -> FastAPI:
    """The app; tests pass fake transports so nothing reaches the network."""
    # One long-lived client per outside service, shared by every request and thread and closed
    # only when the app stops: closing a client closes its connection pool.
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
    app.add_api_route(SAVED_SONG_PATH, save_song, methods=["PUT"])
    app.add_api_route(SAVED_SONG_PATH, unsave_song, methods=["DELETE"])
    app.add_api_route(PLAYBACK_PATH, save_song_playback, methods=["PUT"])
    return app
