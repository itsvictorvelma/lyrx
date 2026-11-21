"""Builds the FastAPI app: its ASGI layers, the error handlers, the routes, and the built page."""

import pathlib
import sqlite3
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from http import HTTPStatus
from typing import Annotated, cast

import httpx2
from fastapi import FastAPI, Path, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from starlette.exceptions import HTTPException

from subbed import config, database, library
from subbed.accounts.routes import add_account_routes
from subbed.accounts.sessions import require_user, signed_in_user
from subbed.accounts.users import User
from subbed.errors import ApiError, ErrorCode, error_response
from subbed.lyrics.lrclib import make_lrclib_client
from subbed.lyrics.search import search_songs
from subbed.rate_limits import count_if_allowed, new_song_limits, peer_address
from subbed.schemas import (
    Playback,
    RecentSongsResponse,
    SavedSongsResponse,
    SongSearchRequest,
    SongSearchResponse,
    SongVersionsRequest,
    SongVersionsResponse,
)
from subbed.server.body_limit import BodySizeLimit
from subbed.server.crash_guard import CrashGuard
from subbed.server.host_check import HostCheck
from subbed.server.origin_check import OriginCheck
from subbed.server.request_log import RequestLog, logged_request
from subbed.song import fill_missing_lines, missing_lines, open_song
from subbed.translation.chain import ready_translators
from subbed.translation.gemini import make_gemini_client
from subbed.translation.groq import make_groq_client

SONG_SEARCH_PATH = "/api/song-search"
SONG_VERSIONS_PATH = "/api/song-versions"
SAVED_SONGS_PATH = "/api/songs"
SAVED_SONG_PATH = "/api/songs/{song_id}/saved"
PLAYBACK_PATH = "/api/songs/{song_id}/playback"
RECENT_SONGS_PATH = "/api/recent-songs"
HEALTH_PATH = "/api/health"
API_PREFIX = "/api/"
PAGE_METHODS = frozenset({"GET", "HEAD"})

ROUTING_ERROR_CODES: dict[int, ErrorCode] = {404: "not_found", 405: "method_not_allowed"}
FIRST_SERVER_ERROR_STATUS = 500


async def handle_api_error(request: Request, error: Exception) -> JSONResponse:
    return error_response(cast(ApiError, error))


async def handle_http_error(request: Request, error: Exception) -> Response:
    """404 and 405 keep their meaning; other client errors are invalid_request.

    When the server has the built page, a missed page address (not `/api`) gets the page.
    """
    http_error = cast(HTTPException, error)
    status = http_error.status_code
    page_dir = config.PAGE_DIR
    if status == HTTPStatus.NOT_FOUND and page_dir is not None and is_page_request(request):
        return page_response(page_dir, request.url.path)
    if status >= FIRST_SERVER_ERROR_STATUS:
        return error_response(ApiError("internal_error"))
    code = ROUTING_ERROR_CODES.get(status, "invalid_request")
    return error_response(ApiError(code), headers=http_error.headers)


def is_page_request(request: Request) -> bool:
    """A GET or HEAD for anything outside `/api`."""
    return request.method in PAGE_METHODS and not (request.url.path + "/").startswith(API_PREFIX)


def page_response(page_dir: pathlib.Path, path: str) -> FileResponse:
    """The file at `path` when it is inside `page_dir`, else `index.html` so the page's own
    routing (such as `/song/5`) takes over in the browser."""
    relative = path.lstrip("/")
    file = page_file(page_dir, relative)
    if file is None:
        index = page_dir / "index.html"
        return FileResponse(index, headers={"Cache-Control": config.PAGE_INDEX_CACHE_CONTROL})
    cache = (
        config.PAGE_ASSET_CACHE_CONTROL
        if relative.startswith(config.PAGE_ASSETS_PREFIX)
        else config.PAGE_INDEX_CACHE_CONTROL
    )
    return FileResponse(file, headers={"Cache-Control": cache})


def page_file(page_dir: pathlib.Path, relative: str) -> pathlib.Path | None:
    """The existing file `relative` names, or None when there is none or it would leave the
    folder (`..`, a link pointing out, a null byte)."""
    if not relative:
        return None
    try:
        file = (page_dir / relative).resolve()
        if file.is_relative_to(page_dir) and file.is_file():
            return file
    except (OSError, ValueError):
        pass
    return None


async def handle_invalid_request(request: Request, error: Exception) -> JSONResponse:
    return error_response(ApiError("invalid_request"))


# The routes are sync `def`s on purpose: FastAPI runs them in its threadpool, so the
# blocking HTTP calls and the database never block the event loop.


def find_songs(body: SongSearchRequest, request: Request) -> SongSearchResponse:
    """Search: a short ranked list of songs, without lyrics."""
    with logged_request(SONG_SEARCH_PATH) as log:
        user = signed_in_user(request)
        user_id = None if user is None else user.id
        results = search_songs(body.query, request.app.state.lrclib_client, user_id)
        log.add("results", len(results))
        return SongSearchResponse(results=results)


def get_song_versions(body: SongVersionsRequest, request: Request) -> SongVersionsResponse:
    """Open a song for anyone: from the cache (missing lines asked again), else LRCLIB and the
    translators within the daily caps. A signed-in person also gets their saved mark and video."""
    with logged_request(SONG_VERSIONS_PATH) as log:
        log.add("lrclib_id", body.id)
        user = signed_in_user(request)
        cached = library.find_song(body.id)
        log.add("from_library", "true" if cached else "false")
        if cached is not None:
            reply = refill_quietly(cached, request, log).model_copy(update={"from_library": True})
        else:
            reply = translate_new_song(body.id, user, request, log)
        return reply if user is None else library.with_library_entry(reply, user.id)


def translate_new_song(
    song_id: int, user: User | None, request: Request, log: RequestLog
) -> SongVersionsResponse:
    """A song not in the cache: counted toward the daily caps first, so failures count too."""
    limits = new_song_limits(None if user is None else user.id, peer_address(request))
    if not count_if_allowed(*limits):
        raise ApiError("daily_limit")
    # Keys are read per request, so setting one after start works.
    translators = ready_translators(request.app.state.translator_clients)
    song, lines, versions, translation = open_song(
        song_id, translators, request.app.state.lrclib_client
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


def list_saved_songs(request: Request) -> SavedSongsResponse:
    """The signed-in person's saved songs, most recently opened first, without lines."""
    with logged_request(SAVED_SONGS_PATH) as log:
        user = require_user(request)
        songs = library.list_songs(user.id)
        log.add("songs", len(songs))
        return SavedSongsResponse(songs=songs)


def list_recent_songs(request: Request) -> RecentSongsResponse:
    """The home page row: recently opened cached songs, without lines (spec 021).

    Only the signed-in person's own videos show, never another person's (spec 014).
    """
    with logged_request(RECENT_SONGS_PATH) as log:
        user = signed_in_user(request)
        user_id = None if user is None else user.id
        songs = library.list_recent_songs(config.RECENT_SONGS_SHOWN, user_id)
        log.add("songs", len(songs))
        return RecentSongsResponse(songs=songs)


def save_song(
    song_id: Annotated[int, Path(ge=1, le=config.MAX_SONG_ID)], body: Playback, request: Request
) -> Response:
    """Puts a cached song in the library with its video and nudge: 204, or 404 when not cached."""
    with logged_request(SAVED_SONG_PATH) as log:
        log.add("lrclib_id", song_id)
        user = require_user(request)
        if not library.save_song_to_library(user.id, song_id, body):
            raise ApiError("song_not_found")
        return Response(status_code=HTTPStatus.NO_CONTENT)


def unsave_song(
    song_id: Annotated[int, Path(ge=1, le=config.MAX_SONG_ID)], request: Request
) -> Response:
    """Takes a song out of the library (it stays cached): 204, or 404 when it was not saved."""
    with logged_request(SAVED_SONG_PATH) as log:
        log.add("lrclib_id", song_id)
        user = require_user(request)
        if not library.unsave_song(user.id, song_id):
            raise ApiError("song_not_found")
        return Response(status_code=HTTPStatus.NO_CONTENT)


def save_song_playback(
    song_id: Annotated[int, Path(ge=1, le=config.MAX_SONG_ID)], body: Playback, request: Request
) -> Response:
    """Saves a saved song's YouTube video and sync nudge: 204, or 404 when it is not saved."""
    with logged_request(PLAYBACK_PATH) as log:
        log.add("lrclib_id", song_id)
        user = require_user(request)
        if not library.save_playback(user.id, song_id, body):
            raise ApiError("song_not_found")
        return Response(status_code=HTTPStatus.NO_CONTENT)


def check_health() -> dict[str, str]:
    """For the container's health check: ok after one cheap database read, else 503."""
    try:
        with database.connect() as connection:
            connection.execute("SELECT 1")
    except (sqlite3.Error, OSError):
        raise ApiError("server_unavailable") from None
    return {"status": "ok"}


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
    # The last layer added runs first: the crash guard, the Host check, the Origin check, then
    # the body cap.
    app.add_middleware(BodySizeLimit)
    app.add_middleware(OriginCheck)
    app.add_middleware(HostCheck)
    app.add_middleware(CrashGuard)
    app.add_exception_handler(ApiError, handle_api_error)
    app.add_exception_handler(HTTPException, handle_http_error)
    app.add_exception_handler(RequestValidationError, handle_invalid_request)
    app.add_api_route(SONG_SEARCH_PATH, find_songs, methods=["POST"])
    app.add_api_route(SONG_VERSIONS_PATH, get_song_versions, methods=["POST"])
    app.add_api_route(SAVED_SONGS_PATH, list_saved_songs, methods=["GET"])
    app.add_api_route(RECENT_SONGS_PATH, list_recent_songs, methods=["GET"])
    app.add_api_route(SAVED_SONG_PATH, save_song, methods=["PUT"])
    app.add_api_route(SAVED_SONG_PATH, unsave_song, methods=["DELETE"])
    app.add_api_route(PLAYBACK_PATH, save_song_playback, methods=["PUT"])
    app.add_api_route(HEALTH_PATH, check_health, methods=["GET"])
    add_account_routes(app)
    return app
