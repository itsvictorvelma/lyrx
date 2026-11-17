# 001 — Tasks

Each task is one test-writer → implementer → reviewer round. Server tests use a fake Claude client; no test calls the network.

- [x] T1 (setup): Scaffold `backend/` (uv, FastAPI, pytest) and `frontend/` (Vite, React, TS, Vitest on jsdom), `.env.example`, `scripts/check.sh`. Both test suites run and pass empty. No AC; the reviewer checks it against the plan.
- [x] T2 (AC-9, 30, 31, 32): App shell: the error shape, Host check, `127.0.0.1` bind, `invalid_request`, `internal_error` with no leak.
- [x] T3 (AC-1, 5, 6, 7, 8, 22, 42, 43, 44): Splitting and limits: line splitting, `empty_input`, `input_too_large` at both limits, `no_japanese`, `server_not_configured`, each with Claude not called.
- [x] T4 (AC-23, 24, 25, 26, 27, 28): Romaji from hiragana.
- [x] T5 (AC-17, 19, plus the unit part of 18; also AC-45, 46, 47): Reading checks: the hiragana-only hard check and the kana-kept comparison.
- [x] T6 (AC-10, 11, 12, 13, 14, 15, 16, 20, 21): The Claude call and reply checks: model and schema, prompt-as-data, refusal, truncation, invalid JSON, bad indexes, empty English, SDK errors.
- [x] T7 (AC-2, 3, 4, 18, 29, 33): Assembling the four versions: the happy path, blank lines, non-Japanese lines, `readingVerified: false`, romaji equals `to_romaji(hiragana)`, nothing sensitive logged.
- [x] T8 (AC-34, 35, 36, 37, 38, 39, 40, 41): The page.
- [ ] Follow-ups from the T2 review:
  - T3: disable `/docs`, `/redoc`, `/openapi.json` (they pull CDN assets); replace the typing-only `assert` in `app.py` with `cast`; comment that Host matching is case-sensitive on purpose. Tests: add an empty-Host case, make the allowed-host test expect 400, import `create_app` and the route path at module top.
  - T7: in `claude.py`, catch `httpx2.RequestError` (the parent of `TransportError` and `DecodingError`) instead of `TransportError`, so a corrupt compressed stream is also `model_unavailable`. Add a test.
  - [x] T4 (tests): rename the body-cap and HTTPException tests to cite AC-44, and the extra-range `has_japanese` test to cite AC-43.
  - T5/T7: normalize the pasted lyrics and Claude's reading to NFC where they enter the pipeline, so decomposed kana (か + U+3099) behaves like が. Test it.
  - T6: reword the `has_allowed_length` docstring to cite `MAX_READING_LENGTH_FACTOR` instead of repeating "6".
  - T7: the pipeline must call `tidy_reading` and then `reading_is_allowed` and fail the whole reply before any `reading_keeps_kana`. Add a test that an over-long reading never reaches the matcher.
  - T7: make the route a sync `def` so FastAPI runs the CPU-bound checks in its threadpool rather than on the event loop.
  - [x] T8: the page's `input_too_large` message uses the AC-45 text.
  - T7: add end-to-end tests that the 502 and 503 bodies hold no exception or reply text. Logging must never walk an exception's `__context__`, since a suppressed pydantic error still holds reply text there.
  - T7: add a test that a client disconnecting mid-body never reaches the app or Claude.
  - T7: add an AC-32 test that raises through the fake Claude client; make sure uvicorn's traceback log on a 500 can't carry lyrics or the reply (AC-33).
- [x] Tests layout: move the tests for `host_check.py`, `body_limit.py`, `crash_guard.py` and `request_log.py` out of `test_app.py` / `test_four_versions.py` into `test_host_check.py`, `test_body_limit.py`, `test_crash_guard.py` and `test_request_log.py` (AGENTS.md: one test file per module). Moves only, no behavior change. The end-to-end AC-33 log tests stay in `test_four_versions.py`; `test_request_log.py` holds direct unit tests of `logged_request`.
- [x] T9 (AC-37, accessibility, from the Impeccable critique; approved by the user): when a result arrives, show a heading above the list ("Four versions" with the line count) and move focus to it, so keyboard and screen-reader users know it worked and focus is not lost when the button disables. The paste box border uses `--color-muted` so it meets the WCAG 3:1 non-text contrast rule (no new color).
- [ ] T9 follow-up (accessibility, same reason as T9): on an error, move focus to the paste box so a keyboard user can fix the text where they left off; focus is otherwise lost when the button disables. Rename the T9 tests to say they are accessibility checks from T9, since no AC lists them.
- [ ] README: folder map, setup (key, both servers), and `scripts/check.sh`.
- [ ] Final review of the whole diff, then the explainer's walkthrough, then the PR.
