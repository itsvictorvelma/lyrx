"""Build one Groq lyric completion and read the draft back.

Prompt tokens and completion tokens share an 8,000 token minute on the free
plan. reasoning_effort stays low so the reply is not spent on thinking.
Hiragana and romaji are not asked of the model. A sourced song asks only for
the English meanings. The measured call is recorded in benchmarks/groq-token-usage.md.
"""

import json

from app.contracts import LyricDraft
from app.errors import DomainError

TOKEN_MINUTE = 8_000
SCHEMA_OVERHEAD = 800
COMPLETION_FLOOR = 400
COMPLETION_CAP = 6_000
MEANING_CAP = 1_200

LYRIC_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "lyric_draft",
        "strict": True,
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["title", "artist", "lines"],
            "properties": {
                "title": {"type": "string"},
                "artist": {"type": "string"},
                "lines": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": [
                            "originalText",
                            "readingHiragana",
                            "pronunciationRomaji",
                            "translationEnglish",
                        ],
                        "properties": {
                            "originalText": {"type": "string"},
                            "readingHiragana": {"type": "string"},
                            "pronunciationRomaji": {"type": "string"},
                            "translationEnglish": {"type": "string"},
                        },
                    },
                },
            },
        },
    },
}


def user_message(instruction: str, draft: LyricDraft | None) -> str:
    text = instruction.strip()
    if draft is None:
        return (
            "Write the complete song, from the first line through the last, including repeated choruses. "
            "Do not return a sample, a verse, or a summary. "
            "Every line needs original Japanese, spaced hiragana, spaced Hepburn romaji, and a literal English meaning. "
            "Keep the spaces that separate phrases. "
            f"Request: {text}"
        )
    current = json.dumps(draft.model_dump(mode="json"), ensure_ascii=False)
    return (
        "Return every line of the current song, in the same order. "
        "Keep each originalText exactly, including its spaces. "
        "readingHiragana is spaced hiragana, pronunciationRomaji is spaced Hepburn, "
        "and translationEnglish is the literal meaning of that one line. "
        f"Instruction: {text}\nCurrent song: {current}"
    )


def completion_limit(prompt: str) -> int:
    estimate = SCHEMA_OVERHEAD + max(1, len(prompt) // 4)
    room = TOKEN_MINUTE - estimate
    if room < COMPLETION_FLOOR:
        raise DomainError(
            "generation_too_large",
            "That song is too long for one lyric request. Shorten the request and send again.",
        )
    return min(COMPLETION_CAP, room)


def completion_body(model: str, instruction: str, draft: LyricDraft | None) -> dict[str, object]:
    prompt = user_message(instruction, draft)
    return {
        "model": model,
        "temperature": 0,
        "max_completion_tokens": completion_limit(prompt),
        "reasoning_effort": "low",
        "include_reasoning": False,
        "messages": [{"role": "user", "content": prompt}],
        "response_format": LYRIC_SCHEMA,
    }


MEANING_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "line_meanings",
        "strict": True,
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["meanings"],
            "properties": {"meanings": {"type": "array", "items": {"type": "string"}}},
        },
    },
}


def meaning_message(title: str, artist: str, lines: list[str], note: str = "") -> str:
    numbered = "\n".join(f"{index}. {line}" for index, line in enumerate(lines, start=1))
    prefix = note.strip()
    lead = f"{prefix}\n" if prefix else ""
    return (
        f"{lead}Translate each line of {title} by {artist} into literal English. "
        f"Return exactly {len(lines)} meanings, in the same order. "
        "Copy a line that is already English. Do not add, merge, or drop a line.\n"
        f"{numbered}"
    )


def meaning_body(model: str, title: str, artist: str, lines: list[str], note: str = "") -> dict[str, object]:
    prompt = meaning_message(title, artist, lines, note)
    return {
        "model": model,
        "temperature": 0,
        "max_completion_tokens": min(MEANING_CAP, completion_limit(prompt)),
        "reasoning_effort": "low",
        "include_reasoning": False,
        "messages": [{"role": "user", "content": prompt}],
        "response_format": MEANING_SCHEMA,
    }


def meanings_from(payload: object, expected: int) -> list[str]:
    rows = payload.get("meanings") if isinstance(payload, dict) else None
    if not isinstance(rows, list) or len(rows) != expected:
        raise DomainError("generation_invalid", "The lyrics did not include every line. Send again.")
    meanings: list[str] = []
    for row in rows:
        if not isinstance(row, str) or not row.strip():
            raise DomainError("generation_invalid", "The lyrics came back in a shape that could not be used. Send again.")
        meanings.append(row.strip())
    return meanings


def confirmation(draft: LyricDraft) -> str:
    count = len(draft.lines)
    label = "line" if count == 1 else "lines"
    return f"{draft.title}, {count} {label}"
