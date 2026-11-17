"""Invented Japanese pastes of an exact size, for the size-limit tests. No real lyrics."""

# The AC-45 details and message: still what the 64 KB body cap returns (AC-44, AC-48 decision).
LIMIT_DETAILS = {"maxCharacters": 5000, "maxLines": 200, "maxLineCharacters": 200}
LIMIT_MESSAGE = (
    "The lyrics are too long. The limit is 5,000 characters, 200 lines,"
    " and 200 characters per line."
)
# Every key an AC-48 size refusal may put in `details`.
LIMIT_DETAIL_KEYS = {*LIMIT_DETAILS, "limitHit", "measured", "lineNumber"}


def limit_details(
    limit_hit: str, measured: int, line_number: int | None = None
) -> dict[str, object]:
    """The AC-48 `details` of a paste refused by the size limits: the limits and what was hit."""
    details: dict[str, object] = {**LIMIT_DETAILS, "limitHit": limit_hit, "measured": measured}
    if line_number is not None:
        details["lineNumber"] = line_number
    return details


FILLER = "ほしのよるに"
FILLER_LINE_LENGTH = 49
FILLER_LINE_COUNT = 99


def japanese_line(length: int) -> str:
    """A line of invented kana exactly `length` characters long."""
    return (FILLER * (length // len(FILLER) + 1))[:length]


def paste_of_characters(total_characters: int, line_ending: str = "\n") -> str:
    """100 Japanese lines that are `total_characters` long once every line ending is one `\\n`."""
    first_line_length = total_characters - FILLER_LINE_COUNT * (FILLER_LINE_LENGTH + 1)
    lines = [japanese_line(first_line_length)]
    lines += [japanese_line(FILLER_LINE_LENGTH)] * FILLER_LINE_COUNT
    return line_ending.join(lines)


def paste_of_lines(line_count: int, line_ending: str = "\n") -> str:
    """`line_count` short, non-blank Japanese lines."""
    return line_ending.join(f"そらのうた{index}" for index in range(line_count))
