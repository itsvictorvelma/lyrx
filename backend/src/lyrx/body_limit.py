"""Refuses a request body over `MAX_BODY_BYTES` before anything parses it (spec 003 AC-65)."""

from typing import Literal

from starlette.datastructures import Headers
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from lyrx import config
from lyrx.errors import ApiError, error_response

BodyRefusal = Literal["too_large", "disconnected"]


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
            too_large = error_response(ApiError("not_lyrics"))
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
