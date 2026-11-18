"""The two long-lived HTTP clients (Gemini and LRCLIB), built once per app with fixed settings.

One client per service is shared by every request and thread, and closed only when the app
stops. Closing a client also closes its connection pool, so it must never be closed per request.
"""

import httpx2

from lyrx import config


def make_gemini_client(transport: httpx2.BaseTransport) -> httpx2.Client:
    """No proxies from the environment; the timeout applies to each step of a request."""
    return httpx2.Client(
        transport=transport, timeout=config.GEMINI_TIMEOUT_SECONDS, trust_env=False
    )


def make_lrclib_client(transport: httpx2.BaseTransport) -> httpx2.Client:
    """No redirects, no proxies, the app's User-Agent, and uncompressed bodies for the caps."""
    return httpx2.Client(
        transport=transport,
        timeout=config.LRCLIB_TIMEOUT_SECONDS,
        follow_redirects=False,
        trust_env=False,
        headers={"User-Agent": config.USER_AGENT, "Accept-Encoding": "identity"},
    )
