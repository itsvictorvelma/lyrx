"""Spells hiragana as modified Hepburn romaji, without macrons.

The text is read word by word, splitting on spaces. Katakana is turned into
hiragana first. Each word is cut into sounds, taking a two-kana sound such as
きゃ before a single kana. Then the marks are resolved in order: the iteration
marks ゝ and ゞ, small っ, the long mark ー, and ん. A word that is exactly は or
へ is a particle and reads wa or e.
"""

import string

# One kana chart row per line.
BASIC_SOUNDS = {
    "あ": "a", "い": "i", "う": "u", "え": "e", "お": "o",
    "か": "ka", "き": "ki", "く": "ku", "け": "ke", "こ": "ko",
    "さ": "sa", "し": "shi", "す": "su", "せ": "se", "そ": "so",
    "た": "ta", "ち": "chi", "つ": "tsu", "て": "te", "と": "to",
    "な": "na", "に": "ni", "ぬ": "nu", "ね": "ne", "の": "no",
    "は": "ha", "ひ": "hi", "ふ": "fu", "へ": "he", "ほ": "ho",
    "ま": "ma", "み": "mi", "む": "mu", "め": "me", "も": "mo",
    "や": "ya", "ゆ": "yu", "よ": "yo",
    "ら": "ra", "り": "ri", "る": "ru", "れ": "re", "ろ": "ro",
    "わ": "wa", "ゐ": "wi", "ゑ": "we", "を": "o",
}  # fmt: skip

VOICED_SOUNDS = {
    "が": "ga", "ぎ": "gi", "ぐ": "gu", "げ": "ge", "ご": "go",
    "ざ": "za", "じ": "ji", "ず": "zu", "ぜ": "ze", "ぞ": "zo",
    "だ": "da", "ぢ": "ji", "づ": "zu", "で": "de", "ど": "do",
    "ば": "ba", "び": "bi", "ぶ": "bu", "べ": "be", "ぼ": "bo",
    "ぱ": "pa", "ぴ": "pi", "ぷ": "pu", "ぺ": "pe", "ぽ": "po",
}  # fmt: skip

# A small kana that cannot join the kana before it is read as its own sound.
SMALL_SOUNDS = {
    "ぁ": "a", "ぃ": "i", "ぅ": "u", "ぇ": "e", "ぉ": "o",
    "\u3095": "ka", "\u3096": "ke",  # small か and け
    "ゃ": "ya", "ゅ": "yu", "ょ": "yo",
    "ゎ": "wa",
}  # fmt: skip

COMBINED_SOUNDS = {
    "きゃ": "kya", "きゅ": "kyu", "きょ": "kyo",
    "ぎゃ": "gya", "ぎゅ": "gyu", "ぎょ": "gyo",
    "しゃ": "sha", "しゅ": "shu", "しょ": "sho",
    "じゃ": "ja", "じゅ": "ju", "じょ": "jo",
    "ちゃ": "cha", "ちゅ": "chu", "ちょ": "cho",
    "ぢゃ": "ja", "ぢゅ": "ju", "ぢょ": "jo",
    "にゃ": "nya", "にゅ": "nyu", "にょ": "nyo",
    "ひゃ": "hya", "ひゅ": "hyu", "ひょ": "hyo",
    "びゃ": "bya", "びゅ": "byu", "びょ": "byo",
    "ぴゃ": "pya", "ぴゅ": "pyu", "ぴょ": "pyo",
    "みゃ": "mya", "みゅ": "myu", "みょ": "myo",
    "りゃ": "rya", "りゅ": "ryu", "りょ": "ryo",
}  # fmt: skip

# Sounds from loanwords.
EXTENDED_SOUNDS = {
    "ふぁ": "fa", "ふぃ": "fi", "ふぇ": "fe", "ふぉ": "fo", "ふゅ": "fyu",
    "てぃ": "ti", "でぃ": "di", "とぅ": "tu", "どぅ": "du",
    "しぇ": "she", "じぇ": "je", "ちぇ": "che",
    "いぇ": "ye", "うぃ": "wi", "うぇ": "we", "うぉ": "wo",
    "ゔ": "vu", "ゔぁ": "va", "ゔぃ": "vi", "ゔぇ": "ve", "ゔぉ": "vo",
}  # fmt: skip

SOUNDS = BASIC_SOUNDS | VOICED_SOUNDS | SMALL_SOUNDS | COMBINED_SOUNDS | EXTENDED_SOUNDS

# The voiced form of a kana, used by the voiced iteration mark ゞ.
VOICED_FORMS = {
    "う": "ゔ",
    "か": "が", "き": "ぎ", "く": "ぐ", "け": "げ", "こ": "ご",
    "さ": "ざ", "し": "じ", "す": "ず", "せ": "ぜ", "そ": "ぞ",
    "た": "だ", "ち": "ぢ", "つ": "づ", "て": "で", "と": "ど",
    "は": "ば", "ひ": "び", "ふ": "ぶ", "へ": "べ", "ほ": "ぼ",
}  # fmt: skip

# The kana that spells each vowel, used to write out the long mark ー.
VOWEL_KANA = {"a": "あ", "i": "い", "u": "う", "e": "え", "o": "お"}
VOWELS = "aiueo"

# "\uff01" and "\uff1f" are the full-width ! and ?.
PUNCTUATION = {"、": ",", "。": ".", "\uff01": "!", "\uff1f": "?", "「": '"', "」": '"'}
FULL_WIDTH_SPACE = "\u3000"
# Punctuation that may sit at either end of a word without hiding a particle.
# Ellipsis, full-width tilde, wave dash, white corner brackets, middle dot.
# They pass through unchanged.
OTHER_JAPANESE_PUNCTUATION = "\u2026\uff5e\u301c\u300e\u300f\u30fb"
ATTACHED_PUNCTUATION = "".join(PUNCTUATION) + OTHER_JAPANESE_PUNCTUATION + string.punctuation

PARTICLE_SOUNDS = {"は": "wa", "へ": "e"}

SMALL_TSU = "っ"
SYLLABIC_N = "ん"
# ん before these first letters is written n' so it is not read as part of the next sound.
APOSTROPHE_BEFORE = VOWELS + "y"
LONG_MARK = "ー"
ITERATION_MARK = "ゝ"
VOICED_ITERATION_MARK = "ゞ"

# Each katakana sits 0x60 code points above its hiragana (ア U+30A2, あ U+3042).
KATAKANA_TO_HIRAGANA_OFFSET = 0x60
KATAKANA_WITH_HIRAGANA = [
    *range(ord("ァ"), ord("ヶ") + 1),
    *range(ord("ヽ"), ord("ヾ") + 1),
]
KATAKANA_TO_HIRAGANA = {code: code - KATAKANA_TO_HIRAGANA_OFFSET for code in KATAKANA_WITH_HIRAGANA}


def to_romaji(text: str) -> str:
    """Spells a line of hiragana (or katakana) as romaji, keeping its spacing."""
    hiragana = text.translate(KATAKANA_TO_HIRAGANA).replace(FULL_WIDTH_SPACE, " ")
    return " ".join(spell_word(word) for word in hiragana.split(" "))


def spell_word(word: str) -> str:
    """Spells one word, reading it as a particle when it is exactly は or へ plus punctuation."""
    # ponytail: a word that is exactly は is always the particle wa, so the rare
    # noun は (tooth) written alone is spelled wa too. Telling them apart needs
    # the original kanji or grammar, which this function does not see.
    particle = word.strip(ATTACHED_PUNCTUATION)
    if particle in PARTICLE_SOUNDS:
        before, _, after = word.partition(particle)
        return spell_kana(before) + PARTICLE_SOUNDS[particle] + spell_kana(after)
    return spell_kana(word)


def spell_kana(text: str) -> str:
    """Spells a run of text with no spaces; characters that are not kana pass through."""
    sounds = split_into_sounds(text)
    sounds = apply_iteration_marks(sounds)
    sounds = drop_unused_small_tsu(sounds)
    sounds = apply_long_marks(sounds)
    return "".join(spell_sound(sounds, index) for index in range(len(sounds)))


def split_into_sounds(text: str) -> list[str]:
    """Cuts text into sounds, taking a two-kana sound before a single character."""
    sounds: list[str] = []
    index = 0
    while index < len(text):
        length = 2 if text[index : index + 2] in SOUNDS else 1
        sounds.append(text[index : index + length])
        index += length
    return sounds


def apply_iteration_marks(sounds: list[str]) -> list[str]:
    """ゝ repeats the sound before it and ゞ repeats it voiced; with no sound before, they drop."""
    result: list[str] = []
    for sound in sounds:
        if sound not in (ITERATION_MARK, VOICED_ITERATION_MARK):
            result.append(sound)
        elif result and result[-1] in SOUNDS:
            previous = result[-1]
            if sound == VOICED_ITERATION_MARK:
                previous = VOICED_FORMS.get(previous[0], previous[0]) + previous[1:]
            result.append(previous)
    return result


def drop_unused_small_tsu(sounds: list[str]) -> list[str]:
    """Keeps a small っ only when the next sound starts with a consonant it can double."""
    return [
        sound
        for index, sound in enumerate(sounds)
        if sound != SMALL_TSU or starts_with_consonant(next_sound(sounds, index))
    ]


def starts_with_consonant(sound: str) -> bool:
    """True for a kana sound whose romaji starts with a consonant; marks and non-kana are not."""
    return sound in SOUNDS and SOUNDS[sound][0] not in VOWELS


def next_sound(sounds: list[str], index: int) -> str:
    """The sound after `index`, or an empty string at the end of the word."""
    return sounds[index + 1] if index + 1 < len(sounds) else ""


def apply_long_marks(sounds: list[str]) -> list[str]:
    """ー becomes the vowel of the sound before it; with no vowel before, it drops."""
    result: list[str] = []
    for sound in sounds:
        if sound != LONG_MARK:
            result.append(sound)
        elif result and result[-1] in SOUNDS:
            result.append(VOWEL_KANA[SOUNDS[result[-1]][-1]])
    return result


def spell_sound(sounds: list[str], index: int) -> str:
    """Spells one sound; っ and ん depend on the sound after them."""
    sound = sounds[index]
    following = SOUNDS.get(next_sound(sounds, index), "")
    if sound == SMALL_TSU:
        # drop_unused_small_tsu already removed any っ not followed by a consonant sound.
        return "t" if following.startswith("ch") else following[:1]
    if sound == SYLLABIC_N:
        return "n'" if following and following[0] in APOSTROPHE_BEFORE else "n"
    return SOUNDS.get(sound) or PUNCTUATION.get(sound, sound)
