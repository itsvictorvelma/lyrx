"""Data shapes: request bodies, responses, the LRCLIB record, and the Gemini reply."""

from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field


class VersionsRequest(BaseModel):
    """The body of `POST /api/versions`. A non-string `lyrics` is rejected, not coerced."""

    model_config = ConfigDict(strict=True)

    lyrics: str


class SongSearchRequest(BaseModel):
    """The body of `POST /api/song-search`."""

    model_config = ConfigDict(strict=True)

    query: str


class SongVersionsRequest(BaseModel):
    """The body of `POST /api/song-versions`. Strict, so `true`, `1.5`, and `"1"` are refused."""

    model_config = ConfigDict(strict=True)

    id: int = Field(ge=1)


class VersionLine(BaseModel):
    """One line of a song in its four versions."""

    index: int
    original: str
    hiragana: str
    romaji: str
    english: str


class VersionsResponse(BaseModel):
    """The body of a successful `POST /api/versions`: every line, in order."""

    lines: list[VersionLine]


class Song(BaseModel):
    """Which LRCLIB song a result or a reply is about."""

    id: int
    track: str
    artist: str
    album: str
    duration_seconds: int = Field(serialization_alias="durationSeconds")


class SearchResult(Song):
    """One search result: the song, and whether its lyrics look Japanese."""

    looks_japanese: bool = Field(serialization_alias="looksJapanese")


class SongSearchResponse(BaseModel):
    """The body of a successful `POST /api/song-search`, best first."""

    results: list[SearchResult]


class SongVersionsResponse(BaseModel):
    """The body of a successful `POST /api/song-versions`."""

    song: Song
    lines: list[VersionLine]


class ErrorResponse(BaseModel):
    """The one error shape every failed request returns."""

    code: str
    message: str


class LrclibRecord(BaseModel):
    """One LRCLIB record, from search or by id. Fields Lyrx does not read are ignored."""

    id: int = Field(strict=True, ge=1)
    track_name: str = Field(alias="trackName", strict=True)
    artist_name: str = Field(alias="artistName", strict=True)
    album_name: str | None = Field(default=None, alias="albumName", strict=True)
    duration: float = Field(default=0, ge=0, strict=True, allow_inf_nan=False)
    instrumental: bool = Field(default=False, strict=True)
    plain_lyrics: str | None = Field(default=None, alias="plainLyrics", strict=True)


class GeminiPart(BaseModel):
    """One part of a Gemini candidate's content. A part may hold no text."""

    model_config = ConfigDict(strict=True)

    text: str = ""


class GeminiContent(BaseModel):
    """A Gemini candidate's content: its parts, in order."""

    model_config = ConfigDict(strict=True)

    parts: list[GeminiPart] = []


class GeminiCandidate(BaseModel):
    """One Gemini candidate. A blocked or empty candidate may have no content."""

    model_config = ConfigDict(strict=True)

    content: GeminiContent | None = None
    finish_reason: str | None = Field(default=None, alias="finishReason")


class GeminiPromptFeedback(BaseModel):
    """Gemini's verdict on the prompt; a block reason means the prompt was blocked."""

    model_config = ConfigDict(strict=True)

    block_reason: str | None = Field(default=None, alias="blockReason")


class GeminiUsage(BaseModel):
    """The token counts Gemini reports. A missing count is zero."""

    model_config = ConfigDict(strict=True)

    prompt_token_count: int = Field(default=0, alias="promptTokenCount")
    candidates_token_count: int = Field(default=0, alias="candidatesTokenCount")


class GeminiEnvelope(BaseModel):
    """The `generateContent` reply around the text. Fields Lyrx does not read are ignored."""

    model_config = ConfigDict(strict=True)

    candidates: list[GeminiCandidate] = []
    prompt_feedback: GeminiPromptFeedback | None = Field(default=None, alias="promptFeedback")
    usage_metadata: GeminiUsage | None = Field(default=None, alias="usageMetadata")


class GeminiLine(BaseModel):
    """One line of Gemini's reply. Strict: no coercion and no extra fields."""

    model_config = ConfigDict(strict=True, extra="forbid")

    index: int
    hiragana: str
    romaji: str
    english: str


# The shapes below are internal: the server builds them from text it has already checked,
# so they are plain frozen dataclasses, never validated, unlike the Pydantic shapes above.


@dataclass(frozen=True)
class TokenUsage:
    """The tokens Gemini reports for one or more calls."""

    input_tokens: int
    output_tokens: int


@dataclass(frozen=True)
class LineVersions:
    """The three versions Gemini made for one line, after every check."""

    hiragana: str
    romaji: str
    english: str


@dataclass(frozen=True)
class ChunkReply:
    """One Gemini reply after its checks: the good lines, and the lines to ask again."""

    lines: dict[int, LineVersions]
    bad_indexes: list[int]
    usage: TokenUsage


@dataclass(frozen=True)
class GeminiVersions:
    """Gemini's versions for a song by line index, and what it took, for the log.

    `missing_lines` failed the checks even when asked again; they are shown without versions.
    """

    lines: dict[int, LineVersions]
    usage: TokenUsage
    calls: int = 1
    retries: int = 0
    missing_lines: int = 0
    elapsed_ms: int = 0
