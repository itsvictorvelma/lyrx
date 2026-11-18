"""Turns LRCLIB's plain lyrics into lines: one per lyric line, one blank line between verses."""

import unicodedata


def read_lyrics(lyrics: str) -> list[str]:
    """The lyrics in NFC (so a decomposed か + U+3099 behaves like が), one line each.

    Line endings are unified and each line is trimmed. Blank lines at the ends are dropped,
    and each run of blank lines becomes one.
    """
    text = unicodedata.normalize("NFC", lyrics).replace("\r\n", "\n").replace("\r", "\n")
    lines: list[str] = []
    for line in (raw.strip() for raw in text.split("\n")):
        if line or (lines and lines[-1]):
            lines.append(line)
    if lines and not lines[-1]:
        lines.pop()
    return lines
