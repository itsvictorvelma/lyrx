"""Sets a new password for a friend and signs them out everywhere.

Run from `backend/`: `uv run python -m lyrx.accounts.reset_password <username>`.
"""

import getpass
import sys

from pydantic import ValidationError

from lyrx.accounts.users import set_password
from lyrx.schemas import AccountRequest


def main(arguments: list[str]) -> int:
    """Asks for the new password twice; 0 when it was changed, 1 otherwise."""
    if len(arguments) != 1:
        print("Usage: uv run python -m lyrx.accounts.reset_password <username>")
        return 1
    password = getpass.getpass("New password: ")
    if getpass.getpass("Same password again: ") != password:
        print("The passwords differ. Nothing changed.")
        return 1
    try:
        account = AccountRequest(username=arguments[0], password=password)
    except ValidationError:
        print("The username or password does not fit the rules. Nothing changed.")
        return 1
    if not set_password(account.username, account.password):
        print("No account has that username. Nothing changed.")
        return 1
    print("Password changed. That person is signed out everywhere.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
