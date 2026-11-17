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
| `src/lyrx/py.typed` | new | Empty marker so mypy type-checks the package when tests import it |
| `src/lyrx/__main__.py` | new | `uv run python -m lyrx` starts uvicorn on the host and port from `config.py` (AC-31) |
| `src/lyrx/config.py` | new | Every setting in one place: host, port, model, effort, `max_tokens`, timeout, size limits, and reading the API key |
| `src/lyrx/errors.py` | new | `ApiError`, the table of error codes → HTTP status and message, and `error_response` (the one error shape as a JSON response) |
| `src/lyrx/schemas.py` | new | Pydantic shapes: request body, response line, Claude's reply. Internal frozen dataclasses: `Paste` (NFC text and its lines), `TokenUsage`, and `ClaudeReadings` (the checked reply lines with the token counts) |
| `src/lyrx/app.py` | new | `create_app()`: stacks the ASGI layers, error handlers, `POST /api/versions` (AC-9, 30, 32) |
| `src/lyrx/host_check.py` | new | Plain ASGI layer refusing any `Host` but `127.0.0.1` or `localhost` (AC-30) |
| `src/lyrx/body_limit.py` | new | Plain ASGI layer refusing a body over 64 KB before parsing; a cut-off body never reaches the app (AC-44) |
| `src/lyrx/crash_guard.py` | new | Outermost ASGI layer: no exception escapes to uvicorn; answers `internal_error`, logs only the class name (AC-32, 33) |
| `src/lyrx/request_log.py` | new | `logged_request`, the context manager the route wraps the pipeline in: times it, writes the one `name=value` log line per `POST /api/versions`, and turns an unexpected exception into `internal_error` (AC-32, 33) |
| `src/lyrx/kana.py` | new | Which characters are kana and kanji, and katakana → hiragana. Shared by `lines`, `romaji`, `readings` |
| `src/lyrx/lines.py` | new | Read the paste (NFC, then split), check size limits, detect Japanese (AC-1, 5–8) |
| `src/lyrx/prompt.py` | new | The system prompt and the user-message builder, as readable text (AC-11, 12) |
| `src/lyrx/claude.py` | new | The one Claude call and the checks on its reply (AC-10, 13–16, 20, 21) |
| `src/lyrx/readings.py` | new | Hiragana-only hard check and kana-kept comparison (AC-17–19) |
| `src/lyrx/romaji.py` | new | One pure `to_romaji(hiragana)` (AC-23–28) |
| `src/lyrx/four_versions.py` | new | The pipeline: split → limits → key → call → checks → four versions (AC-2–4, 18, 22, 29, 33) |
| `tests/conftest.py` | new | The fake Claude client and a test-app fixture |
| `tests/raw_asgi.py` | new | Calls the ASGI app directly with a scripted `receive`, as uvicorn does, and logs an escaping exception to `uvicorn.error` |
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
- SDK errors are caught specific-first (`APIStatusError`, then `APIConnectionError`, which includes timeouts) → `model_unavailable`. So are raw `httpx2.TransportError`s, which the SDK lets through when a streamed reply breaks or times out after the headers arrive. `httpx2` (the SDK's own HTTP library) is a direct runtime dependency, approved by the user.

**Romaji** is a hand-written kana table plus three rules: small っ, ん, and ー. It uses no library. It works word by word, so the は/へ particle rule is a whole-word match.

**Romaji edge cases** (coordinator decisions within modified Hepburn; the spec leaves them open):
- Katakana in the input is turned into hiragana first, then romanized.
- A word is split on ASCII or full-width spaces. Spacing is kept as given, with no collapsing. ん before a space is plain `n` (`ほん あお` → `hon ao`).
- The particle rule ignores punctuation attached to the word: `は、` → `wa,` and `へ。` → `e.`.
- Extended kana from loanwords: ふぁ fa, ふぃ fi, ふぇ fe, ふぉ fo, ふゅ fyu, てぃ ti, でぃ di, とぅ tu, どぅ du, しぇ she, じぇ je, ちぇ che, いぇ ye, うぃ wi, うぇ we, うぉ wo, ゔ vu, and ゔぁ/ゔぃ/ゔぇ/ゔぉ va/vi/ve/vo. ゐ is wi and ゑ is we. A small vowel or ゃゅょゎ that can't combine with the kana before it is read as its own sound (a, i, u, e, o, ya, yu, yo, wa).
- ゝ repeats the kana before it, and ゞ repeats it voiced (`すゞ` → `suzu`).
- Small っ before ん, ー, another っ, or at the end is dropped. A ー with no vowel before it (at the start of a word, or after ん or っ) is dropped.
- Full-width Latin letters and digits pass through unchanged, like other non-kana.
- A dropped mark is invisible to the next rule. `あっー` is `aa`: っ is dropped, and ー repeats the vowel of あ. `んーあ` is `n'a`: ー is dropped, so ん comes before a vowel.
- ゝ repeats the whole sound before it as written (`ぶゝ` → `bubu`, `きゃゝ` → `kyakya`). ゞ repeats it voiced when a voiced form exists, and as written otherwise (`あゞ` → `aa`). Either mark at the start of a word is dropped.
- Small katakana ヵ and ヶ (and their hiragana ゕ ゖ) read as `ka` and `ke`. No kana from the tables survives into the romaji. Rare marks outside them (ヷ–ヺ, ゟ, ヿ, ゠, ゛ ゜) pass through as written.
- `…`, `～`, `〜`, `『`, `』` and `・` also count as attached punctuation for the particle rule. They pass through unchanged.
- ASCII punctuation counts as attached punctuation for the particle rule (`は!` → `wa!`). Katakana ハ or ヘ standing alone becomes hiragana first, so it reads `wa` or `e`.

**Reading checks.** `readings.py` has three public functions:
- `tidy_reading(reading)` runs first in the pipeline. It normalizes to NFC, trims leading and trailing ASCII spaces, and collapses runs of ASCII spaces to one. It changes nothing else, so a tab or a full-width space is still caught by the hard check.
- `reading_is_allowed(original, reading)` is the hard check (rule 5). The only whitespace allowed is a single ASCII space between words; any other whitespace is refused even if the original has it. Hiragana includes ゝ and ゞ. As the spec says, a character from the original line (Latin, digits, punctuation, even katakana or kanji) passes this check, but rule 6 then flags a katakana or kanji left in the reading.
- `reading_keeps_kana(original, reading)` is the warning (rule 6). It removes whitespace and turns katakana into hiragana, then walks the original as tokens: each kanji run (using `kana.is_kanji`, 々 included) and each other character. It checks the reading with a small dynamic-programming matcher over (token, reading position). The cost is tokens × reading length, which is quadratic, with no regex and no exponential backtracking. It stays bounded because a line is at most 200 characters (AC-45) and `reading_is_allowed` refuses a reading longer than 6× its line (AC-46) before this runs. Kana in the original, including ゝ and ゞ, must appear in the reading exactly as written. A kanji run must match one or more characters from hiragana and ー, and the first must be a hiragana letter.

**Logging** writes one line per request: status, code, line and character counts, duration, and token usage. It never logs the lyrics, the reply, headers, or the key.

**T7 decisions** (coordinator; the spec leaves them open):
- The paste is normalized to NFC as it enters the pipeline, before splitting, so `original` is the NFC line as split. Composed and decomposed kana look the same on the page.
- The one log line goes to the `lyrx` logger as `name=value` fields: `status`, `code` (errors only), `lines`, `characters`, `duration_ms`, `input_tokens`/`output_tokens` on success, and `exception=<ClassName>` on `internal_error` only (the class name, never the message). It covers `POST /api/versions` only. Host refusals, 404, 405 and `invalid_request` are not logged.
- No exception may escape the app, since uvicorn would log its traceback and message. An outermost ASGI layer turns any unexpected exception into the `internal_error` response (if nothing has been sent yet) and logs only the exception's class name.
- The Host check becomes a plain ASGI middleware like the body-size limit, so a client that disconnects mid-body gets no response and causes no error or traceback.

**Page.** `App` holds one state: idle, waiting, result, or error. `PasteForm` and `FourVersions` are presentational. Requests use `fetch` with no router and no state library. All text renders as React children. CSS is neutral with a Japanese font stack and a visible focus outline, and no invented colors. The colors, approved by the user, are CSS variables on `:root`: text `#1a1a1a`, muted labels `#5c5c5c`, borders `#d0d0d0`, page `#ffffff`, error text `#a40000` (always with the word "Error:", never color alone), and focus `2px solid` in the text color. Under `prefers-color-scheme: dark`: text `#ececec`, muted `#a8a8a8`, border `#444444`, page `#161616`, error `#ff8a80`.

**T8 decisions** (coordinator; the spec leaves them open):
- The `server_not_configured` message is shown as plain text, without the backticks the spec table uses for code style.
- A reply that arrives but is not the error shape (non-JSON, or no string `code`) shows "Something went wrong. Try again.", as the spec's "any other code" row says. Only a rejected `fetch` shows the server-unreachable message.
- A reply the page cannot trust is its own result, `unreadable`, and shows the same fallback message. That covers a reply that isn't the error shape, a 200 whose `lines` are not valid `Line`s (including indexes that don't run 0, 1, 2… in order), and a body that fails to read after the response arrived (AGENTS.md: validate at every boundary).
- T9 (user-approved, from the Impeccable critique): a result shows an `h2` "Four versions (N lines)" above the list, counting blank lines, and focus moves to it on every new result so keyboard and screen-reader users know it worked. On an error (an error reply, unreachable, or unreadable), focus moves to the paste box instead, with the pasted text kept, so the learner fixes it where they left off; otherwise focus is lost when the button disables. The paste box border uses `--color-muted` to meet the WCAG 3:1 non-text contrast rule; no new color.

**Quality tools.** `ruff format`, `ruff check`, `mypy --strict`, and `pytest` for the backend. Prettier, ESLint (typescript-eslint, react-hooks), `tsc --noEmit`, Vitest, and `vite build` for the frontend. `scripts/check.sh` runs them all and fails on the first error.

## Side effects

- **Dependencies, all approved:**
  - Backend: `fastapi`, `uvicorn`, `anthropic`; dev `pytest`, `httpx`, `ruff`, `mypy`.
  - Frontend: `react`, `react-dom`; dev `vite`, `@vitejs/plugin-react`, `typescript`, `@types/react`, `@types/react-dom`, `vitest`, `jsdom`, `@testing-library/react`, `@testing-library/user-event`, `eslint`, `typescript-eslint`, `eslint-plugin-react-hooks`, `prettier`.
- Adds `backend/`, `frontend/`, `scripts/`, and `.env.example`.
- No database, no files written at runtime, no CI change.
