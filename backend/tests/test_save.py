import json
import logging
from pathlib import Path

from alembic import command
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

from app.core.deps import get_generation_service
from app.generation.service import GenerationService
from app.main import create_app
from app.models import LyricVersion, Track
from app.services.library import song_id_from_title
from tests.lyric_fixture import search_ame
from tests.test_app import settings
from tests.test_database import migration_config

MP3 = (bytes([0xFF, 0xFB, 0x90, 0x00]) + bytes(413)) * 2


def draft() -> dict[str, object]:
    return {
        "title": "Ame",
        "artist": "Example",
        "lines": [
            {
                "originalText": "雨",
                "readingHiragana": "あめ",
                "pronunciationRomaji": "ame",
                "translationEnglish": "rain",
            },
            {
                "originalText": "空",
                "readingHiragana": "そら",
                "pronunciationRomaji": "sora",
                "translationEnglish": "sky",
            },
        ],
    }


def app_for(tmp_path: Path):
    database_path = tmp_path / "lyrx.db"
    command.upgrade(migration_config(database_path), "head")
    return create_app(
        settings(
            database_url=f"sqlite:///{database_path}",
            media_root=str(tmp_path / "media"),
            audio_staging_root=str(tmp_path / "uploads"),
            public_media_base_url="http://localhost:8000/media",
        )
    )


def test_song_id_comes_from_the_title() -> None:
    assert song_id_from_title("Akuma no Ko") == "akuma-no-ko"
    assert song_id_from_title("雨").startswith("song-")


def test_save_can_be_read_back_without_audio(tmp_path: Path) -> None:
    client = TestClient(app_for(tmp_path))

    created = client.post("/api/songs", json=draft())
    songs = client.get("/api/songs")
    song = client.get("/api/songs/ame")

    assert created.status_code == 201
    assert "audioUrl" not in created.json()
    assert songs.json()[0]["title"] == "Ame"
    assert song.status_code == 200
    assert [line["readingHiragana"] for line in song.json()["lines"]] == ["あめ", "そら"]
    assert list((tmp_path / "media").iterdir()) == []


def test_a_second_save_with_the_same_title_is_a_new_song(tmp_path: Path) -> None:
    client = TestClient(app_for(tmp_path))

    first = client.post("/api/songs", json=draft())
    second = client.post("/api/songs", json=draft())

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] == "ame"
    assert second.json()["id"] != "ame"


def test_audio_attaches_and_replace_is_required(tmp_path: Path) -> None:
    client = TestClient(app_for(tmp_path))
    created = client.post("/api/songs", json=draft())
    song_id = created.json()["id"]

    attached = client.post(f"/api/songs/{song_id}/audio", files={"audio": ("track.mp3", MP3, "audio/mpeg")})
    conflict = client.post(f"/api/songs/{song_id}/audio", files={"audio": ("other.mp3", MP3, "audio/mpeg")})
    replaced = client.post(
        f"/api/songs/{song_id}/audio",
        data={"replace": "true"},
        files={"audio": ("other.mp3", MP3, "audio/mpeg")},
    )

    assert attached.status_code == 200
    assert attached.json()["audioUrl"].endswith(".mp3")
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "song_conflict"
    assert replaced.status_code == 200


def test_invalid_audio_leaves_the_song_without_a_file(tmp_path: Path) -> None:
    client = TestClient(app_for(tmp_path))
    created = client.post("/api/songs", json=draft())

    response = client.post(
        f"/api/songs/{created.json()['id']}/audio",
        files={"audio": ("notes.txt", b"not an mp3", "audio/mpeg")},
    )

    assert response.status_code == 400
    assert response.json()["code"] == "invalid_audio"
    assert "audioUrl" not in client.get(f"/api/songs/{created.json()['id']}").json()
    assert list((tmp_path / "media").iterdir()) == []


def test_lyric_file_import_is_gone(tmp_path: Path) -> None:
    response = TestClient(app_for(tmp_path)).post("/api/import")

    assert response.status_code == 404
    assert response.json()["code"] == "not_found"


def _slots(readings: list[list[str]]) -> dict[str, object]:
    return {
        "status_code": 200,
        "data": {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "lines": [
                                    {"readings": row, "translationEnglish": "rain", "pronunciationRomaji": "from-the-model"}
                                    for row in readings
                                ]
                            },
                            ensure_ascii=False,
                        )
                    }
                }
            ]
        },
    }


def test_generation_uses_one_injected_call(tmp_path: Path) -> None:
    application = app_for(tmp_path)
    calls = {"count": 0}

    class FakeGroq:
        def complete(self, body: dict[str, object]) -> dict[str, object]:
            calls["count"] += 1
            return _slots([["あめ"], ["そら"]])

    application.dependency_overrides[get_generation_service] = lambda: GenerationService(
        FakeGroq(),
        "openai/gpt-oss-120b",
        search_ame,
    )
    response = TestClient(application).post("/api/generations", json={"message": "Ame by Example", "draft": draft()})

    assert response.status_code == 200
    assert calls["count"] == 1
    lyric = response.json()["draft"]
    assert [line["originalText"] for line in lyric["lines"]] == ["雨", "空"]
    assert lyric["lines"][0]["readingHiragana"] == "あめ"
    assert lyric["lines"][0]["pronunciationRomaji"] == "ame"
    session = sessionmaker(bind=application.state.engine)()
    tracks = session.scalar(select(func.count()).select_from(Track))
    session.close()
    assert tracks == 0


def test_a_bad_generation_is_not_saved_or_retried(tmp_path: Path) -> None:
    application = app_for(tmp_path)
    calls = {"count": 0}

    class FakeGroq:
        def complete(self, body: dict[str, object]) -> dict[str, object]:
            calls["count"] += 1
            return _slots([])

    application.dependency_overrides[get_generation_service] = lambda: GenerationService(
        FakeGroq(),
        "openai/gpt-oss-120b",
        search_ame,
    )
    response = TestClient(application).post("/api/generations", json={"message": "Ame by Example"})

    assert response.status_code == 422
    assert response.json()["code"] == "generation_invalid"
    assert calls["count"] == 1
    session = sessionmaker(bind=application.state.engine)()
    tracks = session.scalar(select(func.count()).select_from(Track))
    session.close()
    assert tracks == 0


def test_stored_line_times_are_not_returned(tmp_path: Path) -> None:
    application = app_for(tmp_path)
    client = TestClient(application)
    created = client.post("/api/songs", json=draft())
    assert created.status_code == 201

    session = sessionmaker(bind=application.state.engine)()
    version = session.scalar(select(LyricVersion))
    assert version is not None
    payload = json.loads(version.lines_json)
    payload[0]["startSeconds"] = 1.5
    version.lines_json = json.dumps(payload)
    session.commit()
    session.close()

    song = client.get("/api/songs/ame")

    assert song.status_code == 200
    assert "startSeconds" not in song.json()["lines"][0]
    assert song.json()["lines"][0]["readingHiragana"] == "あめ"


def test_missing_song_is_a_safe_error(tmp_path: Path) -> None:
    response = TestClient(app_for(tmp_path)).get("/api/songs/missing", headers={"X-Request-ID": "trace-1"})

    assert response.status_code == 404
    assert response.json()["code"] == "song_not_found"
    assert response.json()["requestId"] == "trace-1"
    assert response.headers["x-request-id"] == "trace-1"


def test_request_id_header_must_be_a_token(tmp_path: Path) -> None:
    response = TestClient(app_for(tmp_path)).get("/api/songs/missing", headers={"X-Request-ID": "bad id"})

    assert " " not in response.json()["requestId"]


def test_invalid_save_uses_the_error_envelope(tmp_path: Path) -> None:
    response = TestClient(app_for(tmp_path)).post("/api/songs", json={}, headers={"X-Request-ID": "trace-1"})

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "validation_error"
    assert body["message"] == "The request is invalid."
    assert body["requestId"] == "trace-1"
    assert "title" in {detail["field"] for detail in body["details"]}


def test_a_song_saved_without_hiragana_still_opens(tmp_path: Path) -> None:
    application = app_for(tmp_path)
    client = TestClient(application)
    created = client.post("/api/songs", json=draft())
    assert created.status_code == 201

    session = sessionmaker(bind=application.state.engine)()
    version = session.scalar(select(LyricVersion))
    assert version is not None
    stored = json.loads(version.lines_json)
    for row in stored:
        row.pop("readingHiragana")
    version.lines_json = json.dumps(stored)
    session.commit()
    session.close()

    song = client.get("/api/songs/ame")

    assert song.status_code == 200
    assert [line["readingHiragana"] for line in song.json()["lines"]] == ["", ""]


def test_unreadable_stored_lyrics_are_a_safe_error(tmp_path: Path, caplog) -> None:
    application = app_for(tmp_path)
    client = TestClient(application)
    created = client.post("/api/songs", json=draft())
    assert created.status_code == 201

    session = sessionmaker(bind=application.state.engine)()
    version = session.scalar(select(LyricVersion))
    assert version is not None
    version.lines_json = "not-json"
    session.commit()
    session.close()

    song_log = logging.getLogger("app.services.songs")
    song_log.addHandler(caplog.handler)
    try:
        with caplog.at_level("WARNING", logger="app.services.songs"):
            song = client.get("/api/songs/ame")
    finally:
        song_log.removeHandler(caplog.handler)

    assert song.status_code == 500
    assert song.json()["code"] == "invalid_song"
    assert "not-json" not in song.json()["message"]
    assert any(getattr(record, "song_id", None) == "ame" for record in caplog.records)
    assert all("not-json" not in record.getMessage() for record in caplog.records)
