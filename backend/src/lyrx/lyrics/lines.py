"""LRCLIB's lyrics as lines: one per lyric line, one blank line between verses, with start times."""

import re
import unicodedata

# A time tag at the start of a timed line: [m:ss], [mm:ss.x], [mm:ss.xx], or [mm:ss.xxx].
TIME_TAG = re.compile(r"\[(\d{1,3}):([0-5]\d)(?:\.(\d{1,3}))?\]")


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


def start_times(lines: list[str], synced_lyrics: str | None) -> list[int | None]:
    """Each line's start in milliseconds, from LRCLIB's timed lyrics; None for blank lines.

    The timed lines must be the same lyric lines, in order, with times that never go back;
    otherwise no line gets a time, since a wrong highlight is worse than none.
    """
    timed = [(start, text) for start, text in read_timed_lines(synced_lyrics or "") if text]
    starts = [start for start, _ in timed]
    matches = [text for _, text in timed] == [line for line in lines if line]
    if not timed or not matches or starts != sorted(starts):
        return [None] * len(lines)
    remaining = iter(starts)
    return [next(remaining) if line else None for line in lines]


def read_timed_lines(synced_lyrics: str) -> list[tuple[int, str]]:
    """Each line that starts with a time tag, as (start in ms, its text read like a lyric line)."""
    timed: list[tuple[int, str]] = []
    for raw in unicodedata.normalize("NFC", synced_lyrics).splitlines():
        line = raw.strip()
        tag = TIME_TAG.match(line)
        if tag is None:
            continue
        minutes, seconds, fraction = tag.groups()
        start = (int(minutes) * 60 + int(seconds)) * 1000 + int((fraction or "0").ljust(3, "0"))
        timed.append((start, line[tag.end() :].strip()))
    return timed
