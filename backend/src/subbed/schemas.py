"""What the page sends and receives: request bodies, replies, and the error shape."""

from pydantic import BaseModel, ConfigDict, Field, field_validator

from subbed.config import (
    MAX_SONG_ID,
    PASSWORD_MAX_CHARACTERS,
    PASSWORD_MIN_CHARACTERS,
    PLAYBACK_MAX_OFFSET_MS,
    USERNAME_PATTERN,
    YOUTUBE_VIDEO_ID_PATTERN,
)


class SongSearchRequest(BaseModel):
    """The body of `POST /api/song-search`."""

    model_config = ConfigDict(strict=True)

    query: str


class SongVersionsRequest(BaseModel):
    """The body of `POST /api/song-versions`. Strict, so `true`, `1.5`, and `"1"` are refused."""

    model_config = ConfigDict(strict=True)

    id: int = Field(ge=1, le=MAX_SONG_ID)


class VersionLine(BaseModel):
    """One line of a song in its four versions, and when it starts (None when unknown)."""

    index: int
    original: str
    hiragana: str
    romaji: str
    english: str
    start_ms: int | None = Field(default=None, ge=0, serialization_alias="startMs")


class Playback(BaseModel):
    """A saved song's YouTube video and its sync nudge; also the body of the playback PUT."""

    model_config = ConfigDict(strict=True, extra="forbid")

    video_id: str | None = Field(default=None, alias="videoId", pattern=YOUTUBE_VIDEO_ID_PATTERN)
    offset_ms: int = Field(
        default=0, alias="offsetMs", ge=-PLAYBACK_MAX_OFFSET_MS, le=PLAYBACK_MAX_OFFSET_MS
    )


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


class SavedSong(Song):
    """A saved song in the library list: its video and sync, and when it was last opened."""

    video_id: str | None = Field(serialization_alias="videoId")
    # Listed so Undo after Remove can save the song again with its sync (spec 025).
    offset_ms: int = Field(serialization_alias="offsetMs")
    last_opened_at: int = Field(serialization_alias="lastOpenedAt")


class SavedSongsResponse(BaseModel):
    """The body of `GET /api/songs`: the saved songs, most recently opened first."""

    songs: list[SavedSong]


class RecentSong(Song):
    """A recently opened cached song for the home page row: its saved video, if any."""

    video_id: str | None = Field(serialization_alias="videoId")


class RecentSongsResponse(BaseModel):
    """The body of `GET /api/recent-songs`: cached songs, most recently opened first."""

    songs: list[RecentSong]


class SongVersionsResponse(BaseModel):
    """The body of a successful `POST /api/song-versions`; `fromLibrary` when it was saved."""

    song: Song
    lines: list[VersionLine]
    # True when the reply came from the server's cache instead of a new translation.
    from_library: bool = Field(default=False, serialization_alias="fromLibrary")
    playback: Playback = Playback()
    # Whether the song is in the learner's library.
    saved: bool = False


class AccountRequest(BaseModel):
    """The body of sign-up and sign-in. The username is stored and compared in lowercase."""

    model_config = ConfigDict(strict=True, extra="forbid")

    username: str = Field(pattern=USERNAME_PATTERN)
    password: str = Field(min_length=PASSWORD_MIN_CHARACTERS, max_length=PASSWORD_MAX_CHARACTERS)

    @field_validator("username")
    @classmethod
    def to_lowercase(cls, username: str) -> str:
        return username.lower()


class PasswordRequest(BaseModel):
    """The body of `DELETE /api/account`: the password, asked again."""

    model_config = ConfigDict(strict=True, extra="forbid")

    password: str = Field(min_length=1, max_length=PASSWORD_MAX_CHARACTERS)


class AccountResponse(BaseModel):
    """Who is signed in: the username, or None for a guest."""

    username: str | None


class ErrorResponse(BaseModel):
    """The one error shape every failed request returns."""

    code: str
    message: str
