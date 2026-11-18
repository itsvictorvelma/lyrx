"""The two LRCLIB requests, search and one record by id, with their caps and checks."""

import json
from typing import Any

import httpx2
from pydantic import TypeAdapter, ValidationError

from lyrx import config
from lyrx.errors import ApiError, ErrorCode
from lyrx.schemas import LrclibRecord

HTTP_NOT_FOUND = 404
RECORD_ADAPTER = TypeAdapter(LrclibRecord)


def search(query: str, client: httpx2.Client) -> list[LrclibRecord]:
    """The valid records among the first items LRCLIB returns; invalid items are dropped."""
    body = fetch_json(
        config.LRCLIB_SEARCH_URL,
        {"q": query},
        config.LRCLIB_SEARCH_MAX_BYTES,
        client,
        not_found_code="lyrics_source_unavailable",
    )
    if not isinstance(body, list):
        raise ApiError("lyrics_source_unavailable")
    return [record for item in body[: config.SEARCH_ITEMS_READ] if (record := to_record(item))]


def get_record(record_id: int, client: httpx2.Client) -> LrclibRecord:
    """One record by id; it must pass the schema and carry the requested id."""
    url = config.LRCLIB_RECORD_URL.format(id=record_id)
    body = fetch_json(
        url, {}, config.LRCLIB_RECORD_MAX_BYTES, client, not_found_code="song_not_found"
    )
    record = to_record(body)
    if record is None or record.id != record_id:
        raise ApiError("lyrics_source_unavailable")
    return record


def to_record(item: Any) -> LrclibRecord | None:
    try:
        return RECORD_ADAPTER.validate_python(item)
    except ValidationError:
        return None


def fetch_json(
    url: str,
    params: dict[str, str],
    max_bytes: int,
    client: httpx2.Client,
    not_found_code: ErrorCode,
) -> Any:
    """One GET to a fixed LRCLIB address, body capped while it streams, then parsed as JSON.

    The client asks for the body uncompressed, so the cap counts real bytes.
    """
    try:
        with client.stream("GET", url, params=params) as response:
            if response.status_code == HTTP_NOT_FOUND:
                raise ApiError(not_found_code)
            if response.status_code != httpx2.codes.OK:
                raise ApiError("lyrics_source_unavailable")
            content = read_capped(response, max_bytes)
    except httpx2.RequestError:
        raise ApiError("lyrics_source_unavailable") from None
    try:
        return json.loads(content)
    except (ValueError, RecursionError):
        raise ApiError("lyrics_source_unavailable") from None


def read_capped(response: httpx2.Response, max_bytes: int) -> bytes:
    """The body, refused as soon as it passes `max_bytes`."""
    content = bytearray()
    for piece in response.iter_bytes():
        content.extend(piece)
        if len(content) > max_bytes:
            raise ApiError("lyrics_source_unavailable")
    return bytes(content)
