"""The one Claude call for a paste, and the checks on its reply before it is used."""

import json
from collections.abc import Iterable, Sequence
from types import TracebackType
from typing import Any, Protocol

import anthropic
import httpx2
from anthropic.types import Message, MessageParam, OutputConfigParam, TextBlock
from pydantic import ValidationError

from lyrx import config
from lyrx.errors import ApiError
from lyrx.lines import has_japanese
from lyrx.prompt import SYSTEM_PROMPT, build_user_message
from lyrx.schemas import ClaudeReply, ReplyLine

NumberedLines = Sequence[tuple[int, str]]

REPLY_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "lines": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "index": {"type": "integer"},
                    "reading": {"type": "string"},
                    "english": {"type": "string"},
                },
                "required": ["index", "reading", "english"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["lines"],
    "additionalProperties": False,
}


class MessageStream(Protocol):
    """The open stream: it gives the final message once the reply is complete."""

    def get_final_message(self) -> Message: ...


class MessageStreamManager(Protocol):
    """What `messages.stream(...)` returns: a context manager around the stream."""

    def __enter__(self) -> MessageStream: ...

    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...


class Messages(Protocol):
    """The part of `client.messages` this module uses."""

    def stream(
        self,
        *,
        model: str,
        max_tokens: int,
        system: str,
        messages: Iterable[MessageParam],
        output_config: OutputConfigParam,
    ) -> MessageStreamManager: ...


class ClaudeClient(Protocol):
    """The SDK client, or a fake with the same `messages.stream(...)`."""

    @property
    def messages(self) -> Messages: ...


def make_client(api_key: str) -> anthropic.Anthropic:
    """The real SDK client, with the request timeout and the SDK's default retries."""
    return anthropic.Anthropic(api_key=api_key, timeout=config.REQUEST_TIMEOUT_SECONDS)


def request_readings(client: ClaudeClient, lines: NumberedLines) -> list[ReplyLine]:
    """Sends the lines in one call and returns the checked reply, one entry per sent line."""
    message = send_request(client, lines)
    check_stop_reason(message)
    reply = parse_reply(join_text_blocks(message))
    check_indexes(reply, lines)
    check_english(reply, lines)
    return reply.lines


def send_request(client: ClaudeClient, lines: NumberedLines) -> Message:
    """Exactly one completion. An SDK error becomes model_unavailable, without its text."""
    try:
        with client.messages.stream(
            model=config.MODEL,
            max_tokens=config.MAX_TOKENS,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": build_user_message(lines)}],
            output_config={
                "effort": config.EFFORT,
                "format": {"type": "json_schema", "schema": REPLY_SCHEMA},
            },
        ) as stream:
            return stream.get_final_message()
    except (anthropic.APIStatusError, anthropic.APIConnectionError, httpx2.TransportError):
        # APIConnectionError includes timeouts. The SDK lets a raw TransportError through
        # when a streamed reply breaks or times out after the headers arrive.
        raise ApiError("model_unavailable") from None


def check_stop_reason(message: Message) -> None:
    """Only `end_turn` gives a usable reply; refusal and truncation have their own codes."""
    if message.stop_reason == "refusal":
        raise ApiError("model_refused")
    if message.stop_reason == "max_tokens":
        raise ApiError("model_output_truncated")
    if message.stop_reason != "end_turn":
        raise ApiError("model_output_invalid")


def join_text_blocks(message: Message) -> str:
    """The text blocks joined in order. Thinking blocks are skipped."""
    return "".join(block.text for block in message.content if isinstance(block, TextBlock))


def parse_reply(text: str) -> ClaudeReply:
    """Parses and validates the reply; deeply nested JSON is invalid, not a crash."""
    try:
        return ClaudeReply.model_validate(json.loads(text))
    except (json.JSONDecodeError, RecursionError, ValidationError):
        raise ApiError("model_output_invalid") from None


def check_indexes(reply: ClaudeReply, lines: NumberedLines) -> None:
    """The indexes must be exactly the sent ones, each once, in order."""
    if [line.index for line in reply.lines] != [index for index, _ in lines]:
        raise ApiError("model_output_invalid")


def check_english(reply: ClaudeReply, lines: NumberedLines) -> None:
    """A Japanese line needs a non-blank English line. Lines are already matched by index."""
    for reply_line, (_, text) in zip(reply.lines, lines, strict=True):
        if has_japanese(text) and not reply_line.english.strip():
            raise ApiError("model_output_invalid")
