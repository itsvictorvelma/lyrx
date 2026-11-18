"""Says whether cleaned lyrics look Japanese: enough of their lines hold a kana."""

from lyrx import config
from lyrx.kana import is_kana


def looks_japanese(lines: list[str]) -> bool:
    """Kana, not kanji, is what counts, so Chinese lyrics do not look Japanese."""
    non_blank = [line for line in lines if line]
    if not non_blank:
        return False
    with_kana = sum(1 for line in non_blank if any(is_kana(character) for character in line))
    return with_kana >= config.LOOKS_JAPANESE_FRACTION * len(non_blank)
