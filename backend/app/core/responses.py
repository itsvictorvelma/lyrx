"""Map failures onto the shared error response."""

import logging

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException
from starlette.requests import Request

from app.contracts import ErrorDetail, ErrorResponse
from app.core.context import current_request_id
from app.errors import DomainError

logger = logging.getLogger(__name__)

STATUS_CODES = {
    "invalid_metadata": 400,
    "wrong_filename": 400,
    "invalid_audio": 400,
    "invalid_text": 400,
    "line_count_mismatch": 400,
    "partial_blank_row": 400,
    "empty_song": 400,
    "song_conflict": 409,
    "song_not_found": 404,
    "not_found": 404,
    "file_too_large": 413,
    "validation_error": 422,
    "invalid_song": 500,
    "internal_error": 500,
    "database_unavailable": 503,
}

_LOCATION_PREFIXES = {"body", "query", "header", "cookie", "path"}


def error_response(
    status_code: int,
    code: str,
    message: str,
    request: Request,
    details: list[ErrorDetail] | None = None,
) -> JSONResponse:
    request_id = current_request_id(request)
    payload = ErrorResponse(code=code, message=message, details=details, requestId=request_id)
    response = JSONResponse(status_code=status_code, content=payload.model_dump(exclude_none=True))
    response.headers["X-Request-ID"] = request_id
    return response


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(DomainError, _domain_error)
    app.add_exception_handler(RequestValidationError, _validation_error)
    app.add_exception_handler(HTTPException, _http_error)


async def guard_unexpected(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as exc:
        logger.error(
            "request failed",
            extra={"request_id": current_request_id(request), "error_type": type(exc).__name__},
        )
        return error_response(500, "internal_error", "The request failed.", request)


def _domain_error(request: Request, exc: Exception) -> JSONResponse:
    error = exc if isinstance(exc, DomainError) else DomainError("internal_error", "The request failed.")
    status_code = STATUS_CODES.get(error.code, 500)
    return error_response(status_code, error.code, error.message, request, error.details)


def _validation_error(request: Request, exc: Exception) -> JSONResponse:
    details: list[ErrorDetail] = []
    if isinstance(exc, RequestValidationError):
        for item in exc.errors():
            parts = [str(part) for part in item.get("loc", ()) if str(part) not in _LOCATION_PREFIXES]
            field = ".".join(parts)
            if field:
                details.append(ErrorDetail(field=field))
    return error_response(
        STATUS_CODES["validation_error"],
        "validation_error",
        "The request is invalid.",
        request,
        details or None,
    )


def _http_error(request: Request, exc: Exception) -> JSONResponse:
    status_code = exc.status_code if isinstance(exc, HTTPException) else 500
    if status_code == 404:
        return error_response(404, "not_found", "That page is not available.", request)
    return error_response(status_code, "request_failed", "The request failed.", request)
