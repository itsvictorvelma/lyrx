"""What the page sends and receives: request bodies, replies, and the error shape."""

from pydantic import BaseModel, ConfigDict, Field

from lyrx.config import MAX_SONG_ID


class SongSearchRequest(BaseModel):
    """The body of `POST /api/song-search`."""

    model_config = ConfigDict(strict=True)

    query: str


class SongVersionsRequest(BaseModel):
    """The body of `POST /api/song-versions`. Strict, so `true`, `1.5`, and `"1"` are refused."""

    model_config = ConfigDict(strict=True)

    id: int = Field(ge=1, le=MAX_SONG_ID)


class VersionLine(BaseModel):
    """One line of a song in its four versions."""

    index: int
    original: str
    hiragana: str
    romaji: str
    english: str


class Song(BaseModel):
    """Which LRCLIB song a result or a reply is about."""

    id: int
    track: str
    artist: str
    album: str
    duration_seconds: int = Field(serialization_alias="durationSeconds")


class SearchResult(Song):
    """One search result: the song, whether its lyrics look Japanese, and whether it is saved."""

    looks_japanese: bool = Field(serialization_alias="looksJapanese")
    saved: bool = False


class SongSearchResponse(BaseModel):
    """The body of a successful `POST /api/song-search`, best first."""

    results: list[SearchResult]


class SavedSongsResponse(BaseModel):
    """The body of `GET /api/songs`: the saved songs, most recently opened first."""

    songs: list[Song]


class SongVersionsResponse(BaseModel):
    """The body of a successful `POST /api/song-versions`; `fromLibrary` when it was saved."""

    song: Song
    lines: list[VersionLine]
    from_library: bool = Field(default=False, serialization_alias="fromLibrary")


class ErrorResponse(BaseModel):
    """The one error shape every failed request returns."""

    code: str
    message: str
