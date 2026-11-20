"""Search: from the typed text to a short ranked list of LRCLIB songs."""

import unicodedata

import httpx2

from lyrx import config, library
from lyrx.errors import ApiError
from lyrx.lyrics import lrclib
from lyrx.lyrics.japanese import looks_japanese
from lyrx.lyrics.lines import read_lyrics
from lyrx.lyrics.lrclib import LrclibRecord
from lyrx.schemas import SearchResult


def search_songs(query: str, client: httpx2.Client, user_id: int | None) -> list[SearchResult]:
    """Japanese-looking songs first, then LRCLIB's order, duplicates removed, at most 10.

    `saved` marks this person's saved songs; it is always false for a guest.
    """
    query = query.strip()
    if not query:
        raise ApiError("empty_search")
    if len(query) > config.SEARCH_QUERY_MAX_CHARACTERS:
        raise ApiError("invalid_request")
    records = [record for record in lrclib.search(query, client) if has_lyrics(record)]
    results = [to_result(record) for record in records]
    ranked = sorted(results, key=lambda result: not result.looks_japanese)
    kept = remove_duplicates(ranked)[: config.SEARCH_RESULTS_SHOWN]
    if not kept:
        raise ApiError("song_not_found")
    if user_id is None:
        return kept
    saved = library.saved_ids_or_none(user_id, (result.id for result in kept))
    return [result.model_copy(update={"saved": result.id in saved}) for result in kept]


def has_lyrics(record: LrclibRecord) -> bool:
    return not record.instrumental and bool(record.plain_lyrics and record.plain_lyrics.strip())


def to_result(record: LrclibRecord) -> SearchResult:
    return SearchResult(
        **lrclib.to_song(record).model_dump(),
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
