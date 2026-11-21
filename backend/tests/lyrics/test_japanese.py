"""Tests for japanese.py: kana and kanji, has_japanese, and looks_japanese."""

import pytest

from subbed.lyrics.japanese import has_japanese, is_kana, is_kanji, looks_japanese

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


# Japanese detection (AC-8)


@pytest.mark.parametrize(
    "text",
    [
        "ひかる",
        "ココロ",
        "空",
        "々",
        "ー",
        "We 歌う tonight",
        "  ほし",
        "2人で",
    ],
)
def test_ac8_text_with_hiragana_katakana_or_kanji_has_japanese(text: str) -> None:
    assert has_japanese(text) is True


@pytest.mark.parametrize(
    "text",
    [
        "",
        "We sing tonight",
        "123 !?",
        "、。「」\uff01\uff1f",
        "\u3000",
        "\uff21\uff22\uff23",
        "하늘",
        "café",
    ],
)
def test_ac8_text_without_hiragana_katakana_or_kanji_has_no_japanese(text: str) -> None:
    assert has_japanese(text) is False


@pytest.mark.parametrize(
    "text",
    [
        "\u309d",  # hiragana iteration mark
        "\u309e",  # voiced hiragana iteration mark
        "\u30fd",  # katakana iteration mark
        "\u30fe",  # voiced katakana iteration mark
        "\u3006",  # shime
        "\u3400",  # first CJK Extension A ideograph
        "\u4dbf",  # last CJK Extension A ideograph
        "\uf900",  # first CJK Compatibility Ideograph
        "\ufaff",  # last code point of the CJK Compatibility Ideographs block
    ],
)
def test_ac43_iteration_marks_shime_and_extra_ideograph_blocks_have_japanese(text: str) -> None:
    assert has_japanese(text) is True


def test_spec003_ac43_kanji_outside_the_basic_plane_is_japanese() -> None:
    """U+20B9F, a CJK Extension B kanji; AC-43's unknown-word example uses it."""
    assert has_japanese("\U00020b9f") is True


# Looks Japanese


@pytest.mark.parametrize(
    ("lines", "expected"),
    [
        (["君の声が", "", "We sing", "all night", "long"], True),
        (["君の声", "We sing", "all night", "long", "and on"], False),
        (["我爱你", "天空很蓝"], False),
        (["kimi no koe ga"], False),
        ([], False),
    ],
    ids=["one-in-four", "kanji-only-line", "chinese", "romaji-only", "empty"],
)
def test_looks_japanese(lines: list[str], expected: bool) -> None:
    assert looks_japanese(lines) is expected
