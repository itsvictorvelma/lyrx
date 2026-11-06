from app.generation.lrclib import choose_plain, lyric_lines


def test_section_labels_are_not_lyric_lines() -> None:
    assert lyric_lines("雨\n[Chorus]\n空\n") == ["雨", "空"]


def test_the_full_exact_match_beats_the_first_excerpt() -> None:
    rows = [
        {"trackName": "Ame", "artistName": "Example", "plainLyrics": "雨\n空", "instrumental": False},
        {
            "trackName": "AME",
            "artistName": "example",
            "plainLyrics": "雨\n空\n海\n風",
            "instrumental": False,
        },
        {
            "trackName": "Something Else",
            "artistName": "Other",
            "plainLyrics": "\n".join(f"行{number}" for number in range(30)),
            "instrumental": False,
        },
        {"trackName": "Ame", "artistName": "Example", "plainLyrics": "長いけど器楽", "instrumental": True},
    ]

    assert lyric_lines(choose_plain(rows, "Ame", "Example") or "") == ["雨", "空", "海", "風"]
