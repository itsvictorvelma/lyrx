"""The accounts table: create, find, check a password, change a password, and delete."""

import sqlite3
import time
from typing import NamedTuple

from lyrx.accounts.passwords import UNKNOWN_USER_HASH, hash_password, password_matches
from lyrx.database import connect


class User(NamedTuple):
    """A signed-in person: the id the other tables use, and the username shown on the page."""

    id: int
    username: str


def create_user(username: str, password: str) -> User | None:
    """The new account, or None when the username is taken.

    The first account created claims the songs saved before accounts existed.
    """
    password_hash = hash_password(password)
    try:
        with connect() as connection:
            cursor = connection.execute(
                "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
                (username, password_hash, time.time()),
            )
            user_id = cursor.lastrowid
            assert user_id is not None
            (users,) = connection.execute("SELECT COUNT(*) FROM users").fetchone()
            if users == 1:
                connection.execute(
                    "UPDATE library_entries SET user_id = ? WHERE user_id IS NULL", (user_id,)
                )
    except sqlite3.IntegrityError:
        return None
    return User(user_id, username)


def user_with_password(username: str, password: str) -> User | None:
    """The account when the password matches; None otherwise.

    An unknown username still runs one scrypt, so the time taken does not tell whether it exists.
    """
    with connect() as connection:
        row = connection.execute(
            "SELECT id, password_hash FROM users WHERE username = ?", (username,)
        ).fetchone()
    if row is None:
        password_matches(password, UNKNOWN_USER_HASH)
        return None
    user_id, stored = row
    return User(user_id, username) if password_matches(password, stored) else None


def username_is_taken(username: str) -> bool:
    with connect() as connection:
        row = connection.execute("SELECT 1 FROM users WHERE username = ?", (username,)).fetchone()
    return row is not None


def set_password(username: str, password: str) -> bool:
    """Changes the password and signs the person out everywhere; False for an unknown name."""
    password_hash = hash_password(password)
    with connect() as connection:
        row = connection.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
        if row is None:
            return False
        connection.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?", (password_hash, row[0])
        )
        connection.execute("DELETE FROM sessions WHERE user_id = ?", (row[0],))
    return True


def delete_user(user_id: int) -> None:
    """Removes the account, its sessions, and its saved songs; cached songs stay."""
    with connect() as connection:
        connection.execute("DELETE FROM library_entries WHERE user_id = ?", (user_id,))
        connection.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
        connection.execute("DELETE FROM users WHERE id = ?", (user_id,))
