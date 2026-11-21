"""Catches any unexpected exception so none escapes the app; answers it with `internal_error`."""

import logging

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from subbed.errors import ApiError, error_response

logger = logging.getLogger(__name__)


class CrashGuard:
    """The outermost of the app's own ASGI layers.

    uvicorn logs an exception that escapes the app with its message and traceback, and
    either can hold the lyrics, Claude's reply, or a file path. So the exception stops
    here: only its class name is logged, and the caller gets the one error shape if no
    response has started yet.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        response_started = False

        async def send_and_track(message: Message) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self.app(scope, receive, send_and_track)
        except Exception as error:
            logger.error("unexpected_error exception=%s", type(error).__name__)
            if not response_started:
                await error_response(ApiError("internal_error"))(scope, receive, send)
