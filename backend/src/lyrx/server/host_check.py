"""Refuses any request whose `Host` is not an allowed host name, which blocks DNS rebinding.

The allowed names come from `LYRX_ALLOWED_HOSTS`: locally 127.0.0.1 and localhost, on the
server the domain (spec 020).
"""

from starlette.datastructures import Headers
from starlette.types import ASGIApp, Receive, Scope, Send

from lyrx import config
from lyrx.errors import ApiError, error_response


def host_name(host_header: str) -> str:
    return host_header.partition(":")[0]


class HostCheck:
    """A plain ASGI layer: it answers a foreign Host itself, before the body is read."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and not host_is_allowed(scope):
            await error_response(ApiError("host_not_allowed"))(scope, receive, send)
            return
        await self.app(scope, receive, send)


def host_is_allowed(scope: Scope) -> bool:
    # Exact, case-sensitive match on purpose: anything unexpected is refused (fails closed).
    return host_name(Headers(scope=scope).get("host", "")) in config.ALLOWED_HOST_NAMES
