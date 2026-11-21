"""Internal results of a translation: built from replies already checked, so never validated."""

from dataclasses import dataclass


@dataclass(frozen=True)
class TokenUsage:
    """The tokens a translator reports for one or more calls."""

    input_tokens: int
    output_tokens: int


@dataclass(frozen=True)
class LineVersions:
    """The three versions a translator made for one line, after every check."""

    hiragana: str
    romaji: str
    english: str


@dataclass(frozen=True)
class TranslatorReply:
    """One translator's reply text, before any check, with its token counts."""

    text: str
    usage: TokenUsage


@dataclass(frozen=True)
class ChunkReply:
    """One reply after its checks: the good lines, the lines to ask again, who answered."""

    lines: dict[int, LineVersions]
    bad_indexes: list[int]
    usage: TokenUsage
    translator: str


@dataclass(frozen=True)
class SongTranslation:
    """The versions for a song by line index, and what it took, for the log.

    `missing_lines` failed the checks even when asked again; they are shown without versions.
    """

    lines: dict[int, LineVersions]
    usage: TokenUsage
    calls: int = 1
    retries: int = 0
    missing_lines: int = 0
    elapsed_ms: int = 0
    # The translators that answered, in chain order.
    translators: tuple[str, ...] = ()
