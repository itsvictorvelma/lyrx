"""Every server setting in one place."""

import logging
import os
from pathlib import Path
from typing import Literal, NamedTuple

HOST = "127.0.0.1"
PORT = 8000
ALLOWED_HOST_NAMES = frozenset({"127.0.0.1", "localhost"})

# A line longer than this many characters, after cleanup, is split at whitespace and marks.
CLEANUP_SPLIT_LENGTH = 200
# A security cap, not a song limit: a real song is a few kilobytes, so lyrics never reach it.
MAX_BODY_BYTES = 256 * 1024

# The largest song id accepted: SQLite's largest integer. LRCLIB ids are far smaller.
MAX_SONG_ID = 2**63 - 1

# Saved songs live in one SQLite file, gitignored (`*.db`), at the repo root's `data/` folder.
REPO_ROOT = Path(__file__).resolve().parents[3]
DATABASE_PATH = REPO_ROOT / "data" / "lyrx.db"

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


class Translator(NamedTuple):
    """One translator in the chain: its name in the log, its service, and the model asked."""

    name: str
    service: Literal["groq", "gemini"]
    model: str


# Tried in this order for every request (spec 010). When one is busy (429, 503, a timeout, or
# no connection) the same request goes to the next. Each model has its own free limits and
# load. Groq is first: in a test it was faster and as accurate; Gemini is the backup.
TRANSLATORS = (
    Translator("groq-gpt-oss-120b", "groq", "openai/gpt-oss-120b"),
    Translator("gemini-3.5-flash-lite", "gemini", "gemini-3.5-flash-lite"),
    Translator("gemini-3.1-flash-lite", "gemini", "gemini-3.1-flash-lite"),
)

GROQ_API_KEY_ENV_VAR = "GROQ_API_KEY"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_TIMEOUT_SECONDS = 45
# Room for one chunk's three versions plus the model's short reasoning, with a margin.
GROQ_MAX_OUTPUT_TOKENS = 8192
# A reply larger than this is refused while it streams in; real replies are far smaller.
GROQ_MAX_REPLY_BYTES = 512 * 1024

GEMINI_API_KEY_ENV_VAR = "GEMINI_API_KEY"
GEMINI_URL_TEMPLATE = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
)
# Seconds before one Gemini request gives up; it then moves on or is retried (waits below).
GEMINI_TIMEOUT_SECONDS = 45
# Room for one chunk's three versions (about 4,000 tokens for 40 lines), with a wide margin.
GEMINI_MAX_OUTPUT_TOKENS = 8192
# Minimal thinking: the versions need context, not reasoning, and thinking adds wait time.
GEMINI_THINKING_LEVEL = "MINIMAL"
# A song is cut into chunks of at most this many lines and characters (texts joined by "\n").
# The chunks are sent at the same time. Smaller chunks come back sooner but cost more of the
# free tier's per-minute and per-day request limits; 40 lines keeps most songs to 1 or 2 calls.
CHUNK_LINES = 40
CHUNK_CHARACTERS = 4000
# How many chunk requests run at once; the free tier limits requests per minute.
PARALLEL_REQUESTS = 4
# Each chunk request also carries the whole song as context, unless the song is longer than this.
CONTEXT_MAX_CHARACTERS = 12000
# Seconds to wait before each retry of an overloaded, timed-out, or unusable request.
# Its length is the number of retries. A rate limit (429) or a block is never retried.
RETRY_WAIT_SECONDS = (1.0, 3.0)


def read_gemini_key() -> str | None:
    """The Gemini API key, read at call time. An empty value counts as unset."""
    return os.environ.get(GEMINI_API_KEY_ENV_VAR, "").strip() or None


def read_groq_key() -> str | None:
    """The Groq API key, read at call time. An empty value counts as unset."""
    return os.environ.get(GROQ_API_KEY_ENV_VAR, "").strip() or None
