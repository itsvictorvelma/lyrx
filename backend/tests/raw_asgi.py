"""Calls the ASGI app directly with a scripted `receive`, the way a server like uvicorn does."""

import asyncio
import logging

from fastapi import FastAPI
from starlette.types import Message, Scope

from lyrx.app import SONG_SEARCH_PATH

ALLOWED_HOST_HEADER = (b"host", b"127.0.0.1:8000")
JSON_CONTENT_TYPE_HEADER = (b"content-type", b"application/json")
# uvicorn logs an exception that escapes the app to this logger, with its traceback.
UVICORN_ERROR_LOGGER = "uvicorn.error"


def post_scope(headers: list[tuple[bytes, bytes]], path: str = SONG_SEARCH_PATH) -> Scope:
    return {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "root_path": "",
        "headers": headers,
        "client": ("127.0.0.1", 50000),
        "server": ("127.0.0.1", 8000),
    }


def body_messages(chunks: list[bytes]) -> list[Message]:
    """One `http.request` per chunk; only the last one ends the body."""
    return [
        {"type": "http.request", "body": chunk, "more_body": index < len(chunks) - 1}
        for index, chunk in enumerate(chunks)
    ]


def run_like_uvicorn(
    app: FastAPI,
    headers: list[tuple[bytes, bytes]],
    incoming: list[Message],
    path: str = SONG_SEARCH_PATH,
) -> list[Message]:
    """Runs one POST to `path` and returns every message the app sent.

    `receive` hands out `incoming` in order, then `http.disconnect`. An exception that
    escapes the app is logged to `uvicorn.error` with its traceback, as uvicorn does.
    """
    pending = list(incoming)
    sent: list[Message] = []

    async def receive() -> Message:
        if pending:
            return pending.pop(0)
        return {"type": "http.disconnect"}

    async def send(message: Message) -> None:
        sent.append(message)

    async def run() -> None:
        try:
            await app(post_scope(headers, path), receive, send)
        except BaseException as error:
            logging.getLogger(UVICORN_ERROR_LOGGER).error(
                "Exception in ASGI application\n", exc_info=error
            )

    asyncio.run(run())
    return sent


def response_status(sent: list[Message]) -> int:
    start = next(message for message in sent if message["type"] == "http.response.start")
    status: int = start["status"]
    return status


def response_body(sent: list[Message]) -> bytes:
    return b"".join(
        message.get("body", b"") for message in sent if message["type"] == "http.response.body"
    )
