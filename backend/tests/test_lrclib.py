import httpx
import pytest

from app.errors import DomainError
from app.generation.lrclib import choose_recording, lyric_lines, search_recording


def test_section_labels_are_not_lyric_lines() -> None:
    assert lyric_lines("雨\n[Chorus]\n空\n") == ["雨", "空"]


def test_the_full_exact_match_beats_the_first_excerpt() -> None:
    rows = [
        {"trackName": "Ame", "artistName": "Example", "plainLyrics": "雨\n空", "instrumental": False},
        {
            "trackName": "AME",
            "artistName": "example",
            "plainLyrics": "雨\n空\n海\n風",
            "instrumental": False,
        },
        {
            "trackName": "Something Else",
            "artistName": "Other",
            "plainLyrics": "\n".join(f"行{number}" for number in range(30)),
            "instrumental": False,
        },
        {"trackName": "Ame", "artistName": "Example", "plainLyrics": "長いけど器楽", "instrumental": True},
    ]

    chosen = choose_recording(rows, "Ame", "Example")

    assert chosen is not None
    assert chosen.title == "AME"
    assert chosen.artist == "example"
    assert lyric_lines(chosen.text) == ["雨", "空", "海", "風"]


def test_a_japanese_lyric_beats_a_longer_translation() -> None:
    rows = [
        {
            "trackName": "Idol",
            "artistName": "YOASOBI",
            "plainLyrics": "Couldn't beat her smile\nSecret side\nSo mysterious\n",
            "instrumental": False,
        },
        {
            "trackName": "Idol",
            "artistName": "YOASOBI",
            "plainLyrics": "無敵の笑顔\n秘密",
            "instrumental": False,
        },
    ]

    chosen = choose_recording(rows, "Idol", "YOASOBI")

    assert chosen is not None
    assert lyric_lines(chosen.text) == ["無敵の笑顔", "秘密"]


def test_an_exact_artist_beats_a_longer_lyric() -> None:
    rows = [
        {"trackName": "Ame", "artistName": "Other", "plainLyrics": "雨\n空\n海\n風", "instrumental": False},
        {"trackName": "Ame", "artistName": "Example", "plainLyrics": "雨\n空", "instrumental": False},
    ]

    named = choose_recording(rows, "Ame", "Example")
    unnamed = choose_recording(rows, "Ame", "")

    assert named is not None and lyric_lines(named.text) == ["雨", "空"]
    assert unnamed is not None and lyric_lines(unnamed.text) == ["雨", "空", "海", "風"]


def test_an_english_only_result_is_not_used_as_the_original() -> None:
    rows = [
        {
            "trackName": "Idol",
            "artistName": "YOASOBI",
            "plainLyrics": "Couldn't beat her smile\nSecret side",
            "instrumental": False,
        }
    ]

    assert choose_recording(rows, "Idol", "YOASOBI") is None


def test_a_failed_fetch_does_not_invent_a_lyric(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(*_args: object, **_kwargs: object) -> None:
        raise httpx.ConnectError("offline")

    monkeypatch.setattr("app.generation.lrclib.httpx.get", fail)

    with pytest.raises(DomainError) as error:
        search_recording("Ame", "Example")

    assert error.value.code == "groq_unavailable"
