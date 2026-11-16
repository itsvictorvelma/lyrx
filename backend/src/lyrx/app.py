"""Builds the FastAPI app: the Host check, the body size cap, the error handlers, and the route."""

from collections.abc import Awaitable, Callable, Mapping
from typing import Literal, cast

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.datastructures import Headers
from starlette.exceptions import HTTPException
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from lyrx import config
from lyrx.errors import ApiError, ErrorCode, size_limit_details
from lyrx.four_versions import make_four_versions
from lyrx.schemas import ErrorResponse, VersionsRequest

VERSIONS_PATH = "/api/versions"

ROUTING_ERROR_CODES: dict[int, ErrorCode] = {404: "not_found", 405: "method_not_allowed"}
FIRST_SERVER_ERROR_STATUS = 500

BodyRefusal = Literal["too_large", "disconnected"]


def error_response(error: ApiError, headers: Mapping[str, str] | None = None) -> JSONResponse:
    body = ErrorResponse(code=error.code, message=error.message, details=error.details)
    return JSONResponse(
        status_code=error.status, content=body.model_dump(exclude_none=True), headers=headers
    )


def host_name(host_header: str) -> str:
    return host_header.partition(":")[0]


async def check_host(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    # Exact, case-sensitive match on purpose: anything unexpected is refused (fails closed).
    if host_name(request.headers.get("host", "")) not in config.ALLOWED_HOST_NAMES:
        return error_response(ApiError("host_not_allowed"))
    return await call_next(request)


class BodySizeLimit:
    """Refuses a body over `MAX_BODY_BYTES` before FastAPI parses it.

    An accepted body is replayed to the app. A client that disconnects mid-body
    never reaches the app, so a cut-off body can never start any work.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        body = await read_capped_body(scope, receive)
        if body == "disconnected":
            return
        if body == "too_large":
            too_large = error_response(ApiError("input_too_large", details=size_limit_details()))
            await too_large(scope, receive, send)
            return
        await self.app(scope, replay_body(body, receive), send)


async def read_capped_body(scope: Scope, receive: Receive) -> bytes | BodyRefusal:
    """The whole body, or why it was refused.

    Checks `Content-Length` when sent, and counts the bytes actually read, so a missing
    or false header cannot get past the cap.
    """
    content_length = Headers(scope=scope).get("content-length", "")
    if content_length.isdecimal() and int(content_length) > config.MAX_BODY_BYTES:
        return "too_large"
    body = b""
    while True:
        message = await receive()
        if message["type"] == "http.disconnect":
            return "disconnected"
        chunk: bytes = message.get("body", b"")
        body += chunk
        if len(body) > config.MAX_BODY_BYTES:
            return "too_large"
        if not message.get("more_body", False):
            return body


def replay_body(body: bytes, receive: Receive) -> Receive:
    """A `receive` that hands the app the already-read body once, then the real channel."""
    replayed = False

    async def receive_replayed() -> Message:
        nonlocal replayed
        if replayed:
            return await receive()
        replayed = True
        return {"type": "http.request", "body": body, "more_body": False}

    return receive_replayed


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


async def handle_unexpected_error(request: Request, error: Exception) -> JSONResponse:
    return error_response(ApiError("internal_error"))


def create_versions(body: VersionsRequest, request: Request) -> None:
    make_four_versions(body.lyrics, request.app.state.claude_client)


def create_app(claude_client: object | None = None) -> FastAPI:
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    app.state.claude_client = claude_client
    # The last middleware added runs first: the Host check, then the body size cap.
    app.add_middleware(BodySizeLimit)
    app.middleware("http")(check_host)
    app.add_exception_handler(ApiError, handle_api_error)
    app.add_exception_handler(HTTPException, handle_http_error)
    app.add_exception_handler(RequestValidationError, handle_invalid_request)
    app.add_exception_handler(Exception, handle_unexpected_error)
    app.add_api_route(VERSIONS_PATH, create_versions, methods=["POST"])
    return app
