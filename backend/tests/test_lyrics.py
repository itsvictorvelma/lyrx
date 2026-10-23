import pytest

from app.errors import ApiError
from app.lyrics import align_lyrics, decode_lyric_file


def test_align_lyrics_keeps_order_and_drops_blank_separators() -> None:
    lines = align_lyrics("雨\n\n空\n", "ame\n\nsora\n", "rain\n\nsky\n")

    assert lines == [("雨", "ame", "rain"), ("空", "sora", "sky")]


def test_decode_strips_bom_and_normalizes_newlines() -> None:
    text = decode_lyric_file("\ufeff雨\r\n空\r".encode("utf-8"), "original.txt")

    assert align_lyrics(text, "ame\nsora", "rain\nsky") == [("雨", "ame", "rain"), ("空", "sora", "sky")]


def test_align_lyrics_reports_each_line_count() -> None:
    with pytest.raises(ApiError, match="original.txt has 2") as error:
        align_lyrics("雨\n空\n", "ame\n", "rain\nsky\n")

    assert error.value.code == "line_count_mismatch"


def test_align_lyrics_rejects_a_partial_blank_row() -> None:
    with pytest.raises(ApiError, match="Row 2") as error:
        align_lyrics("雨\n\n", "ame\nsora\n", "rain\nsky\n")

    assert error.value.code == "partial_blank_row"
