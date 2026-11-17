"""The assertion every error test shares: the body is the one error shape with the expected code."""

from typing import Any

ERROR_SHAPE_KEYS = {"code", "message", "details"}


def assert_error_shape(body: Any, expected_code: str) -> None:
    assert isinstance(body, dict)
    assert set(body) <= ERROR_SHAPE_KEYS
    assert body["code"] == expected_code
    assert isinstance(body["message"], str)
    assert body["message"] != ""
