"""Cuts a song's lines into chunks and asks Gemini for each chunk's versions, in order."""

import httpx2

from lyrx import config
from lyrx.gemini import NumberedLines, request_versions
from lyrx.schemas import GeminiVersions, LineVersions, TokenUsage


def request_in_chunks(
    lines: NumberedLines, api_key: str, transport: httpx2.BaseTransport
) -> GeminiVersions:
    """One Gemini call per chunk, in order; the first failure propagates and nothing is kept."""
    versions: dict[int, LineVersions] = {}
    input_tokens = 0
    output_tokens = 0
    chunks = split_into_chunks(lines)
    for chunk in chunks:
        result = request_versions(chunk, api_key, transport)
        versions.update(result.lines)
        input_tokens += result.usage.input_tokens
        output_tokens += result.usage.output_tokens
    return GeminiVersions(
        lines=versions,
        usage=TokenUsage(input_tokens=input_tokens, output_tokens=output_tokens),
        calls=len(chunks),
    )


def split_into_chunks(lines: NumberedLines) -> list[list[tuple[int, str]]]:
    """Consecutive chunks, each as large as both chunk sizes allow."""
    chunks: list[list[tuple[int, str]]] = []
    characters = 0
    for index, text in lines:
        if chunks and fits(len(chunks[-1]), characters, text):
            characters += 1 + len(text)
            chunks[-1].append((index, text))
        else:
            chunks.append([(index, text)])
            characters = len(text)
    return chunks


def fits(line_count: int, characters: int, text: str) -> bool:
    """Whether one more line keeps the chunk within both sizes."""
    return (
        line_count < config.GEMINI_CHUNK_LINES
        and characters + 1 + len(text) <= config.GEMINI_CHUNK_CHARACTERS
    )
