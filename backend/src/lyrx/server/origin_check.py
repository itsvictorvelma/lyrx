"""Refuses a request that changes data unless its `Origin` is this site, which blocks CSRF."""

from urllib.parse import urlsplit

from starlette.datastructures import Headers
from starlette.types import ASGIApp, Receive, Scope, Send

from lyrx import config
from lyrx.errors import ApiError, error_response

CHANGING_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
ORIGIN_SCHEMES = frozenset({"http", "https"})


class OriginCheck:
    """A plain ASGI layer: a POST, PUT, PATCH, or DELETE needs an allowed `Origin`."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if (
            scope["type"] == "http"
            and scope["method"] in CHANGING_METHODS
            and not origin_is_allowed(Headers(scope=scope).get("origin", ""))
        ):
            await error_response(ApiError("bad_origin"))(scope, receive, send)
            return
        await self.app(scope, receive, send)


def origin_is_allowed(origin: str) -> bool:
    """A missing, `null`, or unreadable Origin is refused (fails closed)."""
    try:
        parts = urlsplit(origin)
        host = parts.hostname
    except ValueError:
        return False
    return parts.scheme in ORIGIN_SCHEMES and host in config.ALLOWED_HOST_NAMES
