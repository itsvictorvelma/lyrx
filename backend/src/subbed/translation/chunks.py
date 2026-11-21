"""Cuts a song into chunks, asks the translators for them at the same time, and retries."""

import time
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

from subbed import config
from subbed.errors import ApiError
from subbed.translation.chain import ReadyTranslator, request_versions
from subbed.translation.prompt import NumberedLines
from subbed.translation.results import LineVersions, SongTranslation, TokenUsage

# A line that still fails the checks after it was asked again is shown without versions.
MISSING = LineVersions(hiragana="", romaji="", english="")

# Overloaded, timed out, or an unusable reply: worth one more try. A rate limit (429) is not,
# since every retry would spend more of the free quota; a block is the translator's decision; and a
# refused request (another 4xx) would be refused again.
RETRYABLE_CODES = frozenset({"translation_unavailable", "translation_invalid"})


@dataclass
class ChunkResult:
    """One chunk's lines and what it took: calls, retries, tokens, missing lines, who answered."""

    lines: dict[int, LineVersions]
    calls: int
    retries: int
    input_tokens: int
    output_tokens: int
    missing_lines: int
    answered_by: set[str]


def request_in_chunks(
    lines: NumberedLines,
    translators: Sequence[ReadyTranslator],
    whole_song: NumberedLines | None = None,
) -> SongTranslation:
    """All chunks at once; if any chunk fails for good, the whole song fails with its error.

    `whole_song` is the context when `lines` are only some of the song's lines.
    """
    started = time.monotonic()
    context = song_context(lines if whole_song is None else whole_song)

    def request_chunk(chunk: NumberedLines) -> ChunkResult:
        return request_one_chunk(chunk if context is None else context, chunk, translators)

    results = run_all_or_stop(request_chunk, split_into_chunks(lines))
    versions: dict[int, LineVersions] = {}
    for result in results:
        versions.update(result.lines)
    return SongTranslation(
        lines=versions,
        usage=TokenUsage(
            input_tokens=sum(result.input_tokens for result in results),
            output_tokens=sum(result.output_tokens for result in results),
        ),
        calls=sum(result.calls for result in results),
        retries=sum(result.retries for result in results),
        missing_lines=sum(result.missing_lines for result in results),
        elapsed_ms=round((time.monotonic() - started) * 1000),
        translators=tuple(
            translator.name
            for translator in translators
            if any(translator.name in result.answered_by for result in results)
        ),
    )


def run_all_or_stop(
    request_chunk: Callable[[NumberedLines], ChunkResult], chunks: list[list[tuple[int, str]]]
) -> list[ChunkResult]:
    """Every chunk's result, a few at a time. The first chunk to fail for good stops the song:
    chunks not yet sent are cancelled and its error propagates, so no more quota is spent."""
    pool = ThreadPoolExecutor(max_workers=config.PARALLEL_REQUESTS)
    try:
        futures = [pool.submit(request_chunk, chunk) for chunk in chunks]
        for future in as_completed(futures):
            future.result()
        return [future.result() for future in futures]
    finally:
        # On success every chunk is done; on a failure, do not wait for requests in flight.
        pool.shutdown(wait=False, cancel_futures=True)


def song_context(lines: NumberedLines) -> NumberedLines | None:
    """The whole song, sent with every chunk for context, unless it is very long."""
    characters = len("\n".join(text for _, text in lines))
    return lines if characters <= config.CONTEXT_MAX_CHARACTERS else None


def request_one_chunk(
    context: NumberedLines,
    chunk: NumberedLines,
    translators: Sequence[ReadyTranslator],
) -> ChunkResult:
    """The chunk's lines; lines that fail the checks are asked once more, on their own."""
    first, first_retries = with_retries(lambda: request_versions(context, chunk, translators))
    lines = dict(first.lines)
    calls, retries = 1 + first_retries, first_retries
    input_tokens, output_tokens = first.usage.input_tokens, first.usage.output_tokens
    answered_by = {first.translator}
    bad = [line for line in chunk if line[0] in first.bad_indexes]
    if bad:
        second, second_retries = with_retries(lambda: request_versions(context, bad, translators))
        lines.update(second.lines)
        answered_by.add(second.translator)
        calls, retries = calls + 1 + second_retries, retries + second_retries
        input_tokens += second.usage.input_tokens
        output_tokens += second.usage.output_tokens
    missing = [index for index, _ in chunk if index not in lines]
    lines.update(dict.fromkeys(missing, MISSING))
    return ChunkResult(
        lines, calls, retries, input_tokens, output_tokens, len(missing), answered_by
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
    return line_count < config.CHUNK_LINES and characters + 1 + len(text) <= config.CHUNK_CHARACTERS


def is_temporary(error: ApiError) -> bool:
    """Whether trying again could help."""
    refused = error.reason is not None and error.reason.startswith("http_4")
    return error.code in RETRYABLE_CODES and not refused


def with_retries[Result](request: Callable[[], Result]) -> tuple[Result, int]:
    """The request's result and how many retries it took; the last error propagates."""
    for retries, wait_seconds in enumerate(config.RETRY_WAIT_SECONDS):
        try:
            return request(), retries
        except ApiError as error:
            if not is_temporary(error):
                raise
        time.sleep(wait_seconds)
    return request(), len(config.RETRY_WAIT_SECONDS)
