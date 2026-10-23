import pytest
from pydantic import ValidationError

from app.contracts import SongDetail


def valid_song() -> dict[str, object]:
    return {
        "id": "akuma-no-ko",
        "title": "Akuma no Ko",
        "artist": "Ai Higuchi",
        "sourceLanguage": "ja",
        "targetLanguage": "en",
        "durationSeconds": 222.0,
        "status": "draft",
        "audioUrl": "/media/akuma-no-ko.mp3",
        "contentVersion": "1",
        "lines": [
            {
                "id": "line-0",
                "index": 0,
                "originalText": "歌詞",
                "pronunciationRomaji": "kashi",
                "translationEnglish": "lyrics",
            }
        ],
    }


def test_song_detail_accepts_ordered_lines() -> None:
    song = SongDetail.model_validate(valid_song())

    assert song.lines[0].index == 0
    assert song.durationSeconds == 222.0


def test_song_detail_accepts_line_start_seconds() -> None:
    payload = valid_song()
    lines = payload["lines"]
    assert isinstance(lines, list)
    lines[0]["startSeconds"] = 5.5

    song = SongDetail.model_validate(payload)

    assert song.lines[0].startSeconds == 5.5


def test_song_detail_rejects_line_timing_fields() -> None:
    payload = valid_song()
    lines = payload["lines"]
    assert isinstance(lines, list)
    lines[0]["startTime"] = 12.5

    with pytest.raises(ValidationError, match="timing fields are not allowed: startTime"):
        SongDetail.model_validate(payload)


def test_song_detail_rejects_top_level_timing_fields() -> None:
    payload = valid_song()
    payload["timing"] = [{"startTime": 0}]

    with pytest.raises(ValidationError, match="timing fields are not allowed: timing"):
        SongDetail.model_validate(payload)


def test_song_detail_rejects_noncontiguous_line_indexes() -> None:
    payload = valid_song()
    lines = payload["lines"]
    assert isinstance(lines, list)
    lines[0]["index"] = 1

    with pytest.raises(ValidationError, match="zero-based, unique, and contiguous"):
        SongDetail.model_validate(payload)
