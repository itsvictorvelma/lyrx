"""Turn the three lyric files into ordered lines.

Line numbers start at 0. A blank row is kept only when all three files are blank
there, and those separator rows are left out of the saved song.
"""

import hashlib
import json

from app.contracts import TIMING_FIELDS, LyricLine
from app.errors import DomainError

TEXT_FILES = ("original.txt", "pronunciation.txt", "translation.txt")


def decode_lyric_file(data: bytes, filename: str) -> str:
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        raise DomainError("invalid_text", f"{filename} must be UTF-8.")
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise DomainError("invalid_text", f"{filename} must be UTF-8.") from exc


def align_lyrics(original: str, pronunciation: str, translation: str) -> list[tuple[str, str, str]]:
    rows = {
        "original.txt": original.splitlines(),
        "pronunciation.txt": pronunciation.splitlines(),
        "translation.txt": translation.splitlines(),
    }
    counts = {name: len(lines) for name, lines in rows.items()}
    if len(set(counts.values())) != 1:
        counted = ", ".join(f"{name} has {count}" for name, count in counts.items())
        raise DomainError("line_count_mismatch", f"The lyric files have different line counts: {counted}.")

    aligned: list[tuple[str, str, str]] = []
    for row_number, trio in enumerate(zip(*rows.values(), strict=True), start=1):
        blank_files = [name for name, text in zip(TEXT_FILES, trio, strict=True) if text == ""]
        if len(blank_files) == 3:
            continue
        if blank_files:
            names = ", ".join(blank_files)
            raise DomainError(
                "partial_blank_row",
                f"Row {row_number} is blank in {names} but not in every lyric file.",
            )
        aligned.append(trio)

    if not aligned:
        raise DomainError("empty_song", "The lyric files do not contain any lines.")
    return aligned


def load_lines(raw_lines: object) -> list[LyricLine]:
    if not isinstance(raw_lines, list):
        raise ValueError("lyric lines must be a list")
    lines: list[LyricLine] = []
    for raw in raw_lines:
        if isinstance(raw, dict):
            raw = {key: value for key, value in raw.items() if key not in TIMING_FIELDS}
        lines.append(LyricLine.model_validate(raw))
    return lines


def dump_lines(lines: list[LyricLine]) -> str:
    return json.dumps([line.model_dump(mode="json") for line in lines], ensure_ascii=False)


def content_hash(lines_json: str) -> str:
    return hashlib.sha256(lines_json.encode("utf-8")).hexdigest()
