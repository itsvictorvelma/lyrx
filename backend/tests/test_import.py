import json
from pathlib import Path

from alembic import command
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

from app.importer import song_id_from_title
from app.main import create_app
from app.models import LyricVersion, Track
from tests.test_app import settings
from tests.test_database import migration_config

MP3 = bytes([0xFF, 0xFB, 0x90, 0x00]) + bytes(413)
MP3 = MP3 * 2


def app_for(tmp_path: Path):
    database_path = tmp_path / "lyrx.db"
    command.upgrade(migration_config(database_path), "head")
    application = create_app(
        settings(
            database_url=f"sqlite:///{database_path}",
            media_root=str(tmp_path / "media"),
            import_staging_root=str(tmp_path / "uploads"),
            import_enabled=True,
            public_media_base_url="http://localhost:8000/media",
        )
    )
    return application


def bundle(translation: str = "rain\nsky\n") -> dict[str, tuple[str, bytes, str]]:
    return {
        "original": ("original.txt", "雨\n空\n".encode(), "text/plain"),
        "pronunciation": ("pronunciation.txt", b"ame\nsora\n", "text/plain"),
        "translation": ("translation.txt", translation.encode(), "text/plain"),
        "audio": ("audio.mp3", MP3, "audio/mpeg"),
    }


def fields(replace: str = "false") -> dict[str, str]:
    return {
        "title": "Ame",
        "artist": "Example",
        "sourceLanguage": "ja",
        "targetLanguage": "en",
        "replace": replace,
    }


def test_song_id_comes_from_the_title() -> None:
    assert song_id_from_title("Akuma no Ko") == "akuma-no-ko"
    assert song_id_from_title("雨").startswith("song-")


def test_import_can_be_read_back(tmp_path: Path) -> None:
    application = app_for(tmp_path)
    client = TestClient(application)

    created = client.post("/api/import", data=fields(), files=bundle())
    songs = client.get("/api/songs")
    song = client.get("/api/songs/ame")

    assert created.status_code == 201
    assert songs.status_code == 200
    assert songs.json()[0]["title"] == "Ame"
    assert song.status_code == 200
    assert [line["originalText"] for line in song.json()["lines"]] == ["雨", "空"]
    assert song.json()["lines"][0]["index"] == 0
    assert song.json()["audioUrl"] == "http://localhost:8000/media/" + Path(song.json()["audioUrl"]).name
    audio_name = Path(song.json()["audioUrl"]).name
    assert (tmp_path / "media" / audio_name).read_bytes() == MP3


def test_same_import_does_not_duplicate(tmp_path: Path) -> None:
    application = app_for(tmp_path)
    client = TestClient(application)
    client.post("/api/import", data=fields(), files=bundle())

    repeated = client.post("/api/import", data=fields(), files=bundle())
    session = sessionmaker(bind=application.state.engine)()
    versions = session.scalar(select(func.count()).select_from(LyricVersion))
    session.close()

    assert repeated.status_code == 200
    assert versions == 1
    assert len(list((tmp_path / "media").iterdir())) == 1


def test_different_content_conflicts_until_replaced(tmp_path: Path) -> None:
    application = app_for(tmp_path)
    client = TestClient(application)
    client.post("/api/import", data=fields(), files=bundle())

    conflict = client.post("/api/import", data=fields(), files=bundle("rain\nheaven\n"))
    replaced = client.post("/api/import", data=fields(replace="true"), files=bundle("rain\nheaven\n"))

    assert conflict.status_code == 409
    assert conflict.json()["code"] == "song_conflict"
    assert replaced.status_code == 201
    assert replaced.json()["lines"][1]["translationEnglish"] == "heaven"


def test_invalid_bundle_writes_nothing(tmp_path: Path) -> None:
    application = app_for(tmp_path)
    client = TestClient(application)

    response = client.post("/api/import", data=fields(), files=bundle("rain\n"))
    session = sessionmaker(bind=application.state.engine)()
    tracks = session.scalar(select(func.count()).select_from(Track))
    session.close()

    assert response.status_code == 400
    assert response.json()["code"] == "line_count_mismatch"
    assert tracks == 0
    assert list((tmp_path / "media").iterdir()) == []


def test_unreadable_audio_is_rejected(tmp_path: Path) -> None:
    application = app_for(tmp_path)
    files = bundle()
    files["audio"] = ("audio.mp3", b"not an mp3", "audio/mpeg")

    response = TestClient(application).post("/api/import", data=fields(), files=files)

    assert response.status_code == 400
    assert response.json()["code"] == "invalid_audio"


def test_stored_line_times_are_not_returned(tmp_path: Path) -> None:
    application = app_for(tmp_path)
    client = TestClient(application)
    created = client.post("/api/import", data=fields(), files=bundle())
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
    assert song.json()["lines"][0]["originalText"] == "雨"


def test_missing_song_is_a_safe_error(tmp_path: Path) -> None:
    response = TestClient(app_for(tmp_path)).get("/api/songs/missing")

    assert response.status_code == 404
    assert response.json()["code"] == "song_not_found"
