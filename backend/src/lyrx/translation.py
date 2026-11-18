"""Cuts a song's lines into chunks and translates each chunk with one Gemini call."""

import httpx2

from lyrx import config
from lyrx.gemini import NumberedLines, request_english
from lyrx.schemas import GeminiTranslation, TokenUsage


def translate_lines(
    lines: NumberedLines, api_key: str, transport: httpx2.BaseTransport
) -> GeminiTranslation:
    """Translates every chunk in order; the first failure propagates and nothing is kept."""
    english: dict[int, str] = {}
    input_tokens = 0
    output_tokens = 0
    for chunk in split_into_chunks(lines):
        result = request_english(chunk, api_key, transport)
        english.update(result.english)
        input_tokens += result.usage.input_tokens
        output_tokens += result.usage.output_tokens
    return GeminiTranslation(
        english=english,
        usage=TokenUsage(input_tokens=input_tokens, output_tokens=output_tokens),
    )


def split_into_chunks(lines: NumberedLines) -> list[NumberedLines]:
    """Consecutive chunks, each as large as both chunk sizes allow."""
    chunks: list[list[tuple[int, str]]] = []
    characters = 0
    for line in lines:
        if chunks and fits(len(chunks[-1]), characters, line[1]):
            characters += 1 + len(line[1])
            chunks[-1].append(line)
        else:
            chunks.append([line])
            characters = len(line[1])
    return list(chunks)


def fits(line_count: int, characters: int, text: str) -> bool:
    """Whether one more line keeps the chunk within both sizes."""
    return (
        line_count < config.GEMINI_CHUNK_LINES
        and characters + 1 + len(text) <= config.GEMINI_CHUNK_CHARACTERS
    )
