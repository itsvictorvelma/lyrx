"""Sessions: a random token in an HttpOnly cookie, and only its SHA-256 hash in the database."""

import hashlib
import secrets
import time

from fastapi import Request, Response

from subbed import config
from subbed.accounts.users import User
from subbed.database import connect
from subbed.errors import ApiError

SESSION_SECONDS = config.SESSION_DAYS * config.DAY_SECONDS


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_session(user_id: int) -> str:
    """A new session's token; expired sessions of anyone are removed at the same time."""
    token = secrets.token_urlsafe(config.SESSION_TOKEN_BYTES)
    now = time.time()
    with connect() as connection:
        connection.execute("DELETE FROM sessions WHERE expires_at <= ?", (now,))
        connection.execute(
            "INSERT INTO sessions (token_hash, user_id, expires_at) VALUES (?, ?, ?)",
            (hash_token(token), user_id, now + SESSION_SECONDS),
        )
    return token


def user_for_token(token: str) -> User | None:
    """The person a token belongs to, or None when it is unknown or expired."""
    with connect() as connection:
        row = connection.execute(
            "SELECT u.id, u.username FROM sessions s JOIN users u ON u.id = s.user_id"
            " WHERE s.token_hash = ? AND s.expires_at > ?",
            (hash_token(token), time.time()),
        ).fetchone()
    return None if row is None else User(*row)


def delete_session(token: str) -> None:
    with connect() as connection:
        connection.execute("DELETE FROM sessions WHERE token_hash = ?", (hash_token(token),))


def session_token(request: Request) -> str | None:
    """The cookie's token, or None when it is missing or too long to be one of ours."""
    token = request.cookies.get(config.SESSION_COOKIE_NAME)
    if not token or len(token) > config.SESSION_TOKEN_MAX_CHARACTERS:
        return None
    return token


def signed_in_user(request: Request) -> User | None:
    """Who sent the request, or None for a guest."""
    token = session_token(request)
    return None if token is None else user_for_token(token)


def require_user(request: Request) -> User:
    """Who sent the request; a guest gets `401 sign_in_required`."""
    user = signed_in_user(request)
    if user is None:
        raise ApiError("sign_in_required")
    return user


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        config.SESSION_COOKIE_NAME,
        token,
        max_age=SESSION_SECONDS,
        path="/",
        httponly=True,
        samesite="lax",
        secure=config.SECURE_COOKIES,
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(
        config.SESSION_COOKIE_NAME,
        path="/",
        httponly=True,
        samesite="lax",
        secure=config.SECURE_COOKIES,
    )
