"""Build one Groq lyric completion and read the draft back.

Prompt tokens and completion tokens share an 8,000 token minute on the free
plan. reasoning_effort stays low so the reply is not spent on thinking.
The measured call is recorded in benchmarks/groq-token-usage.md.
"""

import json

from app.contracts import LyricDraft
from app.errors import DomainError

TOKEN_MINUTE = 8_000
SCHEMA_OVERHEAD = 800
COMPLETION_FLOOR = 400
COMPLETION_CAP = 6_000

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
            "Write the lyric layers for the song the learner named. "
            "Every line needs original Japanese, hiragana, romaji, and direct English. "
            f"Request: {text}"
        )
    current = json.dumps(draft.model_dump(mode="json"), ensure_ascii=False)
    return (
        "Replace the lyric lines using the learner's instruction. Return the full song. "
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
        "temperature": 0.6,
        "max_completion_tokens": completion_limit(prompt),
        "reasoning_effort": "low",
        "include_reasoning": False,
        "messages": [{"role": "user", "content": prompt}],
        "response_format": LYRIC_SCHEMA,
    }


def confirmation(draft: LyricDraft) -> str:
    count = len(draft.lines)
    label = "line" if count == 1 else "lines"
    return f"{draft.title}, {count} {label}"
