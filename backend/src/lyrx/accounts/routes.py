"""The account routes: who is signed in, sign up, sign in, sign out, and delete the account."""

from http import HTTPStatus

from fastapi import FastAPI, Request, Response

from lyrx.accounts.sessions import (
    clear_session_cookie,
    create_session,
    delete_session,
    require_user,
    session_token,
    set_session_cookie,
    signed_in_user,
)
from lyrx.accounts.users import (
    User,
    create_user,
    delete_user,
    user_with_password,
    username_is_taken,
)
from lyrx.errors import ApiError
from lyrx.rate_limits import (
    count_if_allowed,
    failed_sign_in_limit,
    peer_address,
    sign_up_limit,
    uncount,
)
from lyrx.schemas import AccountRequest, AccountResponse, PasswordRequest
from lyrx.server.request_log import logged_request

ACCOUNT_PATH = "/api/account"
SIGN_UP_PATH = "/api/account/sign-up"
SIGN_IN_PATH = "/api/account/sign-in"
SIGN_OUT_PATH = "/api/account/sign-out"


def get_account(request: Request) -> AccountResponse:
    """Who is signed in; a guest gets a null username, not an error."""
    with logged_request(ACCOUNT_PATH):
        user = signed_in_user(request)
        return AccountResponse(username=None if user is None else user.username)


def sign_up(body: AccountRequest, request: Request, response: Response) -> AccountResponse:
    """Creates the account and signs it in."""
    with logged_request(SIGN_UP_PATH) as log:
        # Every attempt counts, so the limit also caps checking which usernames exist.
        if not count_if_allowed(sign_up_limit(peer_address(request))):
            raise ApiError("too_many_attempts")
        if username_is_taken(body.username):
            raise ApiError("username_taken")
        user = create_user(body.username, body.password)
        if user is None:  # Taken between the check above and now.
            raise ApiError("username_taken")
        set_session_cookie(response, create_session(user.id))
        log.add("event", "signed_up")
        log.add("user_id", user.id)
        return AccountResponse(username=user.username)


def sign_in(body: AccountRequest, request: Request, response: Response) -> AccountResponse:
    """Signs in; after too many failures for one username, even the right password waits."""
    with logged_request(SIGN_IN_PATH) as log:
        user = check_password(body.username, body.password)
        set_session_cookie(response, create_session(user.id))
        log.add("event", "signed_in")
        log.add("user_id", user.id)
        return AccountResponse(username=user.username)


def sign_out(request: Request) -> Response:
    """Ends this browser's session; signing out twice is fine."""
    with logged_request(SIGN_OUT_PATH):
        token = session_token(request)
        if token is not None:
            delete_session(token)
        response = Response(status_code=HTTPStatus.NO_CONTENT)
        clear_session_cookie(response)
        return response


def delete_account(body: PasswordRequest, request: Request) -> Response:
    """Deletes the account, its sessions, and its saved songs, after the password again."""
    with logged_request(ACCOUNT_PATH) as log:
        user = require_user(request)
        check_password(user.username, body.password)
        delete_user(user.id)
        log.add("event", "account_deleted")
        log.add("user_id", user.id)
        response = Response(status_code=HTTPStatus.NO_CONTENT)
        clear_session_cookie(response)
        return response


def check_password(username: str, password: str) -> User:
    """The account when the password is right; each failure counts toward the hourly limit.

    The attempt is counted before the check and given back when it is right, so requests sent
    at the same moment cannot all slip under the limit.
    """
    limit = failed_sign_in_limit(username)
    if not count_if_allowed(limit):
        raise ApiError("too_many_attempts")
    user = user_with_password(username, password)
    if user is None:
        raise ApiError("sign_in_failed")
    uncount(limit)
    return user


def add_account_routes(app: FastAPI) -> None:
    app.add_api_route(ACCOUNT_PATH, get_account, methods=["GET"])
    app.add_api_route(ACCOUNT_PATH, delete_account, methods=["DELETE"])
    app.add_api_route(SIGN_UP_PATH, sign_up, methods=["POST"])
    app.add_api_route(SIGN_IN_PATH, sign_in, methods=["POST"])
    app.add_api_route(SIGN_OUT_PATH, sign_out, methods=["POST"])
