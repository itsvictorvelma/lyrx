"""Invented Japanese pastes of an exact size, for the size-limit tests. No real lyrics."""

LIMIT_DETAILS = {"maxCharacters": 5000, "maxLines": 200, "maxLineCharacters": 200}
LIMIT_MESSAGE = (
    "The lyrics are too long. The limit is 5,000 characters, 200 lines,"
    " and 200 characters per line."
)
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
