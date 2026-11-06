import pytest

from app.reading import ReadingError, assemble_reading, hepburn, lock_reading


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


def test_katakana_in_the_line_cannot_be_rewritten() -> None:
    hiragana, romaji = assemble_reading("ニガくてせつない香り", ["かおり"])

    assert hiragana == "にがくてせつない かおり"
    assert romaji == "nigakutesetsunai kaori"


def test_an_extra_reading_joins_the_longest_bracket() -> None:
    line = "恋のプログラムを 狂わせないでね"

    hiragana, romaji = assemble_reading(line, ["こい", "くるわせ", "ないでね"])

    assert hiragana == "こい の ぷろぐらむを くるわせないでね"
    assert romaji == "koi no puroguramuo kuruwasenaidene"

    hiragana, romaji = assemble_reading(line, ["こい", "ぷろぐらむ", "くるわせないでね"])

    assert hiragana == "こい の ぷろぐらむを くるわせないでね"
    assert romaji == "koi no puroguramuo kuruwasenaidene"


def test_too_few_readings_still_do_not_match_the_line() -> None:
    with pytest.raises(ReadingError):
        assemble_reading("恋のプログラムを 狂わせないでね", ["こい"])


def test_common_lyric_readings_replace_the_dictionary_miss() -> None:
    hiragana, romaji = assemble_reading("私はきっと泣いている", ["わたくし", "ないている"])

    assert hiragana == "わたし は きっと ないている"
    assert romaji == "watashi wa kitto naiteiru"

    hiragana, romaji = assemble_reading("明日の今頃には", ["あす", "いまごろ"])

    assert hiragana == "あした の いまごろ に は"
    assert romaji == "ashita no imagoro ni wa"
