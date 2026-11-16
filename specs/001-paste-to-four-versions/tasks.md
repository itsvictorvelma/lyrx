# 001 — Tasks

Each task is one test-writer → implementer → reviewer round. Server tests use a fake Claude client; no test calls the network.

- [x] T1 (setup): Scaffold `backend/` (uv, FastAPI, pytest) and `frontend/` (Vite, React, TS, Vitest on jsdom), `.env.example`, `scripts/check.sh`. Both test suites run and pass empty. No AC; the reviewer checks it against the plan.
- [x] T2 (AC-9, 30, 31, 32): App shell: the error shape, Host check, `127.0.0.1` bind, `invalid_request`, `internal_error` with no leak.
- [x] T3 (AC-1, 5, 6, 7, 8, 22, 42, 43, 44): Splitting and limits: line splitting, `empty_input`, `input_too_large` at both limits, `no_japanese`, `server_not_configured`, each with Claude not called.
- [x] T4 (AC-23, 24, 25, 26, 27, 28): Romaji from hiragana.
- [ ] T5 (AC-17, 19, plus the unit part of 18): Reading checks: the hiragana-only hard check and the kana-kept comparison.
- [ ] T6 (AC-10, 11, 12, 13, 14, 15, 16, 20, 21): The Claude call and reply checks: model and schema, prompt-as-data, refusal, truncation, invalid JSON, bad indexes, empty English, SDK errors.
- [ ] T7 (AC-2, 3, 4, 18, 29, 33): Assembling the four versions: the happy path, blank lines, non-Japanese lines, `readingVerified: false`, romaji equals `to_romaji(hiragana)`, nothing sensitive logged.
- [ ] T8 (AC-34, 35, 36, 37, 38, 39, 40, 41): The page.
- [ ] Follow-ups from the T2 review:
  - T3: disable `/docs`, `/redoc`, `/openapi.json` (they pull CDN assets); replace the typing-only `assert` in `app.py` with `cast`; comment that Host matching is case-sensitive on purpose. Tests: add an empty-Host case, make the allowed-host test expect 400, import `create_app` and the route path at module top.
  - [x] T4 (tests): rename the body-cap and HTTPException tests to cite AC-44, and the extra-range `has_japanese` test to cite AC-43.
  - T5/T7: normalize the pasted lyrics and Claude's reading to NFC where they enter the pipeline, so decomposed kana (か + U+3099) behaves like が. Test it.
  - T7: add a test that a client disconnecting mid-body never reaches the app or Claude.
  - T7: add an AC-32 test that raises through the fake Claude client; make sure uvicorn's traceback log on a 500 can't carry lyrics or the reply (AC-33).
- [ ] README: folder map, setup (key, both servers), and `scripts/check.sh`.
- [ ] Final review of the whole diff, then the explainer's walkthrough, then the PR.
