# Lyrx

An app for learning a Japanese song. Type the song's name, and Lyrx shows every line in four columns: Original, Hiragana, Romaji, and English.

The lyrics come from [LRCLIB](https://lrclib.net) (free, no key). A free AI translator makes the hiragana, romaji, and English for every line: Groq first, Gemini as the backup when Groq is busy. The server checks every reply before showing it. Every song you open is saved on your computer (`data/lyrx.db`, gitignored), so opening it again is instant and uses no quota.

It runs on your own computer, on `127.0.0.1`, for now.

[AGENTS.md](AGENTS.md) holds the rules and the workflow. [specs/](specs/) holds what is planned and approved.

## Setup

You need [uv](https://docs.astral.sh/uv/) (Python 3.12 or later), Node.js with npm, and a free API key from Groq, Gemini, or both (both is best: when one is busy, the other answers).

1. Install the dependencies:
   ```bash
   cd backend && uv sync && cd ..
   cd frontend && npm install && cd ..
   ```
2. Get free keys at [Groq](https://console.groq.com/keys) and [Google AI Studio](https://aistudio.google.com/apikey), then:
   ```bash
   cp .env.example .env
   ```
   Put the keys after `GROQ_API_KEY=` and `GEMINI_API_KEY=` in `.env`. One key is enough; with both, a busy translator hands over to the other. The file is gitignored, so the keys are never committed.

Each request goes to Groq (`gpt-oss-120b`) first. When Groq is busy or out of quota, it goes to Gemini Flash-Lite, then a second Flash-Lite model. The order is `TRANSLATORS` in `backend/src/lyrx/config.py`. Free limits: Groq about 1,000 requests a day and 8,000 tokens a minute per model (about 2 songs a minute); Gemini Flash-Lite about 500 requests a day per model. A song is one call per 40 lines, so most songs take 1 or 2 calls. When every translator is at its limit, the page says so; try again later. Google may use what is sent on Gemini's free tier to improve its products.

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

Backend: ruff format, ruff lint, mypy `--strict`, pytest. Frontend: Prettier, ESLint, `tsc`, Vitest, and the build. No test calls Groq, Gemini, LRCLIB, or the network.

## Folder map

```
lyrx/
├── AGENTS.md              Rules and workflow
├── specs/                 One folder per feature
├── scripts/check.sh       Every check in one command
├── .env.example           The settings: GROQ_API_KEY and GEMINI_API_KEY
├── backend/               Python server (FastAPI, uv)
│   ├── src/lyrx/
│   │   ├── __main__.py        Starts the server on 127.0.0.1
│   │   ├── app.py             Builds the app: the routes, error handlers, and shared clients
│   │   ├── config.py          Every setting in one place
│   │   ├── errors.py          Error codes, their HTTP status, and their message
│   │   ├── schemas.py         What the page sends and receives
│   │   ├── song.py            Open a song: LRCLIB id → every line in four versions
│   │   ├── library.py         Saved songs in one SQLite file
│   │   ├── lyrics/            Finding and preparing lyrics
│   │   │   ├── lrclib.py          LRCLIB: client, search and record requests, record shape
│   │   │   ├── search.py          Typed text → a short ranked list of songs
│   │   │   ├── lines.py           Plain lyrics → trimmed lines, one blank line between verses
│   │   │   └── japanese.py        Kana and kanji, and whether lyrics look Japanese
│   │   ├── translation/       Lines → hiragana, romaji, and English
│   │   │   ├── chain.py           Groq first, Gemini when Groq is busy
│   │   │   ├── chunks.py          Splits a song, sends the chunks at once, retries
│   │   │   ├── prompt.py          What every translator is asked, and the reply shape
│   │   │   ├── checks.py          The checks on every reply: its JSON, then each line
│   │   │   ├── groq.py            Groq: client, one request, reply shape
│   │   │   ├── gemini.py          Gemini: client, one request, reply shape
│   │   │   └── results.py         The internal result shapes
│   │   └── server/            Guards and logging around every request
│   │       ├── host_check.py      Refuses requests not addressed to 127.0.0.1 or localhost
│   │       ├── body_limit.py      Refuses request bodies over 256 KiB before parsing
│   │       ├── crash_guard.py     Turns any unexpected error into a plain 500
│   │       └── request_log.py     One log line per request (no lyrics, no key)
│   └── tests/             The same folders as src/lyrx, one test_<module>.py per module,
│                          plus fake Groq, Gemini, and LRCLIB at the top
└── frontend/              The page (React, Vite, TypeScript)
    └── src/
        ├── main.tsx           Mounts the page
        ├── App.tsx            The page and its state: find, open, saved songs, errors
        ├── styles.css         Neutral colors, Japanese font stack, visible focus
        └── lyrics/
            ├── types.ts           Data shapes shared with the server
            ├── api.ts             The requests to the server, and the checks on their replies
            ├── SearchForm.tsx     The search box and Find button
            ├── OtherMatches.tsx   "Not this song?": the other results
            ├── VersionsTable.tsx  The four-column table
            ├── WaitingStatus.tsx  The waiting line with its seconds counter
            └── SavedSongs.tsx     "Your songs": open or remove a saved song
```
