"""Tests for the Host check: only 127.0.0.1 and localhost pass, before routing or the body cap."""

import json

import pytest
from error_shape import assert_error_shape
from fake_gemini import FakeGemini
from fastapi.testclient import TestClient

from lyrx.app import SONG_SEARCH_PATH


@pytest.mark.parametrize(
    "host",
    [
        "",
        "evil.example",
        "evil.example:8000",
        "localhost.evil.example",
        "127.0.0.1.evil.example",
        "0.0.0.0:8000",
    ],
)
def test_ac30_foreign_host_is_rejected(client: TestClient, host: str) -> None:
    response = client.post(SONG_SEARCH_PATH, json={"query": "夜の月"}, headers={"Host": host})

    assert response.status_code == 403
    assert_error_shape(response.json(), "host_not_allowed")


def test_ac30_foreign_host_is_rejected_before_routing(client: TestClient) -> None:
    response = client.get("/no-such-page", headers={"Host": "evil.example"})

    assert response.status_code == 403
    assert_error_shape(response.json(), "host_not_allowed")


@pytest.mark.parametrize(
    "host", ["127.0.0.1", "127.0.0.1:8000", "localhost", "localhost:8000", "localhost:5173"]
)
def test_ac30_local_host_passes_the_host_check(client: TestClient, host: str) -> None:
    # A body without `query` keeps the request away from LRCLIB; only the Host check matters.
    response = client.post(SONG_SEARCH_PATH, json={}, headers={"Host": host})

    assert response.status_code == 400
    assert_error_shape(response.json(), "invalid_request")


def test_ac30_foreign_host_is_rejected_before_the_body_size_cap(
    client: TestClient, fake_gemini: FakeGemini
) -> None:
    oversized_body = json.dumps({"query": "夜の月" * 30_000}).encode()
    assert len(oversized_body) > 70_000

    response = client.post(
        SONG_SEARCH_PATH,
        content=oversized_body,
        headers={"Content-Type": "application/json", "Host": "evil.example"},
    )

    assert response.status_code == 403
    assert_error_shape(response.json(), "host_not_allowed")
    assert fake_gemini.requests == []
