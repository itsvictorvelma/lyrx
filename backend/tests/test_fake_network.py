"""Tests for the fake network the link tests rely on: scripted lookups, replies, and records."""

import socket

import httpx2
import pytest
from fake_network import PUBLIC_ADDRESS, FakeNetwork, UnscriptedRequestError, endless

LINK = "https://lyrics.example/song/1"


def pinned_request(url: str, address: str) -> httpx2.Request:
    """A request as `PinnedTransport` will hand it down: the IP in the URL, the host kept."""
    link = httpx2.URL(url)
    return httpx2.Request(
        "GET",
        link.copy_with(host=address),
        headers={"Host": link.host, "User-Agent": "test"},
        extensions={"sni_hostname": link.host},
    )


def test_fake_network_scripts_lookup_answers_per_call() -> None:
    network = FakeNetwork()
    network.answer("lyrics.example", [PUBLIC_ADDRESS], ["127.0.0.1"])

    assert network.resolve("lyrics.example", 443) == [PUBLIC_ADDRESS]
    assert network.resolve("lyrics.example", 443) == ["127.0.0.1"]
    assert network.resolve("lyrics.example", 443) == ["127.0.0.1"]
    assert network.lookups == [("lyrics.example", 443)] * 3


def test_fake_network_lookup_failure_raises_gaierror() -> None:
    network = FakeNetwork()
    network.answer("down.example", socket.gaierror(socket.EAI_NONAME, "unknown host"))

    with pytest.raises(socket.gaierror):
        network.resolve("nowhere.example", 443)
    with pytest.raises(socket.gaierror):
        network.resolve("down.example", 443)


def test_fake_network_records_the_dialed_address() -> None:
    network = FakeNetwork()
    network.publish(LINK, network.page("<p>君の声が</p>"))

    response = network.make_transport().handle_request(pinned_request(LINK, PUBLIC_ADDRESS))

    assert response.status_code == 200
    assert response.read().decode() == "<p>君の声が</p>"
    [seen] = network.requests
    assert (seen.method, seen.url, seen.dialed) == ("GET", LINK, PUBLIC_ADDRESS)
    assert seen.sni_hostname == "lyrics.example"
    assert seen.headers["Host"] == "lyrics.example"
    assert network.dialed == [PUBLIC_ADDRESS]


def test_fake_network_records_an_ipv6_dial_without_brackets() -> None:
    network = FakeNetwork()
    network.respond(LINK, network.page("x"))

    network.make_transport().handle_request(pinned_request(LINK, "2606:4700::1"))

    assert network.dialed == ["2606:4700::1"]


def test_fake_network_scripts_redirects_and_errors_per_url() -> None:
    network = FakeNetwork()
    network.respond(LINK, network.redirect("/song/2", headers={"Set-Cookie": "id=1"}))
    network.respond("https://lyrics.example/song/2", httpx2.ConnectError("refused"))
    transport = network.make_transport()

    response = transport.handle_request(pinned_request(LINK, PUBLIC_ADDRESS))
    assert (response.status_code, response.headers["Location"]) == (302, "/song/2")
    with pytest.raises(httpx2.ConnectError):
        transport.handle_request(pinned_request("https://lyrics.example/song/2", PUBLIC_ADDRESS))
    with pytest.raises(UnscriptedRequestError):
        transport.handle_request(pinned_request("https://lyrics.example/other", PUBLIC_ADDRESS))


def test_fake_network_records_chunks_only_as_they_are_read() -> None:
    network = FakeNetwork()
    page = network.chunked_page([b"a" * 10, b"b" * 10, b"c" * 10], headers={"Content-Length": "5"})
    network.respond(LINK, page)
    response = network.make_transport().handle_request(pinned_request(LINK, PUBLIC_ADDRESS))

    assert network.chunks_read == []
    chunks = response.iter_bytes()
    next(chunks)
    response.close()

    assert network.chunks_read == [b"a" * 10]
    assert response.headers["Content-Length"] == "5"


def test_fake_network_slow_body_pauses_before_each_chunk(monkeypatch: pytest.MonkeyPatch) -> None:
    pauses: list[float] = []
    monkeypatch.setattr("fake_network.time.sleep", pauses.append)
    network = FakeNetwork()
    network.respond(LINK, network.chunked_page(endless(b"x"), delay_seconds=0.25))
    response = network.make_transport().handle_request(pinned_request(LINK, PUBLIC_ADDRESS))

    chunks = response.iter_raw()
    next(chunks)
    next(chunks)

    assert pauses == [0.25, 0.25]
