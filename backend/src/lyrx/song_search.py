"""Search: from the typed text to a short ranked list of LRCLIB songs."""

import unicodedata

import httpx2

from lyrx import config, lrclib
from lyrx.errors import ApiError
from lyrx.lines import read_lyrics
from lyrx.looks_japanese import looks_japanese
from lyrx.schemas import LrclibRecord, SearchResult


def search_songs(query: str, transport: httpx2.BaseTransport) -> list[SearchResult]:
    """Japanese-looking songs first, then LRCLIB's order, duplicates removed, at most 10."""
    query = query.strip()
    if not query:
        raise ApiError("empty_search")
    if len(query) > config.SEARCH_QUERY_MAX_CHARACTERS:
        raise ApiError("invalid_request")
    records = [record for record in lrclib.search(query, transport) if has_lyrics(record)]
    results = [to_result(record) for record in records]
    ranked = sorted(results, key=lambda result: not result.looks_japanese)
    kept = remove_duplicates(ranked)[: config.SEARCH_RESULTS_SHOWN]
    if not kept:
        raise ApiError("song_not_found")
    return kept


def has_lyrics(record: LrclibRecord) -> bool:
    return not record.instrumental and bool(record.plain_lyrics and record.plain_lyrics.strip())


def to_result(record: LrclibRecord) -> SearchResult:
    return SearchResult(
        id=record.id,
        track=record.track_name,
        artist=record.artist_name,
        album=record.album_name or "",
        duration_seconds=round(record.duration),
        looks_japanese=looks_japanese(read_lyrics(record.plain_lyrics or "")),
    )


def remove_duplicates(results: list[SearchResult]) -> list[SearchResult]:
    """Keeps the first of results with the same names and durations within a few seconds."""
    kept: list[SearchResult] = []
    for result in results:
        if not any(is_duplicate(result, earlier) for earlier in kept):
            kept.append(result)
    return kept


def is_duplicate(first: SearchResult, second: SearchResult) -> bool:
    return (
        same_name(first.track, second.track)
        and same_name(first.artist, second.artist)
        and abs(first.duration_seconds - second.duration_seconds)
        <= config.DUPLICATE_DURATION_SECONDS
    )


def same_name(first: str, second: str) -> bool:
    return normalize_name(first) == normalize_name(second)


def normalize_name(name: str) -> str:
    return unicodedata.normalize("NFKC", name).strip().casefold()
