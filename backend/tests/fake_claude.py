"""A fake Claude client that records each call and returns a set reply, with no network."""

from types import TracebackType
from typing import Any


class FakeMessageStream:
    """Stands in for the SDK's message stream: a context manager that hands back a set reply."""

    def __init__(self, final_message: object) -> None:
        self.final_message = final_message

    def __enter__(self) -> "FakeMessageStream":
        return self

    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        return None

    def get_final_message(self) -> object:
        return self.final_message


class FakeMessages:
    """Stands in for `client.messages`. Records every `stream(...)` call's keyword arguments.

    If `error` is set, `stream(...)` records the call and then raises it.
    Otherwise it returns a stream whose `get_final_message()` gives `final_message`.
    """

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.error: BaseException | None = None
        self.final_message: object = None

    def stream(self, **request: Any) -> FakeMessageStream:
        self.calls.append(request)
        if self.error is not None:
            raise self.error
        return FakeMessageStream(self.final_message)


class FakeClaudeClient:
    """Stands in for `anthropic.Anthropic`. No test ever reaches the Claude API or the network.

    Records: `messages.calls`, one dict of keyword arguments per `messages.stream(...)` call.
    Configure: `messages.error` (raised on call) or `messages.final_message` (returned reply).
    """

    def __init__(self) -> None:
        self.messages = FakeMessages()
