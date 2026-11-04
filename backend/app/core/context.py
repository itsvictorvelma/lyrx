"""Request id shared by logs and error responses."""

import contextvars
import re
from uuid import uuid4

from starlette.requests import Request

request_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar("request_id", default=None)

_REQUEST_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def incoming_request_id(header: str | None) -> str:
    if header and _REQUEST_ID.fullmatch(header):
        return header
    return uuid4().hex


def current_request_id(request: Request) -> str:
    existing = getattr(request.state, "request_id", None)
    if isinstance(existing, str) and existing:
        return existing
    current = request_id_var.get()
    if current:
        return current
    generated = uuid4().hex
    request.state.request_id = generated
    return generated


async def bind_request_id(request: Request, call_next):
    request_id = incoming_request_id(request.headers.get("x-request-id"))
    request.state.request_id = request_id
    token = request_id_var.set(request_id)
    try:
        response = await call_next(request)
    finally:
        request_id_var.reset(token)
    response.headers["X-Request-ID"] = request_id
    return response
