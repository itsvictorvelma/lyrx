"""Validate ordered lyric lines.

Line numbers start at 0. Every stored line has original text, hiragana,
romaji, and English. Timing fields are dropped on read and rejected on write.
"""

import hashlib
import json

from pydantic import ValidationError

from app.contracts import TIMING_FIELDS, LyricDraft, LyricLine
from app.errors import DomainError

SCHEMA_VERSION = 2


def load_lines(raw_lines: object) -> list[LyricLine]:
    if not isinstance(raw_lines, list):
        raise ValueError("lyric lines must be a list")
    lines: list[LyricLine] = []
    for raw in raw_lines:
        if isinstance(raw, dict):
            raw = {key: value for key, value in raw.items() if key not in TIMING_FIELDS}
        lines.append(LyricLine.model_validate(raw))
    return lines


def dump_lines(lines: list[LyricLine]) -> str:
    return json.dumps([line.model_dump(mode="json") for line in lines], ensure_ascii=False)


def content_hash(lines_json: str) -> str:
    return hashlib.sha256(lines_json.encode("utf-8")).hexdigest()


def lines_for_song(song_id: str, draft: LyricDraft) -> list[LyricLine]:
    lines: list[LyricLine] = []
    for index, row in enumerate(draft.lines):
        try:
            lines.append(
                LyricLine(
                    id=f"{song_id}-{index}",
                    index=index,
                    originalText=row.originalText.strip(),
                    readingHiragana=row.readingHiragana.strip(),
                    pronunciationRomaji=row.pronunciationRomaji.strip(),
                    translationEnglish=row.translationEnglish.strip(),
                )
            )
        except ValidationError as exc:
            raise DomainError("generation_invalid", "A lyric line was empty.") from exc
    return lines


def draft_from_model(payload: object) -> LyricDraft:
    if not isinstance(payload, dict):
        raise DomainError("generation_invalid", "The lyrics came back in a shape that could not be used. Send again.")
    found = sorted(TIMING_FIELDS.intersection(payload))
    if found:
        raise DomainError("generation_invalid", "The lyrics came back with timing fields. Send again.")
    raw_lines = payload.get("lines")
    if isinstance(raw_lines, list):
        for row in raw_lines:
            if isinstance(row, dict) and TIMING_FIELDS.intersection(row):
                raise DomainError("generation_invalid", "The lyrics came back with timing fields. Send again.")
    try:
        draft = LyricDraft.model_validate(
            {
                "title": str(payload.get("title", "")).strip(),
                "artist": str(payload.get("artist", "")).strip(),
                "lines": [_clean_row(row) for row in raw_lines] if isinstance(raw_lines, list) else raw_lines,
            }
        )
    except (ValidationError, TypeError) as exc:
        raise DomainError("generation_invalid", "The lyrics came back in a shape that could not be used. Send again.") from exc
    return draft


def _clean_row(row: object) -> object:
    if not isinstance(row, dict):
        return row
    return {
        "originalText": str(row.get("originalText", "")).strip(),
        "readingHiragana": str(row.get("readingHiragana", "")).strip(),
        "pronunciationRomaji": str(row.get("pronunciationRomaji", "")).strip(),
        "translationEnglish": str(row.get("translationEnglish", "")).strip(),
    }
