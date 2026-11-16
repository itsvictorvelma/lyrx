"""Checks that the lyrx package imports, so the test suite has something to run."""

import lyrx


def test_package_imports() -> None:
    assert lyrx.__doc__ is not None
