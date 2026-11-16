# 001 — Plan

## Files

### Root

| File | New or changed | Why |
|---|---|---|
| `.env.example` | new | Shows the one setting, `ANTHROPIC_API_KEY=`, with no value |
| `scripts/check.sh` | new | One command for every check: ruff, mypy, pytest, Prettier, ESLint, tsc, Vitest, build |
| `README.md` | changed | Folder map, how to set the key, run both servers, and run the checks |

### Backend — `backend/`

| File | New or changed | Why |
|---|---|---|
| `pyproject.toml`, `uv.lock` | new | uv project `lyrx`; ruff, mypy (strict), and pytest config live here |
| `src/lyrx/__init__.py` | new | Package marker |
| `src/lyrx/__main__.py` | new | `uv run python -m lyrx` starts uvicorn on the host and port from `config.py` (AC-31) |
| `src/lyrx/config.py` | new | Every setting in one place: host, port, model, effort, `max_tokens`, timeout, size limits, and reading the API key |
| `src/lyrx/errors.py` | new | `ApiError` and the table of error codes → HTTP status and message |
| `src/lyrx/schemas.py` | new | Pydantic shapes: request body, response line, Claude's reply |
| `src/lyrx/app.py` | new | `create_app()`: Host check, error handlers, `POST /api/versions` (AC-9, 30, 32) |
| `src/lyrx/lines.py` | new | Split the paste, check size limits, detect Japanese (AC-1, 5–8) |
| `src/lyrx/prompt.py` | new | The system prompt and the user-message builder, as readable text (AC-11, 12) |
| `src/lyrx/claude.py` | new | The one Claude call and the checks on its reply (AC-10, 13–16, 20, 21) |
| `src/lyrx/readings.py` | new | Hiragana-only hard check and kana-kept comparison (AC-17–19) |
| `src/lyrx/romaji.py` | new | One pure `to_romaji(hiragana)` (AC-23–28) |
| `src/lyrx/four_versions.py` | new | The pipeline: split → limits → key → call → checks → four versions (AC-2–4, 18, 22, 29, 33) |
| `tests/conftest.py` | new | The fake Claude client and a test-app fixture |
| `tests/test_<module>.py` | new | One test file per module above |

### Frontend — `frontend/`

| File | New or changed | Why |
|---|---|---|
| `package.json`, `package-lock.json` | new | Scripts: `dev`, `build`, `test`, `lint`, `format:check`, `typecheck` |
| `vite.config.ts` | new | Dev server on `127.0.0.1`; `/api` forwarded to `127.0.0.1:8000`; Vitest on jsdom |
| `tsconfig.json`, `eslint.config.js`, `.prettierrc` | new | Strict TypeScript, lint, and format settings |
| `index.html` | new | The page shell |
| `src/main.tsx` | new | Mounts the app |
| `src/App.tsx` | new | Page layout: form above, result or error below; holds the request state |
| `src/styles.css` | new | Plain readable styles, Japanese font stack, visible focus |
| `src/lyrics/types.ts` | new | `Line` and `ApiErrorCode` types matching the server |
| `src/lyrics/api.ts` | new | `getFourVersions(lyrics)`: one POST, returns lines or an error code |
| `src/lyrics/errorMessages.ts` | new | Error code → message on the page |
| `src/lyrics/PasteForm.tsx` | new | Labeled text area, button, waiting status (AC-34–36) |
| `src/lyrics/FourVersions.tsx` | new | One group per line with the four labeled rows (AC-37, 40, 41) |
| `src/lyrics/*.test.tsx`, `src/App.test.tsx` | new | Tests next to what they test (AC-34–41) |

## Approach

**Readability first.** Each module does one job named in its filename. Each file opens with a one-line docstring or comment saying what it is for. Settings live only in `config.py` and data shapes only in `schemas.py`. A newcomer can read `four_versions.py` top to bottom and see the whole request.

**Server.** `create_app(claude_client=None)` builds the FastAPI app. Tests pass a fake client; the real SDK client is built only when a request needs it. A middleware rejects any `Host` that isn't `127.0.0.1` or `localhost` (any port) before routing. Exception handlers turn `ApiError`, validation errors, and anything unexpected into the one error shape, with no exception text. Every refusal before the call (empty, too large, no Japanese, no key) happens before the client is touched, so tests can assert "Claude not called".

**The Claude call** (`claude.py`). It wraps the official `anthropic` SDK, following the current SDK docs:
- `client.messages.stream(...)` + `.get_final_message()`, `model="claude-opus-5-5"`, `max_tokens=32000`, `output_config={"effort": "medium", "format": {"type": "json_schema", "schema": …}}`.
- Streaming keeps a 200-line paste from hitting HTTP timeouts. Thinking is always on for this model and is not configured. Effort `medium` is the model's default, set explicitly.
- The client is made with `timeout=120` and the SDK's default transport retries.
- Reply checks, in order: `stop_reason` refusal, then `max_tokens`; `json.loads` and Pydantic validation; exact indexes; non-empty English.
- SDK errors are caught specific-first (`APIStatusError`, then `APIConnectionError`, which includes timeouts) → `model_unavailable`.

**Romaji** is a hand-written kana table plus three rules: small っ, ん, and ー. It uses no library. It works word by word, so the は/へ particle rule is a whole-word match.

**Reading checks.** The hard check is a character-set test. The kana-kept comparison turns katakana into hiragana by code point, then builds a pattern from the original where each kanji run matches one or more hiragana.

**Logging** writes one line per request: status, code, line and character counts, duration, and token usage. It never logs the lyrics, the reply, headers, or the key.

**Page.** `App` holds one state: idle, waiting, result, or error. `PasteForm` and `FourVersions` are presentational. Requests use `fetch` with no router and no state library. All text renders as React children. CSS is neutral with a Japanese font stack and a visible focus outline, and no invented colors.

**Quality tools.** `ruff format`, `ruff check`, `mypy --strict`, and `pytest` for the backend. Prettier, ESLint (typescript-eslint, react-hooks), `tsc --noEmit`, Vitest, and `vite build` for the frontend. `scripts/check.sh` runs them all and fails on the first error.

## Side effects

- **Dependencies, all approved:**
  - Backend: `fastapi`, `uvicorn`, `anthropic`; dev `pytest`, `httpx`, `ruff`, `mypy`.
  - Frontend: `react`, `react-dom`; dev `vite`, `@vitejs/plugin-react`, `typescript`, `@types/react`, `@types/react-dom`, `vitest`, `jsdom`, `@testing-library/react`, `@testing-library/user-event`, `eslint`, `typescript-eslint`, `eslint-plugin-react-hooks`, `prettier`.
- Adds `backend/`, `frontend/`, `scripts/`, and `.env.example`.
- No database, no files written at runtime, no CI change.
