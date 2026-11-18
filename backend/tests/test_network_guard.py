"""Tests for the test-wide network guard: a real lookup or connection is refused and recorded."""

import socket
from collections.abc import Callable

import pytest
from network_guard import NetworkGuard, RealNetworkError

ADDRESS = ("93.184.215.14", 443)


def open_with_connect(address: tuple[str, int]) -> object:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect(address)
        return None


def open_with_connect_ex(address: tuple[str, int]) -> object:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        return sock.connect_ex(address)


def open_with_create_connection(address: tuple[str, int]) -> object:
    # Looked up at call time: the guard replaces `socket.create_connection` for each test.
    return socket.create_connection(address)


def test_ac57_a_real_lookup_trips_the_guard(network_guard: NetworkGuard) -> None:
    with pytest.raises(RealNetworkError):
        socket.getaddrinfo("lyrics.example", 443)
    assert network_guard.attempts == ["socket.getaddrinfo"]
    network_guard.attempts.clear()


def test_ac57_gethostbyname_trips_the_guard(network_guard: NetworkGuard) -> None:
    with pytest.raises(RealNetworkError):
        socket.gethostbyname("lyrics.example")
    assert network_guard.attempts == ["socket.gethostbyname"]
    network_guard.attempts.clear()


@pytest.mark.parametrize(
    ("connect", "name"),
    [
        (open_with_connect, "socket.socket.connect"),
        (open_with_connect_ex, "socket.socket.connect_ex"),
        (open_with_create_connection, "socket.create_connection"),
    ],
)
def test_ac57_a_real_connection_trips_the_guard(
    network_guard: NetworkGuard, connect: Callable[[tuple[str, int]], object], name: str
) -> None:
    with pytest.raises(RealNetworkError):
        connect(ADDRESS)
    assert network_guard.attempts == [name]
    network_guard.attempts.clear()


def test_ac57_a_caught_attempt_still_fails_the_test(pytester: pytest.Pytester) -> None:
    # The server maps unexpected errors to a 500, so the guard must fail the test at teardown.
    pytester.makeconftest('pytest_plugins = ["network_guard"]')
    pytester.makepyfile(
        """
        import socket

        def test_swallows_the_error():
            try:
                socket.getaddrinfo("lyrics.example", 443)
            except AssertionError:
                pass
        """
    )
    result = pytester.runpytest_inprocess()
    result.assert_outcomes(passed=1, errors=1)
    result.stdout.fnmatch_lines(["*the test used the real network*socket.getaddrinfo*"])
