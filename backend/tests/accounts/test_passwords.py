"""Tests for password hashing: salted scrypt, and the right password only (spec 014 AC-2)."""

from subbed.accounts.passwords import hash_password, password_matches


def test_ac2_a_hash_is_salted_scrypt_and_only_the_right_password_matches() -> None:
    first = hash_password("correct horse battery")
    second = hash_password("correct horse battery")

    assert first.startswith("scrypt$")
    assert "correct horse battery" not in first
    assert first != second  # A random salt per password.
    assert password_matches("correct horse battery", first)
    assert not password_matches("wrong horse battery", first)


def test_a_stored_value_in_an_unknown_shape_never_matches() -> None:
    for stored in ("", "plain-text", "scrypt$1$2$3$zz$zz", "bcrypt$a$b$c$d$e"):
        assert not password_matches("anything", stored)
