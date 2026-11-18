"""The checks on a translator's reply: its JSON, then each line's three versions."""

import json

from pydantic import BaseModel, ConfigDict, ValidationError

from lyrx.errors import ApiError
from lyrx.lyrics.japanese import has_japanese, is_kana, is_kanji
from lyrx.translation.results import LineVersions


class ReplyLine(BaseModel):
    """One line of a translator's reply. Strict: no coercion and no extra fields."""

    model_config = ConfigDict(strict=True, extra="forbid")

    index: int
    hiragana: str
    romaji: str
    english: str


def parse_reply_lines(text: str) -> dict[int, ReplyLine]:
    """The reply's lines by index, the first one kept for a repeated index.

    The reply must be a JSON object with a `lines` array; items that are not a valid line
    are skipped, so one malformed item costs only its own line.
    """
    try:
        data = json.loads(text)
    except (ValueError, RecursionError):
        raise ApiError("translation_invalid", reason="bad_json") from None
    if not isinstance(data, dict) or not isinstance(data.get("lines"), list):
        raise ApiError("translation_invalid", reason="bad_json")
    lines: dict[int, ReplyLine] = {}
    for item in data["lines"]:
        try:
            line = ReplyLine.model_validate(item)
        except ValidationError:
            continue
        lines.setdefault(line.index, line)
    return lines


def line_is_valid(reply_line: ReplyLine, original: str) -> bool:
    """A Japanese line needs all three versions, hiragana without kanji, romaji without kana."""
    if not has_japanese(original):
        return True
    versions = (reply_line.hiragana, reply_line.romaji, reply_line.english)
    return (
        all(version.strip() for version in versions)
        and not any(is_kanji(character) for character in reply_line.hiragana)
        and not any(is_kana(character) or is_kanji(character) for character in reply_line.romaji)
    )


def line_versions(reply_line: ReplyLine, original: str) -> LineVersions:
    """A line with no Japanese keeps its own text in every version; the reply's is ignored."""
    if not has_japanese(original):
        return LineVersions(hiragana=original, romaji=original, english=original)
    return LineVersions(
        hiragana=reply_line.hiragana.strip(),
        romaji=reply_line.romaji.strip(),
        english=reply_line.english.strip(),
    )
