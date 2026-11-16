# 001 — Tasks

Each task is one test-writer → implementer → reviewer round. Server tests use a fake Claude client; no test calls the network.

- [x] T1 (setup): Scaffold `backend/` (uv, FastAPI, pytest) and `frontend/` (Vite, React, TS, Vitest on jsdom), `.env.example`, `scripts/check.sh`. Both test suites run and pass empty. No AC; the reviewer checks it against the plan.
- [ ] T2 (AC-9, 30, 31, 32): App shell: the error shape, Host check, `127.0.0.1` bind, `invalid_request`, `internal_error` with no leak.
- [ ] T3 (AC-1, 5, 6, 7, 8, 22): Splitting and limits: line splitting, `empty_input`, `input_too_large` at both limits, `no_japanese`, `server_not_configured`, each with Claude not called.
- [ ] T4 (AC-23, 24, 25, 26, 27, 28): Romaji from hiragana.
- [ ] T5 (AC-17, 19, plus the unit part of 18): Reading checks: the hiragana-only hard check and the kana-kept comparison.
- [ ] T6 (AC-10, 11, 12, 13, 14, 15, 16, 20, 21): The Claude call and reply checks: model and schema, prompt-as-data, refusal, truncation, invalid JSON, bad indexes, empty English, SDK errors.
- [ ] T7 (AC-2, 3, 4, 18, 29, 33): Assembling the four versions: the happy path, blank lines, non-Japanese lines, `readingVerified: false`, romaji equals `to_romaji(hiragana)`, nothing sensitive logged.
- [ ] T8 (AC-34, 35, 36, 37, 38, 39, 40, 41): The page.
- [ ] README: folder map, setup (key, both servers), and `scripts/check.sh`.
- [ ] Final review of the whole diff, then the explainer's walkthrough, then the PR.
