"""Turn one learner message into a lyric draft."""

import json
import re

from app.contracts import DraftLine, GenerationResponse, LyricDraft
from app.errors import DomainError
from app.generation import completion_body, confirmation
from app.groq_client import GroqClient
from app.lrclib import lyric_lines, search_plain
from app.lyrics import draft_from_model

CHUNK = 12
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
        parsed = self._once(instruction, draft)
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
        lines: list[DraftLine] = []
        for start in range(0, len(originals), CHUNK):
            chunk = originals[start : start + CHUNK]
            lines.extend(self._fill_chunk(title, artist, chunk))
        draft = LyricDraft(title=title, artist=artist, lines=lines)
        return GenerationResponse(message=confirmation(draft), draft=draft)

    def _fill_chunk(self, title: str, artist: str, originals: list[str]) -> list[DraftLine]:
        seed = LyricDraft(
            title=title,
            artist=artist,
            lines=[
                DraftLine(
                    originalText=line,
                    readingHiragana="よみ",
                    pronunciationRomaji="yomi",
                    translationEnglish="line",
                )
                for line in originals
            ],
        )
        instruction = "Fill the hiragana, romaji, and English. Keep every original line."
        failure: DomainError | None = None
        for _attempt in range(2):
            try:
                parsed = self._once(instruction, seed)
                return _locked_lines(originals, parsed)
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

    def _once(self, instruction: str, draft: LyricDraft | None) -> LyricDraft:
        body = completion_body(self._model, instruction, draft)
        return draft_from_model(_content(self._client.complete(body)))


def _song_name(instruction: str) -> tuple[str, str] | None:
    match = re.search(r"(.+?)\s+by\s+(.+)", instruction, re.IGNORECASE)
    if match is None:
        return None
    title = match.group(1).strip(" \"'")
    artist = match.group(2).strip(" \"'.")
    if not title or not artist:
        return None
    return title, artist


def _locked_lines(originals: list[str], draft: LyricDraft) -> list[DraftLine]:
    if len(draft.lines) != len(originals):
        raise DomainError("generation_invalid", "The lyrics did not include every line. Send again.")
    locked: list[DraftLine] = []
    for original, row in zip(originals, draft.lines, strict=True):
        if original.strip() != row.originalText.strip():
            raise DomainError("generation_invalid", "The lyrics did not include every line. Send again.")
        locked.append(row.model_copy(update={"originalText": original.strip()}))
    return locked


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
