"""A test-wide guard: any real DNS lookup or outgoing socket connection is recorded and refused."""

import socket
from collections.abc import Iterator
from typing import Any

import pytest


class RealNetworkError(AssertionError):
    """Raised when a test tries to reach the real network. Tests use the fakes instead."""


class NetworkGuard:
    """Replaces the socket functions that reach the network. Each attempt is recorded and raises.

    Raising alone is not enough: the server turns an unexpected exception into a 500, so the
    fixture also fails the test at teardown if `attempts` is not empty.
    """

    def __init__(self) -> None:
        self.attempts: list[str] = []

    def install(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # ponytail: UDP `sendto`/`sendmsg` are not patched; no installed library sends with them
        # today. Upgrade path: patch them too if a dependency starts to.
        monkeypatch.setattr(socket, "getaddrinfo", self.refuse("socket.getaddrinfo"))
        monkeypatch.setattr(socket, "gethostbyname", self.refuse("socket.gethostbyname"))
        monkeypatch.setattr(socket, "gethostbyname_ex", self.refuse("socket.gethostbyname_ex"))
        monkeypatch.setattr(socket, "gethostbyaddr", self.refuse("socket.gethostbyaddr"))
        monkeypatch.setattr(socket, "getnameinfo", self.refuse("socket.getnameinfo"))
        monkeypatch.setattr(socket, "create_connection", self.refuse("socket.create_connection"))
        monkeypatch.setattr(socket.socket, "connect", self.refuse("socket.socket.connect"))
        monkeypatch.setattr(socket.socket, "connect_ex", self.refuse("socket.socket.connect_ex"))

    def refuse(self, name: str) -> Any:
        """A stand-in for `name` that records the attempt and raises `RealNetworkError`."""

        def refuse_network(*args: object, **kwargs: object) -> Any:
            self.attempts.append(name)
            raise RealNetworkError(f"{name} was called: tests must use the fake network")

        return refuse_network


@pytest.fixture(autouse=True)
def network_guard(monkeypatch: pytest.MonkeyPatch) -> Iterator[NetworkGuard]:
    """Every test: a real lookup or connection raises, and fails the test even if caught."""
    guard = NetworkGuard()
    guard.install(monkeypatch)
    yield guard
    if guard.attempts:
        pytest.fail(f"the test used the real network: {guard.attempts}", pytrace=False)
