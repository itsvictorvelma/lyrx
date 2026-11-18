"""Says which characters are kana and which are kanji."""

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
# Extensions B to H in the supplementary planes; this span also holds the
# compatibility ideographs supplement (U+2F800 .. U+2FA1F).
CJK_SUPPLEMENTARY_IDEOGRAPHS = (0x20000, 0x3134F)
KANJI_RANGES = (
    KANJI_REPEAT_MARK,
    SHIME,
    CJK_EXTENSION_A,
    CJK_UNIFIED_IDEOGRAPHS,
    CJK_COMPATIBILITY_IDEOGRAPHS,
    CJK_SUPPLEMENTARY_IDEOGRAPHS,
)


def in_ranges(character: str, ranges: tuple[tuple[int, int], ...]) -> bool:
    return any(first <= ord(character) <= last for first, last in ranges)


def is_kana(character: str) -> bool:
    return in_ranges(character, KANA_RANGES)


def is_kanji(character: str) -> bool:
    return in_ranges(character, KANJI_RANGES)
