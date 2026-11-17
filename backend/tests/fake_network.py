"""The fake network for link tests: a scripted DNS lookup and a scripted web, with no real socket.

`FakeNetwork.resolve` stands in for the server's lookup, and `FakeNetwork.make_transport()`
gives an `httpx2.MockTransport` that the server's `PinnedTransport` wraps. The fake sees each
request as the pinned transport sends it: the checked IP address in the URL, the host name in
the `Host` header, and the host name again in the `sni_hostname` extension.
"""

import socket
import time
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass, field

import httpx2

# A globally routable address, so it passes the private-address check. The documentation ranges
# (203.0.113/24 and friends) are not global in Python's `ipaddress`. No packet is ever sent here.
PUBLIC_ADDRESS = "93.184.215.14"

# How long an endless slow body keeps sending before it gives up, so a broken deadline makes a
# test fail instead of hang.
SLOW_BODY_SAFETY_SECONDS = 5.0

# One scripted DNS answer: the addresses returned, or an exception to raise.
Answer = Sequence[str] | BaseException
# One scripted reply to a request: a response, or an httpx2 exception to raise.
Reply = httpx2.Response | httpx2.RequestError


class UnscriptedRequestError(AssertionError):
    """The fake web got a request for a URL no test scripted."""


@dataclass(frozen=True)
class SeenRequest:
    """One request the fake web received.

    `url` is the link as the learner sees it (host name, no fragment). `dialed` is the host in
    the URL the transport received: the IP address the connection would go to.
    """

    method: str
    url: str
    headers: httpx2.Headers
    dialed: str
    sni_hostname: str | None


class ChunkedBody(httpx2.SyncByteStream):
    """A response body sent in the given chunks, optionally with a pause before each one.

    Every chunk handed out is appended to `chunks_read`, so a test can see how far the server
    read. `closed` tells whether the server closed the body.
    """

    def __init__(
        self, chunks: Iterable[bytes], chunks_read: list[bytes], delay_seconds: float = 0.0
    ) -> None:
        self.chunks = chunks
        self.chunks_read = chunks_read
        self.delay_seconds = delay_seconds
        # T4 and T5 check that the fetch closes every response, read or not (plan.md, The fetch).
        self.closed = False

    def __iter__(self) -> Iterator[bytes]:
        for chunk in self.chunks:
            if self.delay_seconds:
                time.sleep(self.delay_seconds)
            self.chunks_read.append(chunk)
            yield chunk

    def close(self) -> None:
        self.closed = True


def endless(chunk: bytes) -> Iterator[bytes]:
    """The same chunk again and again, until the safety limit runs out."""
    give_up_at = time.monotonic() + SLOW_BODY_SAFETY_SECONDS
    while time.monotonic() < give_up_at:
        yield chunk


@dataclass
class FakeNetwork:
    """Scripted DNS answers per host and scripted replies per URL. Records everything it sees.

    Records: `lookups` (host, port) per lookup; `requests` (`SeenRequest`) per request;
    `chunks_read`, every body chunk handed to the server, in order.
    """

    lookups: list[tuple[str, int]] = field(default_factory=list)
    requests: list[SeenRequest] = field(default_factory=list)
    chunks_read: list[bytes] = field(default_factory=list)
    answers: dict[str, list[Answer]] = field(default_factory=dict)
    replies: dict[str, list[Reply]] = field(default_factory=dict)

    @property
    def dialed(self) -> list[str]:
        """The connection target of each request, in order."""
        return [request.dialed for request in self.requests]

    def answer(self, host: str, *answers: Answer) -> None:
        """Scripts the lookup of `host`: one answer per lookup, and the last one repeats."""
        self.answers[host] = list(answers)

    def respond(self, url: str, *replies: Reply) -> None:
        """Scripts the replies for `url`: one per request, and the last one repeats.

        A response body can be read only once, so script a fresh page for each request that reads.
        """
        self.replies[str(httpx2.URL(url))] = list(replies)

    def publish(self, url: str, *replies: Reply) -> None:
        """Scripts `url`'s replies, and a lookup of its host that answers `PUBLIC_ADDRESS`."""
        self.answer(httpx2.URL(url).host, [PUBLIC_ADDRESS])
        self.respond(url, *replies)

    def resolve(self, host: str, port: int) -> list[str]:
        """The fake lookup. An unscripted host fails as a real unknown host does."""
        self.lookups.append((host, port))
        answers = self.answers.get(host)
        if not answers:
            raise socket.gaierror(socket.EAI_NONAME, "unknown host")
        answer = answers.pop(0) if len(answers) > 1 else answers[0]
        if isinstance(answer, BaseException):
            raise answer
        return list(answer)

    def make_transport(self) -> httpx2.MockTransport:
        """A transport that answers from the script. A new one may be made for each fetch."""
        return httpx2.MockTransport(self.handle)

    def handle(self, request: httpx2.Request) -> httpx2.Response:
        seen = see_request(request)
        self.requests.append(seen)
        replies = self.replies.get(seen.url)
        if not replies:
            raise UnscriptedRequestError(f"no reply scripted for {seen.url}")
        reply = replies.pop(0) if len(replies) > 1 else replies[0]
        if isinstance(reply, httpx2.RequestError):
            raise reply
        return reply

    def page(
        self,
        body: bytes | str,
        content_type: str | None = "text/html; charset=utf-8",
        status: int = 200,
        headers: dict[str, str] | None = None,
    ) -> httpx2.Response:
        """A whole-body response. A `str` body is sent as UTF-8. `None` sends no Content-Type."""
        content = body.encode() if isinstance(body, str) else body
        return self.chunked_page([content], content_type, status, headers)

    def chunked_page(
        self,
        chunks: Iterable[bytes],
        content_type: str | None = "text/html; charset=utf-8",
        status: int = 200,
        headers: dict[str, str] | None = None,
        delay_seconds: float = 0.0,
    ) -> httpx2.Response:
        """A response whose body streams in `chunks`, recorded in `chunks_read` as it is read.

        No `Content-Length` is added: pass one in `headers` to send it (true or false).
        """
        all_headers = {} if content_type is None else {"Content-Type": content_type}
        all_headers.update(headers or {})
        body = ChunkedBody(chunks, self.chunks_read, delay_seconds)
        return httpx2.Response(status, headers=all_headers, stream=body)

    def redirect(
        self, location: str, status: int = 302, headers: dict[str, str] | None = None
    ) -> httpx2.Response:
        """A redirect to `location`, with no body."""
        return self.chunked_page([], None, status, {"Location": location, **(headers or {})})


def see_request(request: httpx2.Request) -> SeenRequest:
    """What the fake records: the learner's URL is rebuilt from the `Host` header."""
    host_header = request.headers.get("Host", request.url.netloc.decode("ascii"))
    url = f"{request.url.scheme}://{host_header}{request.url.raw_path.decode('ascii')}"
    sni_hostname = request.extensions.get("sni_hostname")
    return SeenRequest(
        method=request.method,
        url=str(httpx2.URL(url)),
        headers=request.headers,
        dialed=request.url.host,
        sni_hostname=sni_hostname if isinstance(sni_hostname, str) else None,
    )
