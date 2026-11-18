# Lyrx

An app for learning a Japanese song. Type the song's name, and Lyrx shows every line in four columns: Original, Hiragana, Romaji, and English.

The lyrics come from [LRCLIB](https://lrclib.net) (free, no key). One call to the Gemini API free tier makes the hiragana, romaji, and English for every line. The server checks that reply before showing it. If LRCLIB has no match, you can paste the lyrics instead.

It runs on your own computer, on `127.0.0.1`, for now.

[AGENTS.md](AGENTS.md) holds the rules and the workflow. [specs/](specs/) holds what is planned and approved.

## Setup

You need [uv](https://docs.astral.sh/uv/) (Python 3.12 or later), Node.js with npm, and a free Gemini API key.

1. Install the dependencies:
   ```bash
   cd backend && uv sync && cd ..
   cd frontend && npm install && cd ..
   ```
2. Get a free key at [Google AI Studio](https://aistudio.google.com/apikey), then:
   ```bash
   cp .env.example .env
   ```
   Put your key after `GEMINI_API_KEY=` in `.env`. The file is gitignored, so the key is never committed.

The free tier has daily and per-minute limits (shown in AI Studio). A song is a few small calls sent at once (about one per 15 lines). When the limit is reached, the page says so; try again later. Google may use what is sent on the free tier to improve its products.

## Run

Use two terminals.

1. The server, on `127.0.0.1:8000`:
   ```bash
   cd backend
   uv run --env-file ../.env python -m lyrx
   ```
2. The page:
   ```bash
   cd frontend
   npm run dev
   ```
   Open the address it prints (normally `http://127.0.0.1:5173`).

## Check

```bash
scripts/check.sh
```

Backend: ruff format, ruff lint, mypy `--strict`, pytest. Frontend: Prettier, ESLint, `tsc`, Vitest, and the build. No test calls Gemini, LRCLIB, or the network.

## Folder map

```
lyrx/
├── AGENTS.md              Rules and workflow
├── specs/                 One folder per feature
├── scripts/check.sh       Every check in one command
├── .env.example           The one setting: GEMINI_API_KEY
├── backend/               Python server (FastAPI, uv)
│   ├── src/lyrx/
│   │   ├── __main__.py        Starts the server on 127.0.0.1
│   │   ├── app.py             Builds the app: three routes and the error handlers
│   │   ├── song_search.py     Search: typed text → ranked LRCLIB results
│   │   ├── song_versions.py   Open a song: LRCLIB id → four versions
│   │   ├── lrclib.py          The two LRCLIB requests, with caps and checks
│   │   ├── four_versions.py   The shared pipeline: cleaned lines → four versions
│   │   ├── chunks.py          Cuts a song into small chunks sent to Gemini at the same time
│   │   ├── retries.py         Retries an overloaded or failed Gemini request after a short wait
│   │   ├── gemini.py          The Gemini request and the checks on its reply
│   │   ├── lines.py           Splits lyrics into cleaned lines; detects Japanese
│   │   ├── lyric_cleanup.py   Removes unwanted characters and splits overlong lines
│   │   ├── looks_japanese.py  Whether lyrics look Japanese (enough lines with kana)
│   │   ├── kana.py            Which characters are kana and kanji
│   │   ├── host_check.py      Refuses requests not addressed to 127.0.0.1 or localhost
│   │   ├── body_limit.py      Refuses request bodies over 256 KiB before parsing
│   │   ├── crash_guard.py     Turns any unexpected error into a plain 500
│   │   ├── request_log.py     One log line per request (no lyrics, no key)
│   │   ├── schemas.py         Data shapes
│   │   ├── errors.py          Error codes, their HTTP status, and their message
│   │   └── config.py          Every setting in one place
│   └── tests/             One test_<module>.py per module, plus fake Gemini and LRCLIB
└── frontend/              The page (React, Vite, TypeScript)
    └── src/
        ├── main.tsx           Mounts the page
        ├── App.tsx            The page and its state: find, open, paste, errors
        ├── styles.css         Neutral colors, Japanese font stack, visible focus
        └── lyrics/
            ├── types.ts           Data shapes shared with the server
            ├── api.ts             The three requests, and the checks on their replies
            ├── SearchForm.tsx     The search box and Find button
            ├── OtherMatches.tsx   "Not this song?": the other results
            ├── VersionsTable.tsx  The four-column table
            ├── WaitingStatus.tsx  The waiting line with its seconds counter
            └── PasteForm.tsx      The paste fallback
```
