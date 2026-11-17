"""Every server setting in one place."""

import logging
import os
from typing import Final

HOST = "127.0.0.1"
PORT = 8000
ALLOWED_HOST_NAMES = frozenset({"127.0.0.1", "localhost"})

# A line longer than this many characters, after cleanup, is split at whitespace and marks.
CLEANUP_SPLIT_LENGTH = 200
# A reading longer than this many times its original line is refused (AC-46).
MAX_READING_LENGTH_FACTOR = 6
# A security cap, not a song limit: a real song is a few kilobytes, so lyrics never reach it.
MAX_BODY_BYTES = 256 * 1024

# The lyrx loggers write at this level; other libraries stay at Python's default (warnings).
LOG_LEVEL = logging.INFO
LOG_FORMAT = "%(levelname)s:     %(name)s %(message)s"

API_KEY_ENV_VAR = "ANTHROPIC_API_KEY"

MODEL = "claude-opus-5-5"
# The model's default effort, set explicitly. `Final` keeps its Literal type, which the
# SDK's OutputConfigParam requires.
EFFORT: Final = "medium"
# Room for a reply to a paste at the size limit.
MAX_TOKENS = 32000
# Seconds before a Claude request gives up; the call then fails with model_unavailable.
REQUEST_TIMEOUT_SECONDS = 120


def read_api_key() -> str | None:
    """The Claude API key, read at call time. An empty value counts as unset."""
    return os.environ.get(API_KEY_ENV_VAR) or None
