"""Builds the FastAPI app: its ASGI layers, the error handlers, and the route."""

from typing import cast

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from lyrx.body_limit import BodySizeLimit
from lyrx.crash_guard import CrashGuard
from lyrx.errors import ApiError, ErrorCode, error_response
from lyrx.four_versions import make_four_versions
from lyrx.host_check import HostCheck
from lyrx.lines import count_characters, read_paste
from lyrx.request_log import logged_request
from lyrx.schemas import VersionsRequest, VersionsResponse

VERSIONS_PATH = "/api/versions"

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


def create_versions(body: VersionsRequest, request: Request) -> VersionsResponse:
    """Reads the paste once, then runs the pipeline inside its one log line."""
    # A sync `def` on purpose: FastAPI runs it in its threadpool, so the CPU-bound
    # reading checks never block the event loop.
    paste = read_paste(body.lyrics)
    characters = count_characters(paste.text)
    with logged_request(lines=len(paste.lines), characters=characters) as log:
        response, usage = make_four_versions(paste, request.app.state.claude_client)
        log.add_tokens(usage)
        return response


def create_app(claude_client: object | None = None) -> FastAPI:
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    app.state.claude_client = claude_client
    # The last layer added runs first: the crash guard, then the Host check, then the body cap.
    app.add_middleware(BodySizeLimit)
    app.add_middleware(HostCheck)
    app.add_middleware(CrashGuard)
    app.add_exception_handler(ApiError, handle_api_error)
    app.add_exception_handler(HTTPException, handle_http_error)
    app.add_exception_handler(RequestValidationError, handle_invalid_request)
    app.add_api_route(VERSIONS_PATH, create_versions, methods=["POST"])
    return app
