from pathlib import Path

from fastapi.testclient import TestClient

from app.align import TimedWord
from tests.test_import import app_for, bundle, fields


def test_saved_line_time_can_be_read_back(tmp_path: Path) -> None:
    client = TestClient(app_for(tmp_path))
    created = client.post("/api/import", data=fields(), files=bundle())
    song_id = created.json()["id"]

    saved = client.post(
        f"/api/songs/{song_id}/line-times",
        json={"lines": [{"index": 1, "startSeconds": 0.02}]},
    )
    again = client.post("/api/import", data=fields(), files=bundle())

    assert saved.status_code == 200
    assert saved.json()["lines"][1]["startSeconds"] == 0.02
    assert "startSeconds" not in saved.json()["lines"][0]
    assert again.status_code == 200
    assert again.json()["lines"][1]["startSeconds"] == 0.02


def test_line_time_past_the_song_is_rejected(tmp_path: Path) -> None:
    client = TestClient(app_for(tmp_path))
    created = client.post("/api/import", data=fields(), files=bundle())
    song_id = created.json()["id"]

    response = client.post(
        f"/api/songs/{song_id}/line-times",
        json={"lines": [{"index": 0, "startSeconds": 3600}]},
    )

    assert response.status_code == 400
    assert response.json()["code"] == "invalid_line"


def test_scan_stores_the_matched_line_times(tmp_path: Path, monkeypatch) -> None:
    def fake_words(_path, _language, _model):
        return [TimedWord("雨", 1.5, 2.0), TimedWord("空", 4.0, 5.0)]

    monkeypatch.setattr("app.songs.transcribe_words", fake_words)
    client = TestClient(app_for(tmp_path))
    created = client.post("/api/import", data=fields(), files=bundle())
    song_id = created.json()["id"]

    scanned = client.post(f"/api/songs/{song_id}/scan")

    assert scanned.status_code == 200
    assert [line["startSeconds"] for line in scanned.json()["lines"]] == [1.5, 4.0]


def test_import_scan_stores_line_times(tmp_path: Path, monkeypatch) -> None:
    def fake_words(_path, _language, _model):
        return [TimedWord("雨", 1.5, 2.0), TimedWord("空", 4.0, 5.0)]

    monkeypatch.setattr("app.importer.transcribe_words", fake_words)
    application = app_for(tmp_path)
    application.state.settings.align_on_import = True
    client = TestClient(application)

    created = client.post("/api/import", data=fields(), files=bundle())

    assert created.status_code == 201
    assert [line["startSeconds"] for line in created.json()["lines"]] == [1.5, 4.0]
