"""Tests for the paste route (AC-11): the same line shape through the same pipeline."""

import pytest
from error_shape import assert_error_shape
from fake_gemini import FakeGemini, sent_indexes, success
from fastapi.testclient import TestClient

from lyrx import config
from lyrx.app import VERSIONS_PATH


@pytest.mark.usefixtures("gemini_key")
def test_ac11_a_paste_comes_back_in_four_versions(
    client: TestClient, fake_gemini: FakeGemini
) -> None:
    fake_gemini.script(
        success({0: ("よる の つき", "yoru no tsuki", "The night moon"), 2: ("Hey", "Hey", "Hey")})
    )

    response = client.post(VERSIONS_PATH, json={"lyrics": "夜の月\n\nHey"})

    assert response.status_code == 200
    assert response.json() == {
        "lines": [
            {
                "index": 0,
                "original": "夜の月",
                "hiragana": "よる の つき",
                "romaji": "yoru no tsuki",
                "english": "The night moon",
            },
            {"index": 1, "original": "", "hiragana": "", "romaji": "", "english": ""},
            {"index": 2, "original": "Hey", "hiragana": "Hey", "romaji": "Hey", "english": "Hey"},
        ]
    }
    assert sent_indexes(fake_gemini.requests[0]) == [0, 2]


@pytest.mark.parametrize(
    ("lyrics", "status_code", "code"),
    [
        ("   ", 400, "empty_input"),
        ("We sing tonight", 400, "no_japanese"),
        ("夜", 503, "server_not_configured"),
    ],
)
def test_refusals_happen_before_gemini(
    client: TestClient,
    fake_gemini: FakeGemini,
    monkeypatch: pytest.MonkeyPatch,
    lyrics: str,
    status_code: int,
    code: str,
) -> None:
    monkeypatch.delenv(config.GEMINI_API_KEY_ENV_VAR, raising=False)

    response = client.post(VERSIONS_PATH, json={"lyrics": lyrics})

    assert response.status_code == status_code
    assert_error_shape(response.json(), code)
    assert fake_gemini.requests == []
