"""Says which characters are kana and kanji, and turns katakana into hiragana."""

# Inclusive Unicode code point ranges, grouped by kind.

# Kana
HIRAGANA = (0x3041, 0x3096)  # ぁ .. ゖ
HIRAGANA_ITERATION_MARKS = (0x309D, 0x309E)  # ゝ ゞ
KATAKANA = (0x30A1, 0x30FA)  # ァ .. ヺ
KATAKANA_LONG_MARK = (0x30FC, 0x30FC)  # ー
KATAKANA_ITERATION_MARKS = (0x30FD, 0x30FE)  # ヽ ヾ
KANA_RANGES = (
    HIRAGANA,
    HIRAGANA_ITERATION_MARKS,
    KATAKANA,
    KATAKANA_LONG_MARK,
    KATAKANA_ITERATION_MARKS,
)

# Kanji
KANJI_REPEAT_MARK = (0x3005, 0x3005)  # 々
SHIME = (0x3006, 0x3006)  # 〆
CJK_EXTENSION_A = (0x3400, 0x4DBF)  # 㐀 .. end of the block
CJK_UNIFIED_IDEOGRAPHS = (0x4E00, 0x9FFF)  # 一 .. end of the block
CJK_COMPATIBILITY_IDEOGRAPHS = (0xF900, 0xFAFF)  # 豈 .. end of the block
KANJI_RANGES = (
    KANJI_REPEAT_MARK,
    SHIME,
    CJK_EXTENSION_A,
    CJK_UNIFIED_IDEOGRAPHS,
    CJK_COMPATIBILITY_IDEOGRAPHS,
)

# Each katakana sits 0x60 code points above its hiragana (ア U+30A2, あ U+3042).
# ヷ ヸ ヹ ヺ and ー have no hiragana form, so they are left out.
KATAKANA_TO_HIRAGANA_OFFSET = 0x60
KATAKANA_WITH_HIRAGANA = [
    *range(ord("ァ"), ord("ヶ") + 1),
    *range(ord("ヽ"), ord("ヾ") + 1),
]
KATAKANA_TO_HIRAGANA = {code: code - KATAKANA_TO_HIRAGANA_OFFSET for code in KATAKANA_WITH_HIRAGANA}


def in_ranges(character: str, ranges: tuple[tuple[int, int], ...]) -> bool:
    return any(first <= ord(character) <= last for first, last in ranges)


def is_kana(character: str) -> bool:
    return in_ranges(character, KANA_RANGES)


def is_hiragana_letter(character: str) -> bool:
    """A hiragana letter, small kana included; not ゝ, ゞ, or ー."""
    return in_ranges(character, (HIRAGANA,))


def is_kanji(character: str) -> bool:
    return in_ranges(character, KANJI_RANGES)


def to_hiragana(text: str) -> str:
    """Turns each katakana that has a hiragana form into it; everything else is unchanged."""
    return text.translate(KATAKANA_TO_HIRAGANA)
