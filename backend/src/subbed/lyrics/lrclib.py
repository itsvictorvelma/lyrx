"""LRCLIB: its client, the two requests (search, and one record by id), and the record shape."""

import json
from typing import Any

import httpx2
from pydantic import BaseModel, Field, TypeAdapter, ValidationError

from subbed import config
from subbed.errors import ApiError, ErrorCode
from subbed.schemas import Song

HTTP_NOT_FOUND = 404


class LrclibRecord(BaseModel):
    """One LRCLIB record, from search or by id. Fields Subbed does not read are ignored."""

    id: int = Field(strict=True, ge=1, le=config.MAX_SONG_ID)
    track_name: str = Field(alias="trackName", strict=True)
    artist_name: str = Field(alias="artistName", strict=True)
    album_name: str | None = Field(default=None, alias="albumName", strict=True)
    duration: float = Field(default=0, ge=0, strict=True, allow_inf_nan=False)
    instrumental: bool = Field(default=False, strict=True)
    plain_lyrics: str | None = Field(default=None, alias="plainLyrics", strict=True)
    synced_lyrics: str | None = Field(default=None, alias="syncedLyrics", strict=True)


RECORD_ADAPTER = TypeAdapter(LrclibRecord)


def to_song(record: LrclibRecord) -> Song:
    """The song a record is about, as the page shows it."""
    return Song(
        id=record.id,
        track=record.track_name,
        artist=record.artist_name,
        album=record.album_name or "",
        duration_seconds=round(record.duration),
    )


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


def make_lrclib_client(transport: httpx2.BaseTransport) -> httpx2.Client:
    """No redirects, no proxies, the app's User-Agent, and uncompressed bodies for the caps."""
    return httpx2.Client(
        transport=transport,
        timeout=config.LRCLIB_TIMEOUT_SECONDS,
        follow_redirects=False,
        trust_env=False,
        headers={"User-Agent": config.USER_AGENT, "Accept-Encoding": "identity"},
    )
