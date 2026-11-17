"""Invented lyrics pages and their expected candidate lines, for the link tests. No real lyrics."""

# Japanese pages use full-width punctuation (colon, exclamation mark), so it is kept.
# ruff: noqa: RUF001

# AC-38: each Japanese line is followed by a Hangul pronunciation line and a Korean translation.
INTERLEAVED_PAGE = """<!doctype html>
<html><head><title>星の歌</title></head>
<body>
<div class="lyric">
君の声が<br>
키미노 코에가<br>
너의 목소리가<br>
遠く ひびく<br>
토오쿠 히비쿠<br>
멀리 울려<br>
</div>
</body></html>
"""
INTERLEAVED_CANDIDATES = ["君の声が", "遠く ひびく"]

# AC-48: a song page with a title, credits, the lyrics, a comment, and a menu word. The nav,
# footer, script, and Latin-only lines are not candidates, so the candidates are exactly
# SONG_PAGE_CANDIDATES, and the lyrics are candidates 2, 3 and 4.
SONG_PAGE = """<!doctype html>
<html lang="ja">
<head><meta charset="utf-8"><title>星の歌 - 歌詞</title></head>
<body>
<nav><a href="/">トップ</a> | <a href="/new">新着</a></nav>
<h1>星の歌 / ミナト</h1>
<p class="credits">作詞・作曲：ミナト</p>
<div class="lyrics">
君の声が<br>
遠く ひびく<br>
星が ながれる<br>
</div>
<p>Your voice echoes far away</p>
<div class="comment">この曲大好き！</div>
<div class="menu">ホーム</div>
<script>var title = "隠れた歌";</script>
<footer>利用規約</footer>
</body></html>
"""
SONG_PAGE_CANDIDATES = [
    "星の歌 / ミナト",
    "作詞・作曲：ミナト",
    "君の声が",
    "遠く ひびく",
    "星が ながれる",
    "この曲大好き！",
    "ホーム",
]
SONG_PAGE_LYRIC_LINES = [2, 3, 4]
SONG_PAGE_LYRICS = "君の声が\n遠く ひびく\n星が ながれる"

# AC-33: a page whose bytes are Shift_JIS. One copy names the charset only in a <meta> tag near
# the top; the other names none, so the charset must come from the Content-Type header.
SHIFT_JIS_LINES = ["君の声が", "遠く ひびく"]
SHIFT_JIS_PAGE_WITH_META = (
    '<html><head><meta charset="Shift_JIS"></head>'
    "<body><p>君の声が</p><p>遠く ひびく</p></body></html>"
).encode("shift_jis")
SHIFT_JIS_PAGE = "<html><body><p>君の声が</p><p>遠く ひびく</p></body></html>".encode("shift_jis")


def html_page(*lines: str) -> str:
    """A plain HTML page with each line in its own paragraph."""
    paragraphs = "".join(f"<p>{line}</p>\n" for line in lines)
    return f"<!doctype html>\n<html><body>\n{paragraphs}</body></html>\n"
