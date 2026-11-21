"""Password hashing with the standard library's scrypt and a random salt per password."""

import hashlib
import hmac
import secrets

from subbed import config

# A stored hash reads "scrypt$n$r$p$salt$hash" (salt and hash in hex), so a later cost change
# still checks older passwords.
PREFIX = "scrypt"
STORED_PARTS = 6


def hash_password(password: str) -> str:
    n, r, p = config.SCRYPT_COST
    salt = secrets.token_bytes(config.SCRYPT_SALT_BYTES)
    digest = scrypt(password, salt, n, r, p)
    return f"{PREFIX}${n}${r}${p}${salt.hex()}${digest.hex()}"


def password_matches(password: str, stored: str) -> bool:
    """Compares in constant time; a stored value in an unknown shape never matches."""
    parts = stored.split("$")
    if len(parts) != STORED_PARTS or parts[0] != PREFIX:
        return False
    try:
        n, r, p = int(parts[1]), int(parts[2]), int(parts[3])
        salt, expected = bytes.fromhex(parts[4]), bytes.fromhex(parts[5])
    except ValueError:
        return False
    return hmac.compare_digest(scrypt(password, salt, n, r, p), expected)


def scrypt(password: str, salt: bytes, n: int, r: int, p: int) -> bytes:
    return hashlib.scrypt(
        password.encode(),
        salt=salt,
        n=n,
        r=r,
        p=p,
        maxmem=config.SCRYPT_MAX_MEMORY_BYTES,
        dklen=config.SCRYPT_HASH_BYTES,
    )


# Checked against when a username does not exist, so that sign-in takes the same time.
UNKNOWN_USER_HASH = hash_password(secrets.token_urlsafe(16))
