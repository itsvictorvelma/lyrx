"""Builds the FastAPI app: the Host check, the error handlers, and `POST /api/versions`."""

from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from lyrx import config
from lyrx.errors import ApiError
from lyrx.schemas import ErrorResponse, VersionsRequest

VERSIONS_PATH = "/api/versions"


def error_response(error: ApiError) -> JSONResponse:
    body = ErrorResponse(code=error.code, message=error.message, details=error.details)
    return JSONResponse(status_code=error.status, content=body.model_dump(exclude_none=True))


def host_name(host_header: str) -> str:
    return host_header.partition(":")[0]


async def check_host(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    if host_name(request.headers.get("host", "")) not in config.ALLOWED_HOST_NAMES:
        return error_response(ApiError("host_not_allowed"))
    return await call_next(request)


async def handle_api_error(request: Request, error: Exception) -> JSONResponse:
    assert isinstance(error, ApiError)
    return error_response(error)


async def handle_invalid_request(request: Request, error: Exception) -> JSONResponse:
    return error_response(ApiError("invalid_request"))


async def handle_unexpected_error(request: Request, error: Exception) -> JSONResponse:
    return error_response(ApiError("internal_error"))


def create_versions(request: VersionsRequest) -> None:
    # ponytail: no pipeline yet, so a valid request is an internal_error; T3-T7 replace this.
    raise ApiError("internal_error")


def create_app(claude_client: object | None = None) -> FastAPI:
    app = FastAPI()
    app.state.claude_client = claude_client
    app.middleware("http")(check_host)
    app.add_exception_handler(ApiError, handle_api_error)
    app.add_exception_handler(RequestValidationError, handle_invalid_request)
    app.add_exception_handler(Exception, handle_unexpected_error)
    app.add_api_route(VERSIONS_PATH, create_versions, methods=["POST"])
    return app
