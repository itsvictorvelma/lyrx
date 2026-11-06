"""Turn one song name into a lyric draft.

LRCLIB supplies the original Japanese lines. One Groq completion supplies
the kanji readings and the direct English. Romaji is spelled from the
hiragana. A bad draft is rejected. Nothing is saved here, and a failure
does not start a second completion.
"""

import json
import re
from collections.abc import Callable

from app.contracts import DraftLine, GenerationResponse, LyricDraft
from app.errors import DomainError
from app.generation.groq import GroqClient
from app.generation.lrclib import Recording, lyric_lines, search_recording
from app.generation.prompts import confirmation, segment_body
from app.reading import ReadingError, line_reading

Search = Callable[[str, str], Recording | None]
_BY = re.compile(r"(.+?)\s+by\s+(.+)", re.IGNORECASE)
_MISS = "No Japanese lyric was found for that song. Send again."
_BAD = "The lyrics came back in a shape that could not be used. Send again."
_INCOMPLETE = "The lyrics did not include every line. Send again."


class GenerationService:
    def __init__(self, client: GroqClient, model: str, search: Search | None = None) -> None:
        self._client = client
        self._model = model
        self._search = search or search_recording

    def generate(self, instruction: str, _draft: LyricDraft | None = None) -> GenerationResponse:
        title, artist = song_name(instruction)
        if not title:
            raise DomainError("generation_invalid", _MISS)
        recording = self._search(title, artist)
        if recording is None:
            raise DomainError("generation_invalid", _MISS)
        originals = lyric_lines(recording.text)
        if not originals:
            raise DomainError("generation_invalid", _MISS)
        lines = self.complete_lines(recording.title, recording.artist, originals)
        parsed = LyricDraft(title=recording.title, artist=recording.artist, lines=lines)
        return GenerationResponse(message=confirmation(parsed), draft=parsed)

    def complete_lines(self, title: str, artist: str, originals: list[str]) -> list[DraftLine]:
        """One completion for these original lines. No retry."""

        if not originals:
            raise DomainError("generation_invalid", _MISS)
        body = segment_body(self._model, title, artist, originals)
        payload = _content(self._client.complete(body), len(originals))
        return _accept(originals, _slot_rows(payload))


def song_name(instruction: str) -> tuple[str, str]:
    """'title by artist' splits. Any other text is the title, with no artist."""

    text = instruction.strip()
    match = _BY.search(text)
    if match is not None:
        title = match.group(1).strip(" \"'")
        artist = match.group(2).strip(" \"'.")
        if title and artist:
            return title, artist
    return text, ""


def _slot_rows(payload: object) -> list[tuple[object, str]]:
    if not isinstance(payload, dict):
        raise DomainError("generation_invalid", _BAD)
    rows = payload.get("lines")
    if not isinstance(rows, list):
        raise DomainError("generation_invalid", _BAD)
    parsed: list[tuple[object, str]] = []
    for row in rows:
        if not isinstance(row, dict):
            raise DomainError("generation_invalid", _BAD)
        readings = row.get("readings")
        english = row.get("translationEnglish")
        if isinstance(readings, list):
            if not all(isinstance(item, str) for item in readings):
                raise DomainError("generation_invalid", _BAD)
        elif not isinstance(readings, str):
            raise DomainError("generation_invalid", _BAD)
        if not isinstance(english, str) or not english.strip():
            raise DomainError("generation_invalid", "A lyric line was empty.")
        parsed.append((readings, english.strip()))
    return parsed


def _accept(originals: list[str], rows: list[tuple[object, str]]) -> list[DraftLine]:
    if len(rows) != len(originals):
        raise DomainError("generation_invalid", _INCOMPLETE)
    locked: list[DraftLine] = []
    for original, (raw_readings, english) in zip(originals, rows, strict=True):
        try:
            hiragana, romaji = line_reading(original, raw_readings)
        except ReadingError as exc:
            raise DomainError("generation_invalid", _INCOMPLETE) from exc
        locked.append(
            DraftLine(
                originalText=original.strip(),
                readingHiragana=hiragana,
                pronunciationRomaji=romaji,
                translationEnglish=english,
            )
        )
    return locked


def _content(payload: dict[str, object], expected: int) -> object:
    status = payload.get("status_code", 200)
    data = payload.get("data")
    error = data.get("error") if isinstance(data, dict) else None
    code = error.get("code") if isinstance(error, dict) else None
    if status in {429, 413} or code == "rate_limit_exceeded":
        raise DomainError("groq_rate_limited", "The lyric request hit the token limit. Wait a minute and send again.")
    if status in {401, 403}:
        raise DomainError("groq_unauthorized", "The lyric model is not connected.")
    failed = status == 400 or (status != 200 and code == "json_validate_failed")
    if failed:
        # json_validate_failed still carries the generated lines. That text is
        # this completion, so it is the draft. Nothing is asked again.
        found = _lines_from(error, ("failed_generation",), expected)
        if found is None:
            found = _lines_from(data, ("failed_generation",), expected)
        if found is None:
            found = _lines_from(_message(data), ("content", "reasoning"), expected)
        if found is None:
            raise DomainError("generation_invalid", _BAD)
        return found
    if status != 200:
        raise DomainError("groq_unavailable", "The lyric request failed. Send again.")
    found = _lines_from(_message(data), ("content", "reasoning"), expected)
    if found is None:
        raise DomainError("generation_invalid", _BAD)
    return found


def _message(data: object) -> object:
    try:
        message = data["choices"][0]["message"]  # type: ignore[index]
    except (KeyError, IndexError, TypeError):
        return None
    return message


def _lines_from(source: object, keys: tuple[str, ...], expected: int) -> object | None:
    if not isinstance(source, dict):
        return None
    for key in keys:
        found = _json_lines(source.get(key), expected)
        if found is not None:
            return found
    return None


def _json_lines(value: object, expected: int) -> object | None:
    if isinstance(value, dict):
        return value if isinstance(value.get("lines"), list) else None
    if not isinstance(value, str) or not value.strip():
        return None
    parsed = _loads_lines(value.strip(), expected)
    if isinstance(parsed, dict) and isinstance(parsed.get("lines"), list):
        return parsed
    return None


def _loads_lines(text: str, expected: int) -> dict[str, object] | None:
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        parsed = None
    if isinstance(parsed, dict) and isinstance(parsed.get("lines"), list):
        return parsed
    decoder = json.JSONDecoder()
    found: list[dict[str, object]] = []
    start = 0
    while True:
        index = text.find("{", start)
        if index < 0:
            break
        try:
            parsed, _end = decoder.raw_decode(text, index)
        except json.JSONDecodeError:
            start = index + 1
            continue
        if isinstance(parsed, dict) and isinstance(parsed.get("lines"), list):
            found.append(parsed)
        start = index + 1
    if not found:
        return None
    # A later one-line object is not the song. Keep the object that has
    # every lyric line. A shorter object is still rejected downstream.
    complete = [item for item in found if len(item["lines"]) == expected]
    if complete:
        return complete[-1]
    best = found[0]
    for item in found[1:]:
        if len(item["lines"]) >= len(best["lines"]):
            best = item
    return best
