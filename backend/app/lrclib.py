"""Read plain lyrics from LRCLIB.

The model was returning a short excerpt. The original lines come from the
search result, and Groq only fills the other columns.
"""

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
    payload = response.json()
    if not isinstance(payload, list):
        return None
    for row in payload:
        if not isinstance(row, dict):
            continue
        text = row.get("plainLyrics")
        if isinstance(text, str) and text.strip():
            return text
    return None
