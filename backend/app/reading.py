"""Hiragana readings and Hepburn romaji.

Romaji is spelled from the hiragana, so the two columns cannot drift apart.
Long vowels stay written out (おう is ou, ー doubles the vowel) so each mora
is visible. Particles は and へ are spoken as wa and e only when that spaced
word is exactly the particle. こんにちは and こんばんは are the other exceptions.
ponytail: a morphological split would also catch an unspaced わたしは.
Iteration marks are copied through.
"""

import re

_KANJI = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\u3005]")
_GREETINGS = {"こんにちは": "konnichiwa", "こんばんは": "konbanwa"}
_PUNCT = {
    "、": ",",
    "。": ".",
    "！": "!",
    "？": "?",
    "・": " ",
    "「": '"',
    "」": '"',
    "…": "...",
    "〜": "",
    "～": "",
}


class ReadingError(ValueError):
    pass


def has_kanji(text: str) -> bool:
    return _KANJI.search(text) is not None


def to_hiragana(text: str) -> str:
    return "".join(_hiragana_char(char) for char in text)


def lock_reading(original: str, reading: str) -> tuple[str, str]:
    """Return the hiragana and romaji to store for one original line."""

    source = original.strip()
    if not has_kanji(source):
        kana = to_hiragana(source)
    else:
        kana = to_hiragana(reading.strip())
        if has_kanji(kana) or (kana == "よみ" and source != "よみ") or not _keeps_kana(source, kana):
            raise ReadingError("reading does not match the line")
    romaji = hepburn(kana)
    if not romaji:
        raise ReadingError("reading does not match the line")
    return kana, romaji


def hepburn(text: str) -> str:
    hira = to_hiragana(text).replace("\u3000", " ")
    parts: list[str] = []
    for token in re.split(r"(\s+)", hira):
        if not token:
            continue
        parts.append(" " if token.isspace() else _token(token))
    return re.sub(r" +", " ", "".join(parts)).strip()


def _hiragana_char(char: str) -> str:
    code = ord(char)
    if 0x30A1 <= code <= 0x30F6:
        return chr(code - 0x60)
    return char


def _is_hiragana(char: str) -> bool:
    code = ord(char)
    return 0x3041 <= code <= 0x3096


def _keeps_kana(original: str, reading: str) -> bool:
    found = iter(_kana_core(reading))
    return all(char in found for char in _kana_core(original))


def _kana_core(text: str) -> str:
    return "".join(char for char in to_hiragana(text) if _is_hiragana(char) or char == "ー")


def _token(token: str) -> str:
    core = _kana_core(token)
    if core in _GREETINGS or core in {"は", "へ"}:
        spoken = _GREETINGS.get(core, "wa" if core == "は" else "e")
        return _replace_kana(token, spoken)
    return _walk(token)


def _replace_kana(token: str, spoken: str) -> str:
    out: list[str] = []
    used = False
    for char in token:
        if _is_hiragana(char) or char == "ー":
            if not used:
                out.append(spoken)
                used = True
            continue
        out.append(_PUNCT.get(char, char))
    return "".join(out)


def _walk(token: str) -> str:
    out: list[str] = []
    index = 0
    while index < len(token):
        char = token[index]
        if char in _PUNCT:
            out.append(_PUNCT[char])
            index += 1
            continue
        if char == "っ":
            found = _mora(token, index + 1)
            if found is None:
                out.append("'")
                index += 1
                continue
            mora, nxt = found
            spelled = _spell(mora)
            out.append(("t" if spelled.startswith("ch") else spelled[0]) + spelled)
            index = nxt
            continue
        if char == "ん":
            nxt = token[index + 1] if index + 1 < len(token) else ""
            out.append("n'" if nxt and nxt in "あいうえおやゆよ" else "n")
            index += 1
            continue
        if char == "ー":
            _lengthen(out)
            index += 1
            continue
        if not _is_hiragana(char):
            out.append(char)
            index += 1
            continue
        mora, nxt = _mora(token, index)
        if mora is None:
            break
        out.append(_spell(mora))
        index = nxt
    return "".join(out)


def _mora(text: str, index: int) -> tuple[str, int] | None:
    if index >= len(text) or not _is_hiragana(text[index]):
        return None
    pair = text[index : index + 2]
    if pair in _DIGRAPHS:
        return pair, index + 2
    return text[index], index + 1


def _lengthen(out: list[str]) -> None:
    if not out:
        return
    for vowel in "aiueo":
        if out[-1].endswith(vowel):
            out[-1] += vowel
            return


def _gojuon(head: str, kana: str) -> dict[str, str]:
    return {syllable: head + vowel for syllable, vowel in zip(kana, "aiueo", strict=True)}


_MONO: dict[str, str] = {}
for _head, _kana in (
    ("", "あいうえお"),
    ("k", "かきくけこ"),
    ("s", "さしすせそ"),
    ("t", "たちつてと"),
    ("n", "なにぬねの"),
    ("h", "はひふへほ"),
    ("m", "まみむめも"),
    ("r", "らりるれろ"),
    ("g", "がぎぐげご"),
    ("z", "ざじずぜぞ"),
    ("d", "だぢづでど"),
    ("b", "ばびぶべぼ"),
    ("p", "ぱぴぷぺぽ"),
):
    _MONO.update(_gojuon(_head, _kana))
_MONO.update(
    {
        "し": "shi",
        "ち": "chi",
        "つ": "tsu",
        "ふ": "fu",
        "や": "ya",
        "ゆ": "yu",
        "よ": "yo",
        "わ": "wa",
        "じ": "ji",
        "ぢ": "ji",
        "づ": "zu",
        "を": "o",
        "ゐ": "i",
        "ゑ": "e",
        "ゔ": "vu",
        "ぁ": "a",
        "ぃ": "i",
        "ぅ": "u",
        "ぇ": "e",
        "ぉ": "o",
        "ゃ": "ya",
        "ゅ": "yu",
        "ょ": "yo",
        "ゎ": "wa",
    }
)
_DIGRAPHS = {
    "きゃ": "kya",
    "きゅ": "kyu",
    "きょ": "kyo",
    "ぎゃ": "gya",
    "ぎゅ": "gyu",
    "ぎょ": "gyo",
    "しゃ": "sha",
    "しゅ": "shu",
    "しょ": "sho",
    "じゃ": "ja",
    "じゅ": "ju",
    "じょ": "jo",
    "ちゃ": "cha",
    "ちゅ": "chu",
    "ちょ": "cho",
    "にゃ": "nya",
    "にゅ": "nyu",
    "にょ": "nyo",
    "ひゃ": "hya",
    "ひゅ": "hyu",
    "ひょ": "hyo",
    "びゃ": "bya",
    "びゅ": "byu",
    "びょ": "byo",
    "ぴゃ": "pya",
    "ぴゅ": "pyu",
    "ぴょ": "pyo",
    "みゃ": "mya",
    "みゅ": "myu",
    "みょ": "myo",
    "りゃ": "rya",
    "りゅ": "ryu",
    "りょ": "ryo",
    "ぢゃ": "ja",
    "ぢゅ": "ju",
    "ぢょ": "jo",
    "しぇ": "she",
    "じぇ": "je",
    "ちぇ": "che",
    "ふぁ": "fa",
    "ふぃ": "fi",
    "ふぇ": "fe",
    "ふぉ": "fo",
    "ふゅ": "fyu",
    "てぃ": "ti",
    "でぃ": "di",
    "とぅ": "tu",
    "どぅ": "du",
    "うぃ": "wi",
    "うぇ": "we",
    "うぉ": "wo",
    "ゔぁ": "va",
    "ゔぃ": "vi",
    "ゔぇ": "ve",
    "ゔぉ": "vo",
    "ゔゅ": "vyu",
    "つぁ": "tsa",
    "つぃ": "tsi",
    "つぇ": "tse",
    "つぉ": "tso",
}


def _spell(mora: str) -> str:
    if mora in _DIGRAPHS:
        return _DIGRAPHS[mora]
    return _MONO.get(mora, mora)
