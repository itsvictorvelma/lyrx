"""Counts kept in the database, per window: daily caps on new songs, sign-ups, failed sign-ins."""

import sqlite3
import time
from typing import NamedTuple

from fastapi import Request

from lyrx import config
from lyrx.database import connect

# Count rows older than this are removed when anything is counted.
KEEP_COUNTS_SECONDS = 2 * config.DAY_SECONDS


class Limit(NamedTuple):
    """At most `most` of `kind` by `who` in each window of `window_seconds`."""

    kind: str
    who: str
    most: int
    window_seconds: int


def peer_address(request: Request) -> str:
    """The client's IP address: the direct peer, or the client Caddy names when uvicorn trusts
    it as the proxy (`LYRX_TRUSTED_PROXY`, spec 020)."""
    return request.client.host if request.client is not None else "unknown"


def new_song_limits(user_id: int | None, guest_ip: str) -> list[Limit]:
    """The daily caps a new (uncached) song counts toward: the person's, then the site's."""
    day = config.DAY_SECONDS
    if user_id is not None:
        person = Limit("new_song_account", str(user_id), config.NEW_SONGS_PER_ACCOUNT_PER_DAY, day)
    else:
        person = Limit("new_song_ip", guest_ip, config.NEW_SONGS_PER_GUEST_IP_PER_DAY, day)
    site = Limit("new_song_site", "site", config.NEW_SONGS_PER_SITE_PER_DAY, day)
    return [person, site]


def sign_up_limit(ip: str) -> Limit:
    return Limit("sign_up", ip, config.SIGN_UPS_PER_IP_PER_DAY, config.DAY_SECONDS)


def failed_sign_in_limit(username: str) -> Limit:
    return Limit(
        "failed_sign_in",
        username,
        config.FAILED_SIGN_INS_PER_USERNAME_PER_HOUR,
        config.HOUR_SECONDS,
    )


def window_start(window_seconds: int) -> int:
    """The start of the current window; windows line up with midnight UTC."""
    now = int(time.time())
    return now - now % window_seconds


def count_if_allowed(*limits: Limit) -> bool:
    """Counts one more toward every limit, or toward none when any is already reached."""
    with connect() as connection:
        for limit in limits:
            if add_one(connection, limit) > limit.most:
                connection.rollback()
                return False
        remove_old_counts(connection)
        return True


def uncount(limit: Limit) -> None:
    """Gives back one counted with `count_if_allowed`, such as a sign-in that turned out right."""
    with connect() as connection:
        connection.execute(
            "UPDATE request_counts SET count = count - 1"
            " WHERE kind = ? AND who = ? AND window_start = ? AND count > 0",
            (limit.kind, limit.who, window_start(limit.window_seconds)),
        )


def add_one(connection: sqlite3.Connection, limit: Limit) -> int:
    """Adds one to the current window's count and returns the new count.

    One statement, so two requests at the same moment cannot both read the old count.
    """
    row = connection.execute(
        "INSERT INTO request_counts (kind, who, window_start, count) VALUES (?, ?, ?, 1)"
        " ON CONFLICT (kind, who, window_start) DO UPDATE SET count = count + 1"
        " RETURNING count",
        (limit.kind, limit.who, window_start(limit.window_seconds)),
    ).fetchone()
    new_count: int = row[0]
    return new_count


def remove_old_counts(connection: sqlite3.Connection) -> None:
    connection.execute(
        "DELETE FROM request_counts WHERE window_start < ?", (time.time() - KEEP_COUNTS_SECONDS,)
    )
