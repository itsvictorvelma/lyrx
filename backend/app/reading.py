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


_PARTICLE = set("はをがにへでとものやねよかさな")


def units(text: str) -> list[tuple[str, str]]:
    """Split a line into kanji slots and kana the model must not rewrite.

    A kanji run keeps the hiragana glued to it (okurigana). A one-character
    particle stays outside the slot. Katakana stays outside, so ニガ cannot
    come back as にか.
    """

    raw = _char_runs(text)
    parts: list[tuple[str, str]] = []
    index = 0
    while index < len(raw):
        is_kanji, surface = raw[index]
        follower = raw[index + 1][1] if index + 1 < len(raw) else ""
        if is_kanji and _okurigana(follower) and follower[0] not in _PARTICLE:
            parts.append(("slot", surface + follower))
            index += 2
            continue
        if is_kanji:
            parts.append(("slot", surface))
            index += 1
            continue
        # A particle glued to the next word (はきっと, には) is its own keep.
        # A kana word that merely starts with に or か stays whole.
        if (
            parts
            and parts[-1][0] == "slot"
            and len(surface) > 1
            and surface[0] in _PARTICLE
        ):
            parts.append(("keep", surface[0]))
            parts.append(("keep", surface[1:]))
            index += 1
            continue
        parts.append(("keep", surface))
        index += 1
    return parts


def marked(text: str) -> str:
    shown: list[str] = []
    for kind, surface in units(text):
        shown.append(f"【{surface}】" if kind == "slot" else surface)
    return "".join(shown)


def needs_model(text: str) -> bool:
    return has_kanji(text) or bool(_kana_core(text))


def assemble_reading(original: str, readings: list[str]) -> tuple[str, str]:
    """Build hiragana and romaji. Kana comes from the original line."""

    parts = units(original.strip())
    expected = [surface for kind, surface in parts if kind == "slot"]
    if len(readings) != len(expected):
        raise ReadingError("reading does not match the line")
    spoken: list[str] = []
    slot = 0
    for kind, surface in parts:
        if kind == "keep":
            spoken.append(_break_particle(to_hiragana(surface)))
            continue
        spoken.append(_break_particle(_slot_reading(surface, readings[slot])))
        slot += 1
    hiragana = " ".join(part for part in spoken if part.strip())
    hiragana = re.sub(r" +", " ", hiragana).strip()
    romaji = hepburn(hiragana)
    if not romaji:
        raise ReadingError("reading does not match the line")
    return hiragana, romaji


def line_reading(original: str, raw: object) -> tuple[str, str]:
    """Hiragana and romaji for one original line that came back in the completion.

    A line with no kanji is copied. A reading that already contains the line's
    kana is split across the brackets. Otherwise each bracket is read on its
    own, and kana the model left out of that bracket is copied from the line.
    """

    source = original.strip()
    expected = sum(1 for kind, _surface in units(source) if kind == "slot")
    if expected == 0:
        return assemble_reading(source, [])
    pieces = _reading_pieces(raw, expected)
    joined = "".join(pieces)
    fitted = _fit_slots(source, joined)
    if fitted is not None:
        try:
            return assemble_reading(source, fitted)
        except ReadingError:
            pass
    if len(pieces) == expected:
        return assemble_reading(source, pieces)
    return lock_reading(source, joined)


def _char_runs(text: str) -> list[tuple[bool, str]]:
    runs: list[tuple[bool, str]] = []
    for char in text:
        flag = bool(_KANJI.search(char))
        if runs and runs[-1][0] == flag:
            runs[-1] = (flag, runs[-1][1] + char)
            continue
        runs.append((flag, char))
    return runs


def _okurigana(surface: str) -> bool:
    return bool(surface) and all(_is_hiragana(char) for char in surface) and surface not in _PARTICLE


def _reading_pieces(raw: object, expected: int) -> list[str]:
    if isinstance(raw, list):
        if not all(isinstance(item, str) for item in raw):
            raise ReadingError("reading does not match the line")
        return [item.strip() for item in raw]
    if not isinstance(raw, str):
        raise ReadingError("reading does not match the line")
    text = raw.strip()
    if not text:
        return []
    for separator in ("|", "\n"):
        parts = [part.strip() for part in text.split(separator) if part.strip()]
        if len(parts) == expected:
            return parts
    parts = [part for part in text.split() if part]
    if len(parts) == expected:
        return parts
    return [text]


def _fit_slots(original: str, reading: str) -> list[str] | None:
    """Split one hiragana reading across the kanji, using the original kana as anchors."""

    compact = _kana_core(to_hiragana(reading))
    if not compact or not _keeps_kana(original, compact):
        return None
    slots: list[str] = []
    cursor = 0
    for kind, surface in units(original.strip()):
        if kind == "slot":
            slots.append("")
            continue
        anchor = _kana_core(surface)
        if not anchor:
            continue
        found = compact.find(anchor, cursor)
        if found < 0:
            return None
        gap = compact[cursor:found]
        if gap:
            if not slots:
                return None
            slots[-1] += gap
        cursor = found + len(anchor)
    if cursor < len(compact):
        if not slots:
            return None
        slots[-1] += compact[cursor:]
    if not slots or any(not item for item in slots):
        return None
    return slots


def _slot_reading(surface: str, reading: str) -> str:
    kana = to_hiragana(reading.strip())
    compact = kana.replace(" ", "")
    if not compact or has_kanji(compact):
        raise ReadingError("reading does not match the line")
    # ponytail: pop lyrics sing わたし and あした. A song that really sings
    # わたくし or あす would need this guard removed.
    if surface == "私" and compact == "わたくし":
        return "わたし"
    if surface == "明日" and compact == "あす":
        return "あした"
    if _keeps_kana(surface, compact):
        return reading.strip()
    # The bracket can hold kana after the kanji. That kana is still the
    # original line, so a reading of the kanji does not drop it.
    return _with_slot_kana(compact, surface)


def _with_slot_kana(reading: str, surface: str) -> str:
    kana = _kana_core(surface)
    if not kana:
        return reading
    for size in range(len(kana), 0, -1):
        if reading.endswith(kana[:size]):
            return reading + kana[size:]
    return reading + kana


def _break_particle(text: str) -> str:
    if len(text) > 1 and text[-1] in {"は", "へ"}:
        return f"{text[:-1]} {text[-1]}"
    return text


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
