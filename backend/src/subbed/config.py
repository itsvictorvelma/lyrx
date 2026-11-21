"""Every server setting in one place: fixed values, and the few read from the environment."""

import ipaddress
import logging
import os
import re
from pathlib import Path
from typing import Literal, NamedTuple

REPO_ROOT = Path(__file__).resolve().parents[3]


class SettingError(ValueError):
    """A `SUBBED_*` setting has a bad value. It carries only the setting's name, never the value."""


def read_setting(name: str) -> str | None:
    """A setting from the environment, trimmed. An empty value counts as unset."""
    return os.environ.get(name, "").strip() or None


def read_ip_address(name: str) -> str | None:
    """An IP address setting, normalised; a bad value raises SettingError."""
    value = read_setting(name)
    if value is None:
        return None
    try:
        return str(ipaddress.ip_address(value))
    except ValueError:
        raise SettingError(name) from None


def read_host() -> str:
    """The address the server binds to (spec 020). The local default is loopback only."""
    return read_ip_address("SUBBED_HOST") or "127.0.0.1"


# A bare host name or IPv4 address: no scheme, port, path, or space.
HOST_NAME_PATTERN = re.compile(r"^[a-z0-9]([a-z0-9.-]*[a-z0-9])?$")


def read_allowed_hosts() -> frozenset[str]:
    """The host names the Host and Origin checks accept, comma-separated, stored lowercase."""
    value = read_setting("SUBBED_ALLOWED_HOSTS")
    if value is None:
        return frozenset({"127.0.0.1", "localhost"})
    names = [name.strip().lower() for name in value.split(",") if name.strip()]
    if not names or not all(HOST_NAME_PATTERN.fullmatch(name) for name in names):
        raise SettingError("SUBBED_ALLOWED_HOSTS")
    return frozenset(names)


def read_path(name: str) -> Path | None:
    """A path setting; a relative path is taken from the repo root."""
    value = read_setting(name)
    return None if value is None else REPO_ROOT / value


def read_database_path() -> Path:
    return read_path("SUBBED_DATABASE_PATH") or REPO_ROOT / "data" / "subbed.db"


def read_secure_cookies() -> bool:
    """Secure cookies need HTTPS, so they are on only on the server."""
    value = read_setting("SUBBED_SECURE_COOKIES")
    if value is None:
        return False
    if value.lower() not in {"true", "false"}:
        raise SettingError("SUBBED_SECURE_COOKIES")
    return value.lower() == "true"


def read_trusted_proxy() -> str | None:
    """The one address (Caddy) whose `X-Forwarded-For` names the client. Unset: no proxy."""
    return read_ip_address("SUBBED_TRUSTED_PROXY")


def read_page_dir() -> Path | None:
    """The built page folder the server serves (spec 020). Unset locally: Vite serves the page."""
    page_dir = read_path("SUBBED_PAGE_DIR")
    if page_dir is not None and not (page_dir / "index.html").is_file():
        raise SettingError("SUBBED_PAGE_DIR")
    return None if page_dir is None else page_dir.resolve()


# Read once at start. A bad value stops the server with a message that names only the setting.
try:
    HOST = read_host()
    ALLOWED_HOST_NAMES = read_allowed_hosts()
    # Songs, accounts, and counts live in one SQLite file, gitignored (`*.db`); locally in the
    # repo root's `data/` folder.
    DATABASE_PATH = read_database_path()
    SECURE_COOKIES = read_secure_cookies()
    TRUSTED_PROXY = read_trusted_proxy()
    PAGE_DIR = read_page_dir()
except SettingError as error:
    raise SystemExit(f"Subbed cannot start: the setting {error} is not valid.") from None

PORT = 8000
# The built page: hashed asset files never change, so they are cached for a year; index.html
# is checked again on every visit so a new deploy shows at once.
PAGE_ASSETS_PREFIX = "assets/"
PAGE_ASSET_CACHE_CONTROL = "public, max-age=31536000, immutable"
PAGE_INDEX_CACHE_CONTROL = "no-cache"

# A security cap, not a song limit: a real song is a few kilobytes, so lyrics never reach it.
MAX_BODY_BYTES = 256 * 1024

# A YouTube video id: exactly 11 letters, digits, "_" or "-". Only the id is ever kept.
YOUTUBE_VIDEO_ID_PATTERN = r"^[A-Za-z0-9_-]{11}$"
# The sync nudge between the audio and the line timings is limited to this, either way.
PLAYBACK_MAX_OFFSET_MS = 30_000

# The largest song id accepted: SQLite's largest integer. LRCLIB ids are far smaller.
MAX_SONG_ID = 2**63 - 1

# Accounts (spec 014). Usernames are stored lowercase; the pattern also accepts capitals.
USERNAME_PATTERN = r"^[A-Za-z0-9_-]{3,30}$"
PASSWORD_MIN_CHARACTERS = 8
PASSWORD_MAX_CHARACTERS = 128
# scrypt cost: n (a power of two), r, p. About 16 MB of memory and tens of milliseconds per hash.
SCRYPT_COST = (2**14, 8, 1)
SCRYPT_SALT_BYTES = 16
SCRYPT_HASH_BYTES = 32
# Room for the cost above (128 * n * r bytes = 16 MB), with a margin.
SCRYPT_MAX_MEMORY_BYTES = 64 * 1024 * 1024

SESSION_COOKIE_NAME = "subbed_session"
SESSION_TOKEN_BYTES = 32
# A cookie longer than this is not looked up; real tokens are 43 characters.
SESSION_TOKEN_MAX_CHARACTERS = 100
SESSION_DAYS = 30

# Limits per window, in seconds. A day window starts at midnight UTC.
DAY_SECONDS = 24 * 60 * 60
HOUR_SECONDS = 60 * 60
# New (uncached) songs a day: they call LRCLIB and the free translators.
NEW_SONGS_PER_ACCOUNT_PER_DAY = 20
NEW_SONGS_PER_GUEST_IP_PER_DAY = 20
NEW_SONGS_PER_SITE_PER_DAY = 300
SIGN_UPS_PER_IP_PER_DAY = 5
FAILED_SIGN_INS_PER_USERNAME_PER_HOUR = 10

# The subbed loggers write at this level; other libraries stay at Python's default (warnings).
LOG_LEVEL = logging.INFO
LOG_FORMAT = "%(levelname)s:     %(name)s %(message)s"

# Sent to LRCLIB with every request: the app name and version only.
USER_AGENT = "Subbed/0.1.0"

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
# How many recently opened songs the home page row shows (spec 021).
RECENT_SONGS_SHOWN = 12
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
# Seconds one translator request may take in total, however slowly its reply trickles in.
TRANSLATOR_DEADLINE_SECONDS = 45

GEMINI_API_KEY_ENV_VAR = "GEMINI_API_KEY"
GEMINI_URL_TEMPLATE = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
)
# Seconds before one Gemini request gives up; it then moves on or is retried (waits below).
GEMINI_TIMEOUT_SECONDS = 45
# Room for one chunk's three versions (about 4,000 tokens for 40 lines), with a wide margin.
GEMINI_MAX_OUTPUT_TOKENS = 8192
# A reply larger than this is refused while it streams in; real replies are far smaller.
GEMINI_MAX_REPLY_BYTES = 512 * 1024
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


def read_api_key(env_var: str) -> str | None:
    """An API key from the environment, read at call time. An empty value counts as unset."""
    return os.environ.get(env_var, "").strip() or None
