"""Build one Groq lyric completion.

The original lines come from LRCLIB. The completion returns one hiragana
reading per kanji bracket and the direct English. Romaji is not requested.
Prompt tokens and completion tokens share an 8,000 token minute on the free
plan. reasoning_effort stays low so the reply is not spent on thinking.
temperature stays 0.6: Groq's guide for this model asks for 0.5–0.7, and
lower values start repeating. The measured call is recorded in
benchmarks/groq-token-usage.md.
"""

from app.contracts import LyricDraft
from app.errors import DomainError
from app.reading import marked

TOKEN_MINUTE = 8_000
SCHEMA_OVERHEAD = 800
COMPLETION_FLOOR = 400
COMPLETION_CAP = 6_000

SLOT_RULES = (
    "readings is one hiragana string for each 【bracket】, in order. "
    "Read the whole bracket, including the kana inside it, and leave every character outside the brackets out of readings. "
    "A line with no brackets has an empty readings list. "
    "私 is わたし. 明日 is あした. Keep rendaku. "
    "translationEnglish is the literal meaning of that one line. "
    "Do not add a subject or return the previous line."
)

SLOT_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "lyric_slots",
        "strict": True,
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["lines"],
            "properties": {
                "lines": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["readings", "translationEnglish"],
                        "properties": {
                            "readings": {"type": "array", "items": {"type": "string"}},
                            "translationEnglish": {"type": "string"},
                        },
                    },
                },
            },
        },
    },
}


def segment_message(title: str, artist: str, originals: list[str]) -> str:
    shown = "\n".join(f"{number}. {marked(original)}" for number, original in enumerate(originals, 1))
    return f"Song: {title} / {artist}\n{SLOT_RULES}\nLines:\n{shown}"


def completion_limit(prompt: str) -> int:
    estimate = SCHEMA_OVERHEAD + max(1, len(prompt) // 4)
    room = TOKEN_MINUTE - estimate
    if room < COMPLETION_FLOOR:
        raise DomainError(
            "generation_too_large",
            "That song is too long for one lyric request. Shorten the request and send again.",
        )
    return min(COMPLETION_CAP, room)


def segment_body(model: str, title: str, artist: str, originals: list[str]) -> dict[str, object]:
    prompt = segment_message(title, artist, originals)
    return {
        "model": model,
        "temperature": 0.6,
        "max_completion_tokens": completion_limit(prompt),
        "reasoning_effort": "low",
        "include_reasoning": False,
        "messages": [{"role": "user", "content": prompt}],
        "response_format": SLOT_SCHEMA,
    }


def confirmation(draft: LyricDraft) -> str:
    count = len(draft.lines)
    label = "line" if count == 1 else "lines"
    return f"{draft.title}, {count} {label}"
