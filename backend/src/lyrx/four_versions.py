"""The pipeline for one paste: split, check limits, check for Japanese, check the key, then call."""

from lyrx import config
from lyrx.errors import ApiError
from lyrx.lines import check_limits, has_japanese, split_lines


def make_four_versions(lyrics: str, claude_client: object | None) -> None:
    """Every refusal happens before `claude_client` is touched."""
    lines = split_lines(lyrics)
    check_limits(lyrics, lines)
    if not any(has_japanese(line) for line in lines):
        raise ApiError("no_japanese")
    if config.read_api_key() is None:
        raise ApiError("server_not_configured")
    # ponytail: no Claude call yet, so a paste that passes every check is an internal_error;
    # T6-T7 add the call and the four versions.
    raise ApiError("internal_error")
