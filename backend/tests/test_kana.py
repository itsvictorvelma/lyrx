"""Tests for which characters are kana and kanji, and for turning katakana into hiragana."""

import pytest

from lyrx.kana import is_hiragana_letter, is_kana, is_kanji, to_hiragana

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


@pytest.mark.parametrize("character", ["\u3041", "\u3096", "あ", "ん", "ゔ", "っ"])
def test_ac43_hiragana_are_hiragana_letters(character: str) -> None:
    assert is_hiragana_letter(character)


@pytest.mark.parametrize("character", ["ゝ", "ゞ", "\u30fc", "ア", "ヽ", "空", "々", "a", " "])
def test_ac43_marks_katakana_and_kanji_are_not_hiragana_letters(character: str) -> None:
    assert not is_hiragana_letter(character)


# Kanji (AC-43)


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


# Katakana to hiragana (AC-19)


def test_ac19_katakana_becomes_hiragana() -> None:
    assert to_hiragana("ココロ") == "こころ"


def test_ac19_voiced_and_small_katakana_become_hiragana() -> None:
    assert to_hiragana("ガパヴ") == "がぱゔ"
    assert to_hiragana("ァィゥェォッャュョヮ") == "ぁぃぅぇぉっゃゅょゎ"


def test_ac19_katakana_iteration_marks_become_hiragana_iteration_marks() -> None:
    assert to_hiragana("ヽヾ") == "ゝゞ"


def test_ac19_small_ka_and_ke_become_small_hiragana() -> None:
    assert to_hiragana("ヵヶ") == "ゕゖ"


@pytest.mark.parametrize(
    "text",
    [
        "ヷヸヹヺ",  # ヷ ヸ ヹ ヺ have no hiragana form
        "ー",
        "・",
        "空々〆",
        "Go! 123",
        "ひかり",
        "",
    ],
)
def test_ac19_characters_without_a_hiragana_form_are_unchanged(text: str) -> None:
    assert to_hiragana(text) == text


def test_ac19_mixed_line_changes_only_the_katakana() -> None:
    assert to_hiragana("ココロ 光る、Go!") == "こころ 光る、Go!"
