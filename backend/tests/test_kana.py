"""Tests for which characters are kana and which are kanji."""

import pytest

from lyrx.kana import is_kana, is_kanji

# Kana (AC-43)


@pytest.mark.parametrize(
    "character",
    [
        "ぁ",  # ぁ, first hiragana
        "ゖ",  # ゖ, last hiragana
        "あ",
        "ゝ",
        "ゞ",
        "ァ",  # ァ, first katakana
        "ヺ",  # ヺ, last katakana
        "ア",
        "ー",  # ー
        "ヽ",
        "ヾ",
    ],
)
def test_ac43_kana_characters_are_kana(character: str) -> None:
    assert is_kana(character)


@pytest.mark.parametrize(
    "character",
    ["・", "a", "1", " ", "　", "、", "空", "々"],
)
def test_ac43_other_characters_are_not_kana(character: str) -> None:
    assert not is_kana(character)


# Hiragana letters (AC-43): the hiragana block, without iteration marks or the long mark


@pytest.mark.parametrize(
    "character",
    [
        "空",
        "々",
        "〆",
        "一",  # first CJK unified ideograph
        "鿿",  # last CJK unified ideograph
        "㐀",  # first CJK Extension A
        "䶿",  # last CJK Extension A
        "豈",  # first CJK Compatibility Ideograph
        "﫿",  # last CJK Compatibility Ideograph
    ],
)
def test_ac43_kanji_characters_are_kanji(character: str) -> None:
    assert is_kanji(character)


@pytest.mark.parametrize(
    "character",
    [
        "あ",
        "ア",
        "ー",
        "ゝ",
        "a",
        "1",
        "、",
        "㏿",  # just before Extension A
        "䷀",  # just after Extension A
        "",  # just before Compatibility Ideographs
        "ﬀ",  # just after Compatibility Ideographs
    ],
)
def test_ac43_other_characters_are_not_kanji(character: str) -> None:
    assert not is_kanji(character)
