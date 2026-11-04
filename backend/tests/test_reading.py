import pytest

from app.reading import ReadingError, hepburn, lock_reading


@pytest.mark.parametrize(
    ("kana", "romaji"),
    [
        ("したたる", "shitataru"),
        ("わたし は そら を みた", "watashi wa sora o mita"),
        ("こんにちは", "konnichiwa"),
        ("こんばんは。", "konbanwa."),
        ("はは", "haha"),
        ("へや", "heya"),
        ("こっち", "kotchi"),
        ("いっしょ", "issho"),
        ("みっつ", "mittsu"),
        ("まっちゃ", "matcha"),
        ("きんえん", "kin'en"),
        ("あんない", "annai"),
        ("コーヒー", "koohii"),
        ("がっこう", "gakkou"),
        ("カフェ", "kafe"),
        ("あっ", "a'"),
        ("Hello", "Hello"),
    ],
)
def test_hepburn(kana: str, romaji: str) -> None:
    assert hepburn(kana) == romaji


def test_a_kana_line_ignores_a_wrong_reading() -> None:
    assert lock_reading("コーヒー", "かんじ") == ("こーひー", "koohii")


def test_a_reading_must_keep_the_original_kana() -> None:
    with pytest.raises(ReadingError):
        lock_reading("雨が", "あめ")

    assert lock_reading("雨が", "あめ が") == ("あめ が", "ame ga")


def test_placeholder_hiragana_is_rejected() -> None:
    with pytest.raises(ReadingError):
        lock_reading("雨", "よみ")
