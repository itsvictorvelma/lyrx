"""Every server setting in one place."""

import os

HOST = "127.0.0.1"
PORT = 8000
ALLOWED_HOST_NAMES = frozenset({"127.0.0.1", "localhost"})

MAX_CHARACTERS = 5000
MAX_LINES = 200
# Above any valid paste: even 5,000 astral characters JSON-escaped as \uXXXX\uXXXX
# (12 bytes each) plus the `{"lyrics":""}` wrapper is 60,013 bytes, under 65,536.
MAX_BODY_BYTES = 64 * 1024

API_KEY_ENV_VAR = "ANTHROPIC_API_KEY"


def read_api_key() -> str | None:
    """The Claude API key, read at call time. An empty value counts as unset."""
    return os.environ.get(API_KEY_ENV_VAR) or None
