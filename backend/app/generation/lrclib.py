"""Read plain lyrics from LRCLIB.

The model was returning a short excerpt. The original lines come from the
search result, and Groq only fills the other columns. An exact title and
artist match wins, and among those the longest lyric wins.
"""

import re
from urllib.parse import urlencode

import httpx

from app.errors import DomainError

SEARCH_URL = "https://lrclib.net/api/search"


def lyric_lines(plain: str) -> list[str]:
    lines: list[str] = []
    for raw in plain.splitlines():
        text = raw.strip()
        if not text or (text.startswith("[") and text.endswith("]")):
            continue
        lines.append(text)
    return lines


def search_plain(title: str, artist: str) -> str | None:
    query = urlencode({"track_name": title, "artist_name": artist})
    try:
        response = httpx.get(
            f"{SEARCH_URL}?{query}",
            headers={"User-Agent": "Lyrx/0.1 (local study)"},
            timeout=20,
        )
    except httpx.HTTPError as exc:
        raise DomainError("groq_unavailable", "The lyric text could not be fetched. Send again.") from exc
    if response.status_code != 200:
        return None
    return choose_plain(response.json(), title, artist)


def choose_plain(rows: object, title: str, artist: str) -> str | None:
    if not isinstance(rows, list):
        return None
    best_text: str | None = None
    best_key: tuple[bool, bool, int] | None = None
    for row in rows:
        if not isinstance(row, dict) or row.get("instrumental") is True:
            continue
        text = row.get("plainLyrics")
        if not isinstance(text, str) or not text.strip():
            continue
        key = (
            _same(row.get("trackName"), title),
            _same(row.get("artistName"), artist),
            len(lyric_lines(text)),
        )
        if best_key is None or key > best_key:
            best_key = key
            best_text = text
    return best_text


def _same(left: object, right: str) -> bool:
    return isinstance(left, str) and _fold(left) == _fold(right)


def _fold(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().casefold()
