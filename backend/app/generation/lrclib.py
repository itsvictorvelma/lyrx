"""Read one plain lyric from LRCLIB.

The original lines come from the search result. A Japanese lyric wins over
an English translation, even when the translation has more lines. Among
Japanese lyrics, an exact title wins, then an exact artist when the learner
named one, then the longest lyric.
"""

import re
from dataclasses import dataclass
from urllib.parse import urlencode

import httpx

from app.errors import DomainError

SEARCH_URL = "https://lrclib.net/api/search"


@dataclass(frozen=True)
class Recording:
    title: str
    artist: str
    text: str


def lyric_lines(plain: str) -> list[str]:
    lines: list[str] = []
    for raw in plain.splitlines():
        text = raw.strip()
        if not text or (text.startswith("[") and text.endswith("]")):
            continue
        lines.append(text)
    return lines


def search_recording(title: str, artist: str) -> Recording | None:
    params = {"track_name": title}
    if artist:
        params["artist_name"] = artist
    try:
        response = httpx.get(
            f"{SEARCH_URL}?{urlencode(params)}",
            headers={"User-Agent": "Lyrx/0.1 (local study)"},
            timeout=20,
        )
        payload = response.json() if response.status_code == 200 else None
    except httpx.HTTPError as exc:
        raise DomainError("groq_unavailable", "The lyric text could not be fetched. Send again.") from exc
    except ValueError as exc:
        raise DomainError("groq_unavailable", "The lyric text could not be fetched. Send again.") from exc
    if response.status_code != 200:
        return None
    return choose_recording(payload, title, artist)


def choose_recording(rows: object, title: str, artist: str) -> Recording | None:
    if not isinstance(rows, list):
        return None
    best: Recording | None = None
    best_key: tuple[bool, bool, int] | None = None
    for row in rows:
        if not isinstance(row, dict) or row.get("instrumental") is True:
            continue
        track = row.get("trackName")
        name = row.get("artistName")
        text = row.get("plainLyrics")
        if not isinstance(track, str) or not track.strip():
            continue
        if not isinstance(name, str) or not name.strip():
            continue
        if not isinstance(text, str) or not text.strip() or not _japanese_lyric(text):
            continue
        key = (
            _same(track, title),
            bool(artist) and _same(name, artist),
            len(lyric_lines(text)),
        )
        if best_key is None or key > best_key:
            best_key = key
            best = Recording(title=track.strip(), artist=name.strip(), text=text)
    return best


def _japanese_lyric(text: str) -> bool:
    lines = lyric_lines(text)
    if not lines:
        return False
    japanese = sum(1 for line in lines if _japanese_line(line))
    return japanese * 2 >= len(lines)


def _japanese_line(text: str) -> bool:
    return any(
        0x3040 <= ord(char) <= 0x30FF or 0x3400 <= ord(char) <= 0x4DBF or 0x4E00 <= ord(char) <= 0x9FFF
        for char in text
    )


def _same(left: object, right: str) -> bool:
    return isinstance(left, str) and _fold(left) == _fold(right)


def _fold(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().casefold()
