"""Tests for the app shell: the error shape, routing errors, sync routes, and who sees what
(spec 014: guests, two people, and the daily caps), health, the proxy, and the built page
(spec 020)."""

import inspect
from pathlib import Path
from typing import Any, cast

import pytest
from conftest import make_client, sign_up
from error_shape import ERROR_SHAPE_KEYS, assert_error_shape
from fake_gemini import FakeGemini, answer_with_placeholders
from fake_lrclib import FakeLrclib, json_reply, record
from fastapi import FastAPI, HTTPException, Request
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from starlette.types import ASGIApp
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from lyrx import config, library
from lyrx.app import (
    HEALTH_PATH,
    PLAYBACK_PATH,
    RECENT_SONGS_PATH,
    SAVED_SONG_PATH,
    SAVED_SONGS_PATH,
    SONG_SEARCH_PATH,
    SONG_VERSIONS_PATH,
    page_file,
)
from lyrx.rate_limits import peer_address

VIDEO_A = "aaaaaaaaaaa"
VIDEO_B = "bbbbbbbbbbb"


def test_ac9_body_that_is_not_json_is_invalid_request(client: TestClient) -> None:
    response = client.post(
        SONG_SEARCH_PATH,
        content=b"{not json at all",
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 400
    assert_error_shape(response.json(), "invalid_request")


def test_body_without_query_is_invalid_request(client: TestClient) -> None:
    response = client.post(SONG_SEARCH_PATH, json={"text": "ほしが ひかる"})

    assert response.status_code == 400
    assert_error_shape(response.json(), "invalid_request")


@pytest.mark.parametrize("query", [42, 3.5, None, ["ほしが ひかる"], {"line": "そら"}])
def test_query_that_is_not_a_string_is_invalid_request(client: TestClient, query: object) -> None:
    response = client.post(SONG_SEARCH_PATH, json={"query": query})

    assert response.status_code == 400
    assert_error_shape(response.json(), "invalid_request")


def test_ac32_unexpected_exception_is_internal_error_without_leaks(
    app: FastAPI, client: TestClient
) -> None:
    exception_text = "secret-path /Users/someone/lyrx/src/lyrx/app.py boom"

    def raise_unexpected_error() -> None:
        raise RuntimeError(exception_text)

    app.add_api_route("/api/raise-unexpected-error", raise_unexpected_error, methods=["GET"])

    response = client.get("/api/raise-unexpected-error")

    assert response.status_code == 500
    assert_error_shape(response.json(), "internal_error")
    for leaked in (exception_text, "secret-path", "/Users", "boom", "Traceback", "RuntimeError"):
        assert leaked not in response.text


def test_ac42_unknown_path_is_not_found_in_the_error_shape(client: TestClient) -> None:
    response = client.get("/api/no-such-route")

    assert response.status_code == 404
    assert_error_shape(response.json(), "not_found")
    assert set(response.json()) <= ERROR_SHAPE_KEYS


def test_ac42_unknown_path_with_post_is_not_found(client: TestClient) -> None:
    response = client.post("/api/no-such-route", json={"query": "夜の月"})

    assert response.status_code == 404
    assert_error_shape(response.json(), "not_found")


@pytest.mark.parametrize("path", ["/docs", "/redoc", "/openapi.json"])
def test_ac42_api_docs_pages_are_disabled_and_not_found(client: TestClient, path: str) -> None:
    """The docs pages would load assets from a CDN, so the app turns them off."""
    response = client.get(path)

    assert response.status_code == 404
    assert_error_shape(response.json(), "not_found")


def test_ac42_get_on_search_route_is_method_not_allowed(client: TestClient) -> None:
    response = client.get(SONG_SEARCH_PATH)

    assert response.status_code == 405
    assert_error_shape(response.json(), "method_not_allowed")
    assert set(response.json()) <= ERROR_SHAPE_KEYS


@pytest.mark.parametrize(
    ("raised_status", "expected_status", "expected_code"),
    [(418, 400, "invalid_request"), (503, 500, "internal_error")],
)
def test_ac44_other_http_exceptions_map_to_the_error_shape_without_their_detail(
    app: FastAPI,
    client: TestClient,
    raised_status: int,
    expected_status: int,
    expected_code: str,
) -> None:
    # Spec amendment: other client errors are invalid_request; a server error leaks nothing.
    def raise_http_exception() -> None:
        raise HTTPException(raised_status, detail="secret-detail")

    app.add_api_route("/api/raise-http-exception", raise_http_exception, methods=["GET"])

    response = client.get("/api/raise-http-exception")

    assert response.status_code == expected_status
    assert_error_shape(response.json(), expected_code)
    assert "secret-detail" not in response.text


# The routes run in FastAPI's threadpool.


@pytest.mark.parametrize(
    "path", [SONG_SEARCH_PATH, SONG_VERSIONS_PATH, SAVED_SONGS_PATH, SAVED_SONG_PATH]
)
def test_routes_are_sync_functions_so_blocking_calls_run_off_the_event_loop(
    app: FastAPI, path: str
) -> None:
    routes = [route for route in app.routes if isinstance(route, APIRoute) and route.path == path]

    assert routes
    assert not any(inspect.iscoroutinefunction(route.endpoint) for route in routes)


# Accounts (spec 014)


def open_new_song(
    client: TestClient, fake_lrclib: FakeLrclib, fake_gemini: FakeGemini, song_id: int
) -> Any:
    fake_lrclib.script(json_reply(record(record_id=song_id, track=f"歌{song_id}")))
    fake_gemini.answer = answer_with_placeholders
    return client.post(SONG_VERSIONS_PATH, json={"id": song_id})


def save(client: TestClient, song_id: int, video_id: str | None) -> int:
    path = SAVED_SONG_PATH.format(song_id=song_id)
    return client.put(path, json={"videoId": video_id, "offsetMs": 0}).status_code


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", SAVED_SONGS_PATH),
        ("PUT", SAVED_SONG_PATH.format(song_id=101)),
        ("DELETE", SAVED_SONG_PATH.format(song_id=101)),
        ("PUT", PLAYBACK_PATH.format(song_id=101)),
    ],
)
def test_ac5_a_guest_gets_sign_in_required_on_the_saved_songs_routes(
    client: TestClient, method: str, path: str
) -> None:
    response = client.request(method, path, json={"videoId": None, "offsetMs": 0})

    assert response.status_code == 401
    assert_error_shape(response.json(), "sign_in_required")


@pytest.mark.usefixtures("gemini_key")
def test_ac5_a_guest_opens_songs_and_never_sees_another_persons_video(
    app: FastAPI, client: TestClient, fake_lrclib: FakeLrclib, fake_gemini: FakeGemini
) -> None:
    with make_client(app) as owner:
        sign_up(owner)
        assert open_new_song(owner, fake_lrclib, fake_gemini, 101).status_code == 200
        assert save(owner, 101, VIDEO_A) == 204

    opened = client.post(SONG_VERSIONS_PATH, json={"id": 101}).json()
    recent = client.get(RECENT_SONGS_PATH)

    assert (opened["saved"], opened["playback"]["videoId"]) == (False, None)
    assert recent.status_code == 200
    assert [(song["id"], song["videoId"]) for song in recent.json()["songs"]] == [(101, None)]


@pytest.mark.usefixtures("gemini_key")
def test_ac6_two_people_each_see_only_their_own_songs_and_videos(
    app: FastAPI, fake_lrclib: FakeLrclib, fake_gemini: FakeGemini
) -> None:
    with make_client(app) as first, make_client(app) as second:
        sign_up(first, "first")
        sign_up(second, "second")
        open_new_song(first, fake_lrclib, fake_gemini, 101)
        open_new_song(first, fake_lrclib, fake_gemini, 102)
        save(first, 101, VIDEO_A)
        save(second, 101, VIDEO_B)
        save(second, 102, None)

        assert save(first, 101, VIDEO_A) == 204
        assert first.delete(SAVED_SONG_PATH.format(song_id=101)).status_code == 204

        first_songs = first.get(SAVED_SONGS_PATH).json()["songs"]
        second_songs = second.get(SAVED_SONGS_PATH).json()["songs"]
        assert first_songs == []
        assert {song["id"]: song["videoId"] for song in second_songs} == {101: VIDEO_B, 102: None}
        assert second.post(SONG_VERSIONS_PATH, json={"id": 101}).json()["playback"] == {
            "videoId": VIDEO_B,
            "offsetMs": 0,
        }
        assert first.post(SONG_VERSIONS_PATH, json={"id": 101}).json()["saved"] is False
        recent = {s["id"]: s["videoId"] for s in second.get(RECENT_SONGS_PATH).json()["songs"]}
        assert recent == {101: VIDEO_B, 102: None}
        fake_lrclib.script(json_reply([record(record_id=101), record(record_id=103, track="別")]))
        fake_lrclib.script(json_reply([record(record_id=101), record(record_id=103, track="別")]))
        first_search = first.post(SONG_SEARCH_PATH, json={"query": "歌"}).json()["results"]
        second_search = second.post(SONG_SEARCH_PATH, json={"query": "歌"}).json()["results"]
        assert {r["id"]: r["saved"] for r in first_search} == {101: False, 103: False}
        assert {r["id"]: r["saved"] for r in second_search} == {101: True, 103: False}
    assert library.find_song(101) is not None


@pytest.mark.usefixtures("gemini_key")
def test_ac7_cached_songs_are_free_and_the_account_cap_stops_new_songs_before_lrclib(
    client: TestClient,
    fake_lrclib: FakeLrclib,
    fake_gemini: FakeGemini,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(config, "NEW_SONGS_PER_ACCOUNT_PER_DAY", 2)
    sign_up(client)
    assert open_new_song(client, fake_lrclib, fake_gemini, 101).status_code == 200
    for _ in range(3):
        assert client.post(SONG_VERSIONS_PATH, json={"id": 101}).status_code == 200
    assert open_new_song(client, fake_lrclib, fake_gemini, 102).status_code == 200
    lrclib_calls = len(fake_lrclib.requests)

    response = client.post(SONG_VERSIONS_PATH, json={"id": 103})

    assert response.status_code == 429
    assert_error_shape(response.json(), "daily_limit")
    assert response.json()["message"] == "Daily limit reached. Songs already in Lyrx still open."
    assert len(fake_lrclib.requests) == lrclib_calls


@pytest.mark.usefixtures("gemini_key")
def test_ac7_a_failed_new_song_still_counts(
    client: TestClient, fake_lrclib: FakeLrclib, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(config, "NEW_SONGS_PER_ACCOUNT_PER_DAY", 1)
    sign_up(client)
    fake_lrclib.script(json_reply({"message": "no"}, status=404))
    assert client.post(SONG_VERSIONS_PATH, json={"id": 101}).status_code == 404

    response = client.post(SONG_VERSIONS_PATH, json={"id": 102})

    assert_error_shape(response.json(), "daily_limit")


@pytest.mark.usefixtures("gemini_key")
def test_ac8_guests_are_capped_per_ip_separately_from_accounts(
    app: FastAPI,
    client: TestClient,
    fake_lrclib: FakeLrclib,
    fake_gemini: FakeGemini,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(config, "NEW_SONGS_PER_GUEST_IP_PER_DAY", 1)
    assert open_new_song(client, fake_lrclib, fake_gemini, 101).status_code == 200

    guest_again = client.post(SONG_VERSIONS_PATH, json={"id": 102})
    with make_client(app) as person:
        sign_up(person)
        person_reply = open_new_song(person, fake_lrclib, fake_gemini, 102)

    assert_error_shape(guest_again.json(), "daily_limit")
    assert person_reply.status_code == 200


@pytest.mark.usefixtures("gemini_key")
def test_ac9_the_site_cap_stops_new_songs_for_everyone_but_cached_songs_open(
    app: FastAPI,
    client: TestClient,
    fake_lrclib: FakeLrclib,
    fake_gemini: FakeGemini,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(config, "NEW_SONGS_PER_SITE_PER_DAY", 1)
    assert open_new_song(client, fake_lrclib, fake_gemini, 101).status_code == 200

    with make_client(app) as person:
        sign_up(person)
        refused = person.post(SONG_VERSIONS_PATH, json={"id": 102})
        cached = person.post(SONG_VERSIONS_PATH, json={"id": 101})

    assert_error_shape(refused.json(), "daily_limit")
    assert cached.status_code == 200


def test_spec020_ac5_health_is_ok_after_a_database_read(client: TestClient) -> None:
    response = client.get(HEALTH_PATH)

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_spec020_ac5_health_is_503_when_the_database_cannot_be_read(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # A folder where the database file should be: SQLite cannot open it.
    monkeypatch.setattr(config, "DATABASE_PATH", tmp_path)

    response = client.get(HEALTH_PATH)

    assert response.status_code == 503
    assert_error_shape(response.json(), "server_unavailable")


CADDY_ADDRESS = "172.30.0.10"


def client_as_seen_behind(app: FastAPI, peer: str, trusted_proxy: str | None) -> str:
    """The guest IP the app sees for a request from `peer` carrying a forged-looking
    `X-Forwarded-For`, wrapped the way `python -m lyrx` asks uvicorn to wrap it."""

    def report_peer(request: Request) -> dict[str, str]:
        return {"ip": peer_address(request)}

    app.add_api_route("/api/test-peer", report_peer)
    served: ASGIApp = app
    if trusted_proxy is not None:
        # uvicorn and Starlette spell the same ASGI types differently; at runtime they match.
        served = cast(ASGIApp, ProxyHeadersMiddleware(cast(Any, app), trusted_hosts=trusted_proxy))
    test_client = TestClient(served, base_url="http://127.0.0.1:8000", client=(peer, 50000))
    response = test_client.get("/api/test-peer", headers={"X-Forwarded-For": "203.0.113.7"})
    return str(response.json()["ip"])


def test_spec020_ac6_the_guest_ip_comes_from_the_trusted_proxy(app: FastAPI) -> None:
    assert client_as_seen_behind(app, CADDY_ADDRESS, CADDY_ADDRESS) == "203.0.113.7"


def test_spec020_ac6_a_forged_header_from_another_address_is_ignored(app: FastAPI) -> None:
    assert client_as_seen_behind(app, "198.51.100.9", CADDY_ADDRESS) == "198.51.100.9"


def test_spec020_ac6_without_a_trusted_proxy_the_header_is_ignored(app: FastAPI) -> None:
    assert client_as_seen_behind(app, CADDY_ADDRESS, None) == CADDY_ADDRESS


# Serving the built page (spec 020 AC-4).

INDEX_HTML = "<!doctype html><title>Lyrx</title>"
ASSET_JS = "console.log('page');"


@pytest.fixture
def page_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """A small built page, with a secret file next to (outside) its folder."""
    folder = tmp_path / "dist"
    (folder / "assets").mkdir(parents=True)
    (folder / "index.html").write_text(INDEX_HTML)
    (folder / "assets" / "index-abc123.js").write_text(ASSET_JS)
    (folder / "favicon.svg").write_text("<svg/>")
    (tmp_path / "secret.txt").write_text("outside the page")
    monkeypatch.setattr(config, "PAGE_DIR", folder.resolve())
    return folder


@pytest.mark.parametrize("path", ["/", "/song/5", "/library", "/no/such/file.js"])
def test_ac4_page_addresses_return_index_html(
    client: TestClient, page_dir: Path, path: str
) -> None:
    response = client.get(path)

    assert response.status_code == 200
    assert response.text == INDEX_HTML
    assert response.headers["cache-control"] == "no-cache"


def test_ac4_built_files_are_served_and_assets_cached(client: TestClient, page_dir: Path) -> None:
    asset = client.get("/assets/index-abc123.js")
    favicon = client.get("/favicon.svg")

    assert asset.text == ASSET_JS
    assert "immutable" in asset.headers["cache-control"]
    assert favicon.text == "<svg/>"
    assert favicon.headers["cache-control"] == "no-cache"


@pytest.mark.parametrize("path", ["/%2e%2e/secret.txt", "/assets/%2e%2e/%2e%2e/secret.txt"])
def test_ac4_paths_never_leave_the_page_folder(
    client: TestClient, page_dir: Path, path: str
) -> None:
    response = client.get(path)

    assert "outside the page" not in response.text


def test_ac4_api_routes_are_unchanged(client: TestClient, page_dir: Path) -> None:
    unknown = client.get("/api/x")
    unknown_post = client.post("/api/x", json={})
    wrong_method = client.get(SONG_SEARCH_PATH)
    bare_api = client.get("/api")
    recent = client.get("/api/recent-songs")

    assert unknown.status_code == 404
    assert_error_shape(unknown.json(), "not_found")
    assert_error_shape(unknown_post.json(), "not_found")
    assert_error_shape(wrong_method.json(), "method_not_allowed")
    assert_error_shape(bare_api.json(), "not_found")
    assert recent.json() == {"songs": []}


def test_ac4_without_a_page_folder_the_root_is_not_found(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(config, "PAGE_DIR", None)

    response = client.get("/")

    assert response.status_code == 404
    assert_error_shape(response.json(), "not_found")


@pytest.mark.parametrize("relative", ["../secret.txt", "assets/../../secret.txt", "a\x00b"])
def test_ac4_page_file_refuses_names_outside_the_folder(page_dir: Path, relative: str) -> None:
    assert page_file(page_dir.resolve(), relative) is None
