"""The translator chain: which translators have a key, and one request walked down the chain."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

import httpx2

from lyrx import config
from lyrx.errors import ApiError
from lyrx.gemini import ask_gemini
from lyrx.groq import ask_groq
from lyrx.lines import has_japanese
from lyrx.reply_checks import line_is_valid, line_versions, parse_reply_lines
from lyrx.schemas import ChunkReply, LineVersions, TranslatorReply
from lyrx.translation_prompt import NumberedLines

# Failures that say "this translator is busy or out of reach", so the next one may answer.
BUSY_REASONS = frozenset({"http_429", "http_503", "timeout", "connect_error"})


@dataclass(frozen=True)
class ReadyTranslator:
    """A translator from the chain with its key and its service's shared HTTP client."""

    name: str
    service: str
    model: str
    api_key: str = field(repr=False)
    client: httpx2.Client = field(repr=False)


def ready_translators(clients: Mapping[str, httpx2.Client]) -> list[ReadyTranslator]:
    """The chain in order, without translators whose key is not set; keys are read now."""
    keys = {"groq": config.read_groq_key(), "gemini": config.read_gemini_key()}
    ready = [
        ReadyTranslator(
            translator.name, translator.service, translator.model, key, clients[translator.service]
        )
        for translator in config.TRANSLATORS
        if (key := keys[translator.service]) is not None
    ]
    if not ready:
        raise ApiError("server_not_configured")
    return ready


def request_versions(
    context: NumberedLines, wanted: NumberedLines, translators: Sequence[ReadyTranslator]
) -> ChunkReply:
    """One request for the `wanted` lines, with `context` as the song around them.

    A reply that is not usable at all raises an `ApiError`. A usable reply with some bad or
    missing lines returns the good ones and lists the bad indexes, so only those are asked again.
    """
    reply, translator = ask_down_the_chain(context, wanted, translators)
    reply_lines = parse_reply_lines(reply.text)
    good: dict[int, LineVersions] = {}
    bad: list[int] = []
    for index, text in wanted:
        reply_line = reply_lines.get(index)
        if not has_japanese(text):
            good[index] = LineVersions(hiragana=text, romaji=text, english=text)
        elif reply_line is not None and line_is_valid(reply_line, text):
            good[index] = line_versions(reply_line, text)
        else:
            bad.append(index)
    return ChunkReply(lines=good, bad_indexes=bad, usage=reply.usage, translator=translator.name)


def ask_down_the_chain(
    context: NumberedLines, wanted: NumberedLines, translators: Sequence[ReadyTranslator]
) -> tuple[TranslatorReply, ReadyTranslator]:
    """The first answer, moving on only while translators are busy; else the error stands."""
    *earlier, last = translators
    for translator in earlier:
        try:
            return ask(translator, context, wanted), translator
        except ApiError as error:
            if error.reason not in BUSY_REASONS:
                raise
    return ask(last, context, wanted), last


def ask(
    translator: ReadyTranslator, context: NumberedLines, wanted: NumberedLines
) -> TranslatorReply:
    """One request to one translator."""
    ask_service = ask_groq if translator.service == "groq" else ask_gemini
    return ask_service(translator.model, translator.api_key, translator.client, context, wanted)
