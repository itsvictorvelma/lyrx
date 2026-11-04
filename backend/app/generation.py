"""Build one Groq lyric completion and read the draft back.

Prompt tokens and completion tokens share an 8,000 token minute on the free
plan. reasoning_effort stays low so the reply is not spent on thinking.
temperature stays 0.6: Groq's guide for this model asks for 0.5–0.7, and
lower values start repeating. The measured call is recorded in
benchmarks/groq-token-usage.md.
"""

import json

from app.contracts import DraftLine, LyricDraft
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


RULES = (
    "Return one line per numbered line, in the same order, and copy originalText exactly. "
    "readingHiragana is spaced hiragana with no kanji. Keep every kana from that original line, in order. "
    "Use the reading that is sung in this song when you know it. "
    "translationEnglish is the literal meaning of that line only. "
    "Do not add a subject, merge lines, or return the previous line."
)


def user_message(instruction: str, draft: LyricDraft | None) -> str:
    text = instruction.strip()
    if draft is None:
        return (
            "Write the complete song, from the first line through the last, including every repeated chorus. "
            "Do not return a sample, a verse, a section label, or a summary. "
            f"{RULES} Request: {text}"
        )
    current = json.dumps(draft.model_dump(mode="json"), ensure_ascii=False)
    return (
        "Return every line of the current song, in the same order. "
        f"{RULES} Instruction: {text}\nCurrent song: {current}"
    )


def segment_message(
    title: str,
    artist: str,
    instruction: str,
    originals: list[str],
    previous: str | None,
    current: list[DraftLine] | None,
) -> str:
    blocks: list[str] = []
    for number, original in enumerate(originals, 1):
        block = [f"{number}. {original}"]
        if current is not None:
            row = current[number - 1]
            reading = row.readingHiragana.strip()
            if reading and reading != "よみ":
                block.append(f"   hiragana: {reading}")
            english = row.translationEnglish.strip()
            if english:
                block.append(f"   english: {english}")
        blocks.append("\n".join(block))
    context = f"Previous line, do not return it: {previous}\n" if previous else ""
    shown = "\n".join(blocks)
    return f"Song: {title} / {artist}\n{RULES}\nInstruction: {instruction.strip()}\n{context}Lines:\n{shown}"


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
    return _request(model, user_message(instruction, draft))


def segment_body(
    model: str,
    instruction: str,
    title: str,
    artist: str,
    originals: list[str],
    previous: str | None,
    current: list[DraftLine] | None,
) -> dict[str, object]:
    return _request(model, segment_message(title, artist, instruction, originals, previous, current))


def _request(model: str, prompt: str) -> dict[str, object]:
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
