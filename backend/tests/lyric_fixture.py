"""One canned LRCLIB lyric for the default tests.

This is not a screen. The app does not list it, and the tests do not call
LRCLIB or Groq.
"""

from app.generation.lrclib import Recording

AME = Recording(title="Ame", artist="Example", text="雨\n[Chorus]\n空")


def search_ame(title: str, artist: str) -> Recording | None:
    if title.strip().casefold() != "ame":
        return None
    return AME
