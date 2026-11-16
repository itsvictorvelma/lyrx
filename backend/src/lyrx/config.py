"""Every server setting in one place."""

import os
from typing import Final

HOST = "127.0.0.1"
PORT = 8000
ALLOWED_HOST_NAMES = frozenset({"127.0.0.1", "localhost"})

MAX_CHARACTERS = 5000
MAX_LINES = 200
MAX_LINE_CHARACTERS = 200
# A reading longer than this many times its original line is refused (AC-46).
MAX_READING_LENGTH_FACTOR = 6
# Above any valid paste: even 5,000 astral characters JSON-escaped as \uXXXX\uXXXX
# (12 bytes each) plus the `{"lyrics":""}` wrapper is 60,013 bytes, under 65,536.
MAX_BODY_BYTES = 64 * 1024

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
