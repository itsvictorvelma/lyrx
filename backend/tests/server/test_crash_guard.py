"""Tests for the crash guard: no exception escapes the app to uvicorn's traceback log."""

import json
import logging

import pytest
from error_shape import assert_error_shape
from fastapi import FastAPI
from raw_asgi import (
    ALLOWED_HOST_HEADER,
    UVICORN_ERROR_LOGGER,
    body_messages,
    response_body,
    response_status,
    run_like_uvicorn,
)

CRASH_GUARD_LOGGER = "subbed.server.crash_guard"
CRASH_PATH = "/api/raise-outside-the-pipeline"
CRASH_SECRETS = [
    "/Users/someone/subbed/src/subbed/app.py",
    "君の声が 遠く ひびく",
    "test-key-not-real",
]


def test_ac32_crash_guard_stops_an_exception_raised_outside_the_pipeline(
    app: FastAPI, caplog: pytest.LogCaptureFixture
) -> None:
    """A 500 in the error shape, no uvicorn traceback, one crash line with just the class name."""
    caplog.set_level(logging.DEBUG)

    def raise_outside_the_pipeline() -> None:
        raise RuntimeError(" ".join(CRASH_SECRETS))

    app.add_api_route(CRASH_PATH, raise_outside_the_pipeline, methods=["POST"])

    sent = run_like_uvicorn(app, [ALLOWED_HOST_HEADER], body_messages([b""]), path=CRASH_PATH)

    assert response_status(sent) == 500
    body = response_body(sent).decode()
    assert_error_shape(json.loads(body), "internal_error")
    assert [record for record in caplog.records if record.name == UVICORN_ERROR_LOGGER] == []
    crash_records = [record for record in caplog.records if record.name == CRASH_GUARD_LOGGER]
    assert len(crash_records) == 1
    assert "RuntimeError" in crash_records[0].getMessage()
    crash_text = logging.Formatter().format(crash_records[0]) + repr(crash_records[0].__dict__)
    for secret in CRASH_SECRETS:
        assert secret not in crash_text
        assert secret not in body
