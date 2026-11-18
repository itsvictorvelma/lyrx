"""Every server setting in one place."""

import logging
import os

HOST = "127.0.0.1"
PORT = 8000
ALLOWED_HOST_NAMES = frozenset({"127.0.0.1", "localhost"})

# A line longer than this many characters, after cleanup, is split at whitespace and marks.
CLEANUP_SPLIT_LENGTH = 200
# A security cap, not a song limit: a real song is a few kilobytes, so lyrics never reach it.
MAX_BODY_BYTES = 256 * 1024

# The lyrx loggers write at this level; other libraries stay at Python's default (warnings).
LOG_LEVEL = logging.INFO
LOG_FORMAT = "%(levelname)s:     %(name)s %(message)s"

# Sent to LRCLIB with every request: the app name and version only.
USER_AGENT = "Lyrx/0.1.0"

LRCLIB_SEARCH_URL = "https://lrclib.net/api/search"
LRCLIB_RECORD_URL = "https://lrclib.net/api/get/{id}"
LRCLIB_TIMEOUT_SECONDS = 10
# Size caps on LRCLIB replies, enforced while the body streams.
LRCLIB_SEARCH_MAX_BYTES = 2 * 1024 * 1024
LRCLIB_RECORD_MAX_BYTES = 512 * 1024
# The longest search text, in characters, after trimming.
SEARCH_QUERY_MAX_CHARACTERS = 300
# How many LRCLIB search items are read, and how many results are shown.
SEARCH_ITEMS_READ = 50
SEARCH_RESULTS_SHOWN = 10
# Two results with the same names whose durations differ by this much or less are one song.
DUPLICATE_DURATION_SECONDS = 2
# Lyrics look Japanese when at least this fraction of their non-blank lines hold a kana.
LOOKS_JAPANESE_FRACTION = 0.25

GEMINI_API_KEY_ENV_VAR = "GEMINI_API_KEY"
GEMINI_MODEL = "gemini-3.6-flash"
GEMINI_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
)
# Seconds before one Gemini request gives up; it is then retried (see the waits below).
GEMINI_TIMEOUT_SECONDS = 45
# Room for one chunk's three versions (about 1,500 tokens for 15 lines), with a wide margin.
GEMINI_MAX_OUTPUT_TOKENS = 8192
# Minimal thinking: the versions need context, not reasoning, and thinking adds wait time.
GEMINI_THINKING_LEVEL = "MINIMAL"
# A song is cut into chunks of at most this many lines and characters (texts joined by "\n").
# The chunks are sent at the same time, so smaller chunks make a song come back sooner.
GEMINI_CHUNK_LINES = 15
GEMINI_CHUNK_CHARACTERS = 1500
# How many chunk requests run at once; the free tier limits requests per minute.
GEMINI_PARALLEL_REQUESTS = 4
# Each chunk request also carries the whole song as context, unless the song is longer than this.
GEMINI_CONTEXT_MAX_CHARACTERS = 12000
# Seconds to wait before each retry of an overloaded, timed-out, or unusable request.
# Its length is the number of retries. A rate limit (429) or a block is never retried.
GEMINI_RETRY_WAIT_SECONDS = (1.0, 3.0)


def read_gemini_key() -> str | None:
    """The Gemini API key, read at call time. An empty value counts as unset."""
    return os.environ.get(GEMINI_API_KEY_ENV_VAR) or None
