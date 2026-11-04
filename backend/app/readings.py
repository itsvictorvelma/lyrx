"""Read hiragana and romaji from a lyric line.

The same line always produces the same reading. Groq does not write these
columns. ponytail: unidic-lite uses the common dictionary reading, so a
lyric-specific yomi such as a sung name stays wrong until that line is edited.
"""

import re

import jaconv

_JAPANESE = re.compile(r"[\u3040-\u30ff\u4e00-\u9fff]")
_tagger = None
_cutlet = None


def reading_for(text: str) -> tuple[str, str]:
    raw = " ".join(text.split())
    if not raw or _JAPANESE.search(raw) is None:
        return raw, raw
    tagger, cutter = _tools()
    hiragana: list[str] = []
    romaji: list[str] = []
    for phrase in raw.split(" "):
        if _JAPANESE.search(phrase) is None:
            hiragana.append(phrase)
            romaji.append(phrase)
            continue
        words = list(tagger(phrase))
        tokens = cutter.romaji_tokens(words, capitalize=False)
        if len(tokens) != len(words):
            hiragana.append("".join(_hiragana(word) for word in words))
            romaji.append(cutter.romaji(phrase, capitalize=False).lower())
            continue
        group_h: list[str] = []
        group_r: list[str] = []
        for word, token in zip(words, tokens, strict=True):
            group_h.append(_hiragana(word))
            surface = token.surface.lower() if _JAPANESE.search(word.surface) else token.surface
            group_r.append(surface)
            if token.space:
                hiragana.append("".join(group_h))
                romaji.append("".join(group_r))
                group_h = []
                group_r = []
        if group_h:
            hiragana.append("".join(group_h))
            romaji.append("".join(group_r))
    return _join(hiragana) or raw, _join(romaji) or raw


def _tools():
    global _tagger, _cutlet
    if _tagger is None or _cutlet is None:
        import cutlet
        import fugashi

        _tagger = fugashi.Tagger()
        _cutlet = cutlet.Cutlet()
        _cutlet.use_wo = False
    return _tagger, _cutlet


def _hiragana(word) -> str:
    surface = word.surface
    if _JAPANESE.search(surface) is None:
        return surface
    kana = getattr(word.feature, "kana", None) or ""
    if kana and kana != "*":
        return jaconv.kata2hira(kana)
    return jaconv.kata2hira(surface)


def _join(parts: list[str]) -> str:
    return " ".join(part for part in parts if part)
