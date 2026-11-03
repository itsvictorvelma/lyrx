"""Place a start time on each lyric line.

The matcher compares the lyric text with timed words from a speech scan.
When those words do not resemble the lyrics, each line gets a share of the
scanned span based on how many characters it has. That result is a first pass.
"""

from __future__ import annotations

import difflib
import unicodedata
from dataclasses import dataclass

# Below this, shared characters are treated as a coincidence.
_MATCH_RATIO = 0.25


@dataclass(frozen=True)
class TimedWord:
    text: str
    start: float
    end: float


def assign_line_starts(lines: list[str], words: list[TimedWord]) -> list[float | None]:
    if not lines:
        return []
    usable = sorted(
        (word for word in words if word.text.strip() and word.end >= word.start >= 0),
        key=lambda word: (word.start, word.end),
    )
    if not usable:
        return [None] * len(lines)

    vocal_start = usable[0].start
    vocal_end = max(word.end for word in usable)
    lyric_chars = [(index, char) for index, line in enumerate(lines) for char in _normalize(line)]
    word_chars = _word_chars(usable)
    if not lyric_chars or not word_chars:
        return _spread_lines(lines, vocal_start, vocal_end)

    lyric_text = "".join(char for _, char in lyric_chars)
    heard_text = "".join(char for _, char in word_chars)
    matcher = difflib.SequenceMatcher(a=lyric_text, b=heard_text, autojunk=False)
    if matcher.ratio() < _MATCH_RATIO:
        return _spread_lines(lines, vocal_start, vocal_end)

    found: list[float | None] = [None] * len(lines)
    for block in matcher.get_matching_blocks():
        if block.size == 0:
            continue
        for offset in range(block.size):
            line_index = lyric_chars[block.a + offset][0]
            if found[line_index] is None:
                found[line_index] = word_chars[block.b + offset][0]
    return _fill_gaps(lines, found, vocal_start, vocal_end)


def _word_chars(words: list[TimedWord]) -> list[tuple[float, str]]:
    chars: list[tuple[float, str]] = []
    for word in words:
        normalized = _normalize(word.text)
        if not normalized:
            continue
        span = max(word.end - word.start, 0.0)
        step = span / len(normalized)
        chars.extend((word.start + step * offset, char) for offset, char in enumerate(normalized))
    return chars


def _normalize(text: str) -> str:
    folded = unicodedata.normalize("NFKC", text).casefold()
    return "".join(char for char in folded if char.isalnum())


def _spread_lines(lines: list[str], start: float, end: float) -> list[float]:
    weights = [max(len(_normalize(line)), 1) for line in lines]
    return _monotonic(_slice_starts(weights, start, max(end, start)))


def _fill_gaps(
    lines: list[str],
    found: list[float | None],
    vocal_start: float,
    vocal_end: float,
) -> list[float]:
    weights = [max(len(_normalize(line)), 1) for line in lines]
    placed = list(found)
    anchors = [index for index, value in enumerate(placed) if value is not None]
    if not anchors:
        return _spread_lines(lines, vocal_start, vocal_end)

    first = anchors[0]
    first_time = placed[first]
    if first > 0 and first_time is not None:
        for index, value in enumerate(_slice_starts(weights[:first], vocal_start, first_time)):
            placed[index] = min(value, first_time)

    for left, right in zip(anchors, anchors[1:], strict=False):
        if right <= left + 1:
            continue
        left_time = placed[left]
        right_time = placed[right]
        if left_time is None or right_time is None:
            continue
        middle = _interior_starts(weights[left + 1 : right], left_time, right_time)
        for offset, value in enumerate(middle):
            placed[left + 1 + offset] = value

    last = anchors[-1]
    last_time = placed[last]
    if last < len(placed) - 1 and last_time is not None:
        tail = _interior_starts(weights[last + 1 :], last_time, max(vocal_end, last_time))
        for offset, value in enumerate(tail):
            placed[last + 1 + offset] = value

    return _monotonic([vocal_start if value is None else value for value in placed])


def _interior_starts(weights: list[int], start: float, end: float) -> list[float]:
    """Start times after `start` and before `end`, split by character weight."""
    if not weights:
        return []
    total = sum(weight or 1 for weight in weights)
    span = max(end - start, 0.0)
    usable = span * total / (total + max(weight or 1 for weight in weights))
    cursor = start
    starts: list[float] = []
    for weight in weights:
        cursor += usable * (weight or 1) / total
        starts.append(min(cursor, end))
    return starts


def _slice_starts(weights: list[int], start: float, end: float) -> list[float]:
    if not weights:
        return []
    total = sum(weights) or len(weights)
    span = max(end - start, 0.0)
    cursor = start
    starts: list[float] = []
    for weight in weights:
        starts.append(cursor)
        cursor += span * (weight or 1) / total
    return starts


def _monotonic(starts: list[float]) -> list[float]:
    cleaned: list[float] = []
    for start in starts:
        value = round(max(start, 0.0), 3)
        if cleaned and value <= cleaned[-1]:
            value = round(cleaned[-1] + 0.01, 3)
        cleaned.append(value)
    return cleaned
