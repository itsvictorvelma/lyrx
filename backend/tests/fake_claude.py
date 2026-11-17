"""A fake Claude client that records each call and returns a set reply, with no network."""

from types import TracebackType
from typing import Any, Literal, get_args

from anthropic.types import Message, TextBlock, ThinkingBlock, Usage

# Where a set error is raised, mirroring the SDK: `stream(...)` builds the manager, entering the
# `with` sends the request, and `get_final_message()` reads the rest of the stream.
ErrorPoint = Literal["call", "enter", "final"]

KNOWN_STOP_REASONS = frozenset(
    get_args(get_args(Message.model_fields["stop_reason"].annotation)[0])
)


def fake_message(
    text: str | list[str] | None, stop_reason: str = "end_turn", thinking: bool = False
) -> Message:
    """A real SDK `Message`: one text block per string (none if None), optionally after thinking.

    A stop reason the SDK does not know (e.g. "other") is set without validation.
    """
    content: list[TextBlock | ThinkingBlock] = []
    if thinking:
        content.append(
            ThinkingBlock(type="thinking", thinking='{"lines": "not the reply"}', signature="sig")
        )
    texts = [] if text is None else [text] if isinstance(text, str) else text
    content += [TextBlock(type="text", text=part) for part in texts]
    fields: dict[str, Any] = {
        "id": "msg_fake",
        "type": "message",
        "role": "assistant",
        "model": "claude-opus-5-5",
        "content": content,
        "stop_reason": stop_reason,
        "stop_sequence": None,
        "usage": Usage(input_tokens=100, output_tokens=50),
    }
    if stop_reason in KNOWN_STOP_REASONS:
        return Message.model_validate(fields)
    return Message.model_construct(**fields)


class FakeMessageStream:
    """Stands in for the SDK's message stream: a context manager that hands back a set reply."""

    def __init__(
        self,
        final_message: Message | None,
        error: BaseException | None = None,
        error_point: ErrorPoint = "call",
    ) -> None:
        self.final_message = final_message
        self.error = error
        self.error_point = error_point

    def __enter__(self) -> "FakeMessageStream":
        if self.error is not None and self.error_point == "enter":
            raise self.error
        return self

    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        return None

    def get_final_message(self) -> Message:
        if self.error is not None and self.error_point == "final":
            raise self.error
        assert self.final_message is not None, "set messages.final_message with fake_message()"
        return self.final_message


class FakeMessages:
    """Stands in for `client.messages`. Records every `stream(...)` call's keyword arguments.

    If `error` is set, it is raised at `error_point`: on the `stream(...)` call itself (the
    default), on entering the `with`, or on `get_final_message()`. The call is recorded first.
    Otherwise the stream's `get_final_message()` gives `final_message`.
    """

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.error: BaseException | None = None
        self.error_point: ErrorPoint = "call"
        self.final_message: Message | None = None

    def stream(self, **request: Any) -> FakeMessageStream:
        self.calls.append(request)
        if self.error is not None and self.error_point == "call":
            raise self.error
        return FakeMessageStream(self.final_message, self.error, self.error_point)


class FakeClaudeClient:
    """Stands in for `anthropic.Anthropic`. No test ever reaches the Claude API or the network.

    Records: `messages.calls`, one dict of keyword arguments per `messages.stream(...)` call.
    Configure: `messages.error` and `messages.error_point` (raised on call, enter, or final
    message), or `messages.final_message` (the returned reply, e.g. from `fake_message`).
    """

    def __init__(self) -> None:
        self.messages = FakeMessages()
