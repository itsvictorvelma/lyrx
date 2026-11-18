# Lyrx

A local app for learning a Japanese song. Paste the lyrics, and Lyrx shows every line in four versions: Original, Hiragana, Romaji, and English.

It runs only on your own computer, on `127.0.0.1`. One call to the Claude API returns the hiragana reading and the English for every line. The server checks that reply and spells the romaji from the hiragana in code.

[AGENTS.md](AGENTS.md) holds the rules and the workflow. [specs/](specs/) holds what is planned and approved. The previous version is preserved at the git tag `archive/cursor-v1`.

## Setup

You need [uv](https://docs.astral.sh/uv/) (Python 3.12 or later), Node.js with npm, and a Claude API key.

1. Install the dependencies:
   ```bash
   cd backend && uv sync && cd ..
   cd frontend && npm install && cd ..
   ```
2. Add your API key. The `.env` file is gitignored, so the key is never committed:
   ```bash
   cp .env.example .env
   ```
   Then put your key after `ANTHROPIC_API_KEY=` in `.env`.

## Run

Use two terminals.

1. The server, on `127.0.0.1:8000`. The server reads the key from the environment, so pass the `.env` file to `uv`:
   ```bash
   cd backend
   uv run --env-file ../.env python -m lyrx
   ```
2. The page:
   ```bash
   cd frontend
   npm run dev
   ```
   Open the address it prints (normally `http://127.0.0.1:5173`). It forwards `/api` requests to the server.

Each submit makes one call to the Claude API, which is billed to your key.

## Check

```bash
scripts/check.sh
```

This runs every check, and nothing merges unless it passes:
- **Backend:** ruff format, ruff lint, mypy `--strict`, pytest.
- **Frontend:** Prettier, ESLint, `tsc`, Vitest, and the build.

No test calls the Claude API or the network.

## Folder map

```
lyrx/
├── AGENTS.md              Rules and workflow for every human and agent
├── specs/                 One folder per feature: spec, plan, tasks
├── scripts/check.sh       Every check in one command
├── .env.example           The one setting: ANTHROPIC_API_KEY
├── backend/               Python server (FastAPI, uv)
│   ├── src/lyrx/
│   │   ├── __main__.py        Starts the server on 127.0.0.1
│   │   ├── app.py             Builds the app: the route and the error handlers
│   │   ├── host_check.py      Refuses requests not addressed to 127.0.0.1 or localhost
│   │   ├── body_limit.py      Refuses request bodies over 64 KB before they are parsed
│   │   ├── crash_guard.py     Turns any unexpected error into a plain 500
│   │   ├── request_log.py     The one log line per request (no lyrics, no key)
│   │   ├── four_versions.py   The pipeline: paste in, four versions out
│   │   ├── lines.py           Reads and splits the paste and checks the size limits
│   │   ├── prompt.py          The system prompt and the message sent to Claude
│   │   ├── claude.py          The one Claude call and the checks on its reply
│   │   ├── gemini.py          The Gemini English request and the checks on its reply
│   │   ├── translation.py     Cuts a song into chunks and translates each with Gemini
│   │   ├── readings.py        Checks Claude's hiragana reading against the line
│   │   ├── romaji.py          Spells romaji from hiragana (modified Hepburn)
│   │   ├── kana.py            Which characters are kana and kanji
│   │   ├── schemas.py         Data shapes: request, response, Claude's reply
│   │   ├── errors.py          Error codes, their HTTP status, and their message
│   │   └── config.py          Every setting in one place
│   └── tests/             One test_<module>.py per module, plus a fake Claude client
└── frontend/              The page (React, Vite, TypeScript)
    └── src/
        ├── main.tsx           Mounts the page
        ├── App.tsx            Page layout and its state: idle, waiting, result, error
        ├── styles.css         Neutral colors, Japanese font stack, visible focus
        └── lyrics/
            ├── types.ts           Data shapes shared with the server
            ├── api.ts             The one request to the server, and the checks on its reply
            ├── errorMessages.ts   Error code → message on the page
            ├── PasteForm.tsx      The paste box, the button, and the waiting status
            └── FourVersions.tsx   Each line in its four labeled versions
```

Tests sit next to what they test: `backend/tests/test_<module>.py` and `frontend/src/**/*.test.ts(x)`.
