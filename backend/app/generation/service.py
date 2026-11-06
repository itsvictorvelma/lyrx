"""Turn one learner message into a lyric draft.

A named song is read from LRCLIB, then filled in groups of 12 lines.
A correction sends only the lines it names. A correction that names no line
uses the same groups, and a repeated line is translated once.
"""

import json
import re

from app.contracts import DraftLine, GenerationResponse, LyricDraft
from app.errors import DomainError
from app.generation.groq import GroqClient
from app.generation.lrclib import lyric_lines, search_plain
from app.generation.prompts import completion_body, confirmation, segment_body
from app.lyrics import draft_from_model
from app.reading import ReadingError, assemble_reading, lock_reading, needs_model

CHUNK = 12
_LINE_RANGE = re.compile(r"\blines?\s+(\d+)\s*(?:-|–|—|to)\s*(\d+)\b", re.IGNORECASE)
_LINE_ONE = re.compile(r"\bline\s+(\d+)\b", re.IGNORECASE)
_BY = re.compile(r"(.+?)\s+by\s+(.+)", re.IGNORECASE)
NAME_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "song_name",
        "strict": True,
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["title", "artist"],
            "properties": {"title": {"type": "string"}, "artist": {"type": "string"}},
        },
    },
}


class GenerationService:
    def __init__(self, client: GroqClient, model: str) -> None:
        self._client = client
        self._model = model

    def generate(self, instruction: str, draft: LyricDraft | None) -> GenerationResponse:
        if draft is None:
            sourced = self._from_recording(instruction)
            if sourced is not None:
                return sourced
            parsed = _polish(self._once(instruction))
            return GenerationResponse(message=confirmation(parsed), draft=parsed)
        parsed = self._revise(instruction, draft)
        return GenerationResponse(message=confirmation(parsed), draft=parsed)

    def _from_recording(self, instruction: str) -> GenerationResponse | None:
        named = _song_name(instruction)
        if named is None:
            if len(instruction.split()) < 3:
                return None
            named = self._identify(instruction)
        title, artist = named
        if not title or not artist:
            return None
        plain = search_plain(title, artist)
        if not plain:
            return None
        originals = lyric_lines(plain)
        if not originals:
            return None
        lines = self._fresh(title, artist, originals, instruction)
        draft = LyricDraft(title=title, artist=artist, lines=lines)
        return GenerationResponse(message=confirmation(draft), draft=draft)

    def _revise(self, instruction: str, draft: LyricDraft) -> LyricDraft:
        indexes = target_indexes(draft.lines, instruction)
        if indexes is None:
            lines = self._fresh(
                draft.title,
                draft.artist,
                [line.originalText for line in draft.lines],
                instruction,
            )
            return LyricDraft(title=draft.title, artist=draft.artist, lines=lines)
        if not indexes:
            raise DomainError("generation_invalid", "That line is not in this song. Send again.")
        lines = list(draft.lines)
        self._retouch(draft.title, draft.artist, lines, indexes, instruction)
        return LyricDraft(title=draft.title, artist=draft.artist, lines=lines)

    def _fresh(self, title: str, artist: str, originals: list[str], instruction: str) -> list[DraftLine]:
        cache: dict[str, DraftLine] = {}
        filled: list[DraftLine] = []
        for start in range(0, len(originals), CHUNK):
            window = originals[start : start + CHUNK]
            missing = [line for line in dict.fromkeys(window) if line not in cache]
            if missing:
                anchor = start + window.index(missing[0])
                previous = originals[anchor - 1] if anchor else None
                rows = self._fill_chunk(title, artist, missing, instruction, previous, None)
                cache.update(zip(missing, rows, strict=True))
            filled.extend(cache[line] for line in window)
        return filled

    def _retouch(
        self,
        title: str,
        artist: str,
        lines: list[DraftLine],
        indexes: list[int],
        instruction: str,
    ) -> None:
        refreshed: dict[str, DraftLine] = {}
        for start in range(0, len(indexes), CHUNK):
            group = indexes[start : start + CHUNK]
            unique = list(dict.fromkeys(lines[index].originalText for index in group))
            current: list[DraftLine] = []
            for original in unique:
                matched = next(index for index in group if lines[index].originalText == original)
                current.append(lines[matched])
            previous = lines[group[0] - 1].originalText if group[0] else None
            rows = self._fill_chunk(title, artist, unique, instruction, previous, current)
            refreshed.update(zip(unique, rows, strict=True))
        for index, line in enumerate(lines):
            chosen = refreshed.get(line.originalText)
            if chosen is None:
                continue
            lines[index] = line.model_copy(
                update={
                    "readingHiragana": chosen.readingHiragana,
                    "pronunciationRomaji": chosen.pronunciationRomaji,
                    "translationEnglish": chosen.translationEnglish,
                }
            )

    def _fill_chunk(
        self,
        title: str,
        artist: str,
        originals: list[str],
        instruction: str,
        previous: str | None,
        current: list[DraftLine] | None,
    ) -> list[DraftLine]:
        asked = [line for line in originals if current is not None or needs_model(line)]
        asked_current = None
        if current is not None:
            asked_current = [row for row, line in zip(current, originals, strict=True) if line in asked]
        if not asked:
            return [_local_line(line) for line in originals]
        failure: DomainError | None = None
        for _attempt in range(2):
            try:
                body = segment_body(self._model, instruction, title, artist, asked, previous, asked_current)
                filled = _accept_slots(asked, _slot_rows(_content(self._client.complete(body))))
                by_original = dict(zip(asked, filled, strict=True))
                return [by_original.get(line) or _local_line(line) for line in originals]
            except DomainError as exc:
                failure = exc
        raise failure or DomainError("generation_invalid", "The lyrics came back in a shape that could not be used. Send again.")

    def _identify(self, instruction: str) -> tuple[str, str]:
        body = completion_body(self._model, instruction, None)
        body["temperature"] = 0
        body["max_completion_tokens"] = 200
        body["response_format"] = NAME_SCHEMA
        body["messages"] = [
            {
                "role": "user",
                "content": (
                    "Name the song the learner means. Reply with the title and artist only. "
                    f"Request: {instruction.strip()}"
                ),
            }
        ]
        parsed = _content(self._client.complete(body))
        if not isinstance(parsed, dict):
            return "", ""
        return str(parsed.get("title", "")).strip(), str(parsed.get("artist", "")).strip()

    def _once(self, instruction: str) -> LyricDraft:
        body = completion_body(self._model, instruction, None)
        return draft_from_model(_content(self._client.complete(body)))


def target_indexes(lines: list[DraftLine], instruction: str) -> list[int] | None:
    """Line numbers and quoted lines to resend. None means every line."""

    found: set[int] = set()
    named = _LINE_RANGE.search(instruction) is not None or _LINE_ONE.search(instruction) is not None
    for match in _LINE_RANGE.finditer(instruction):
        start, end = int(match.group(1)), int(match.group(2))
        if start > end:
            start, end = end, start
        for number in range(start, end + 1):
            index = number - 1
            if 0 <= index < len(lines):
                found.add(index)
    for match in _LINE_ONE.finditer(_LINE_RANGE.sub(" ", instruction)):
        index = int(match.group(1)) - 1
        if 0 <= index < len(lines):
            found.add(index)
    for index, line in enumerate(lines):
        original = line.originalText.strip()
        english = line.translationEnglish.strip()
        if (len(original) >= 2 and original in instruction) or (len(english) >= 8 and english in instruction):
            found.add(index)
    if found:
        return sorted(found)
    if named:
        return []
    return None


def _song_name(instruction: str) -> tuple[str, str] | None:
    match = _BY.search(instruction)
    if match is None:
        return None
    title = match.group(1).strip(" \"'")
    artist = match.group(2).strip(" \"'.")
    if not title or not artist:
        return None
    return title, artist


def _local_line(original: str) -> DraftLine:
    text = original.strip()
    return DraftLine(
        originalText=text,
        readingHiragana=text,
        pronunciationRomaji=text,
        translationEnglish=text,
    )


def _slot_rows(payload: object) -> list[tuple[list[str], str]]:
    if not isinstance(payload, dict):
        raise DomainError("generation_invalid", "The lyrics came back in a shape that could not be used. Send again.")
    rows = payload.get("lines")
    if not isinstance(rows, list):
        raise DomainError("generation_invalid", "The lyrics came back in a shape that could not be used. Send again.")
    parsed: list[tuple[list[str], str]] = []
    for row in rows:
        if not isinstance(row, dict):
            raise DomainError("generation_invalid", "The lyrics came back in a shape that could not be used. Send again.")
        readings = row.get("readings")
        english = row.get("translationEnglish")
        if not isinstance(readings, list) or not all(isinstance(item, str) for item in readings):
            raise DomainError("generation_invalid", "The lyrics came back in a shape that could not be used. Send again.")
        if not isinstance(english, str) or not english.strip():
            raise DomainError("generation_invalid", "A lyric line was empty.")
        parsed.append((readings, english.strip()))
    return parsed


def _accept_slots(originals: list[str], rows: list[tuple[list[str], str]]) -> list[DraftLine]:
    if len(rows) != len(originals):
        raise DomainError("generation_invalid", "The lyrics did not include every line. Send again.")
    locked: list[DraftLine] = []
    for original, (readings, english) in zip(originals, rows, strict=True):
        try:
            hiragana, romaji = assemble_reading(original, readings)
        except ReadingError as exc:
            raise DomainError("generation_invalid", "The lyrics did not include every line. Send again.") from exc
        locked.append(
            DraftLine(
                originalText=original.strip(),
                readingHiragana=hiragana,
                pronunciationRomaji=romaji,
                translationEnglish=english,
            )
        )
    return locked


def _polish(draft: LyricDraft) -> LyricDraft:
    lines: list[DraftLine] = []
    seen: dict[str, DraftLine] = {}
    for row in draft.lines:
        hiragana, romaji = _checked(row.originalText, row.readingHiragana)
        line = DraftLine(
            originalText=row.originalText.strip(),
            readingHiragana=hiragana,
            pronunciationRomaji=romaji,
            translationEnglish=row.translationEnglish.strip(),
        )
        chosen = seen.setdefault(line.originalText, line)
        lines.append(
            chosen
            if chosen is line
            else line.model_copy(
                update={
                    "readingHiragana": chosen.readingHiragana,
                    "pronunciationRomaji": chosen.pronunciationRomaji,
                    "translationEnglish": chosen.translationEnglish,
                }
            )
        )
    return draft.model_copy(update={"lines": lines})


def _checked(original: str, reading: str) -> tuple[str, str]:
    try:
        return lock_reading(original, reading)
    except ReadingError as exc:
        raise DomainError("generation_invalid", "The lyrics did not include every line. Send again.") from exc


def _content(payload: dict[str, object]) -> object:
    status = payload.get("status_code", 200)
    data = payload.get("data")
    error = data.get("error") if isinstance(data, dict) else None
    code = error.get("code") if isinstance(error, dict) else None
    if status in {429, 413} or code == "rate_limit_exceeded":
        raise DomainError("groq_rate_limited", "The lyric request hit the token limit. Wait a minute and send again.")
    if status in {401, 403}:
        raise DomainError("groq_unauthorized", "The lyric model is not connected.")
    if status == 400 or code == "json_validate_failed":
        raise DomainError("generation_invalid", "The lyrics came back in a shape that could not be used. Send again.")
    if status != 200:
        raise DomainError("groq_unavailable", "The lyric request failed. Send again.")
    try:
        content = data["choices"][0]["message"]["content"]  # type: ignore[index]
    except (KeyError, IndexError, TypeError) as exc:
        raise DomainError("generation_invalid", "The lyrics came back in a shape that could not be used. Send again.") from exc
    if not isinstance(content, str):
        raise DomainError("generation_invalid", "The lyrics came back in a shape that could not be used. Send again.")
    try:
        return json.loads(content)
    except json.JSONDecodeError as exc:
        raise DomainError("generation_invalid", "The lyrics came back in a shape that could not be used. Send again.") from exc
