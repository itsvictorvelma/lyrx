"""The pipeline for one paste: from the cleaned lines to the four versions of every line."""

from lyrx import claude, config
from lyrx.claude import ClaudeClient
from lyrx.errors import ApiError
from lyrx.lines import has_japanese
from lyrx.readings import reading_is_allowed, reading_keeps_kana, tidy_reading
from lyrx.romaji import to_romaji
from lyrx.schemas import ReplyLine, TokenUsage, VersionLine, VersionsResponse


def make_four_versions(
    lines: list[str], claude_client: ClaudeClient | None
) -> tuple[VersionsResponse, TokenUsage]:
    """Every line in its four versions, and the tokens the call used.

    Every refusal happens before a Claude client is built or called.
    """
    if not any(has_japanese(line) for line in lines):
        raise ApiError("no_japanese")
    api_key = config.read_api_key()
    if api_key is None:
        raise ApiError("server_not_configured")
    # Called through the module so tests can replace `claude.make_client`.
    client = claude_client if claude_client is not None else claude.make_client(api_key)
    sent_lines = [(index, line) for index, line in enumerate(lines) if line]
    readings = claude.request_readings(client, sent_lines)
    replies = allowed_replies(lines, readings.lines)
    versions = [make_line(index, line, replies.get(index)) for index, line in enumerate(lines)]
    return VersionsResponse(lines=versions), readings.usage


def allowed_replies(lines: list[str], reply_lines: list[ReplyLine]) -> dict[int, ReplyLine]:
    """Claude's reply for each Japanese line, its reading tidied, keyed by line index.

    Every reading must pass the hard check (rule 5) before any kana-kept comparison
    runs, so one bad or over-long reading fails the whole reply with bounded work.
    Replies for blank or non-Japanese lines are left out: the server sets those itself.
    """
    replies: dict[int, ReplyLine] = {}
    for reply_line in reply_lines:
        original = lines[reply_line.index]
        if not has_japanese(original):
            continue
        reading = tidy_reading(reply_line.reading)
        if not reading_is_allowed(original, reading):
            raise ApiError("model_output_invalid")
        replies[reply_line.index] = reply_line.model_copy(update={"reading": reading})
    return replies


def make_line(index: int, original: str, reply: ReplyLine | None) -> VersionLine:
    """A Japanese line from Claude's checked reply; any other line repeats its original."""
    if reply is None:
        return VersionLine(
            index=index,
            original=original,
            hiragana=original,
            romaji=original,
            english=original,
            reading_verified=True,
        )
    return VersionLine(
        index=index,
        original=original,
        hiragana=reply.reading,
        romaji=to_romaji(reply.reading),
        english=reply.english,
        reading_verified=reading_keeps_kana(original, reply.reading),
    )
