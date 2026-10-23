# How the code fits together

This page describes the code that exists today. It is the map for anyone opening the project.

The long-term product plan is [AGENTS.md](../AGENTS.md). Each future screen has a spec in [specs/](../specs/). Those files say what to build. This file says what is already built.

## The short version

Lyrx will help a learner rehearse a Japanese song. The page will show the audio, the Japanese words, the pronunciation, and the direct English meaning.

Today there are two small programs:

- `backend/` is the API.
- `frontend/` is the web page.

There is no song list, import form, lesson page, audio player, or database yet. The web page is only a title and one sentence.

## Backend

Start the API from the `backend/` directory:

```bash
cp .env.example .env
uv run uvicorn app.main:create_app --factory --reload
```

Check it with `GET http://localhost:8000/api/health`. A healthy API returns:

```json
{"status": "ok"}
```

### Settings

`backend/app/config.py` reads `backend/.env`.

Copy `backend/.env.example` to `backend/.env` before starting the API. The example file lists every setting.

Two rules are enforced in code:

1. Production cannot turn song import on. If `ENVIRONMENT` is `production` and `IMPORT_ENABLED` is `true`, the API refuses to start.
2. Audio files, rights evidence, and temporary uploads must be three different folders.

Import stays off unless you are in development and you set `IMPORT_ENABLED=true`.

### Song and error shapes

`backend/app/contracts.py` defines the only fields the API accepts.

A song summary has:

- `id`
- `title`
- `artist`
- `sourceLanguage`
- `targetLanguage`
- `durationSeconds`, which may be left out
- `status`, either `draft` or `published`

A full song has everything in the summary, plus:

- `audioUrl`
- `contentVersion`
- `lines`

Each lyric line has:

- `id`
- `index`
- `originalText` — Japanese
- `pronunciationRomaji` — pronunciation, not an English translation
- `translationEnglish` — direct English meaning

Line numbers start at 0. They must be `0`, `1`, `2`, and so on, with no gaps or duplicates.

Timing fields are rejected. These names are not allowed:

`activeLine`, `cue`, `end`, `endTime`, `offset`, `start`, `startTime`, `timestamp`, `timestamps`, `timing`

Any other unknown field is rejected too.

An error has:

- `code` — a short stable name for the error
- `message` — a safe sentence for a person
- `details` — optional list of `field`, `file`, and `line`
- `requestId` — optional trace id

The browser copy of these shapes is `frontend/src/contracts.ts`. If you change a field, change both files in the same commit.

### Routes

`backend/app/main.py` creates the API.

| Route | When it exists | What it does now |
| --- | --- | --- |
| `GET /api/health` | Always | Returns `{"status": "ok"}` |
| `POST /api/import` | Development only, and only when import is enabled | Returns "not implemented". It does not save a song. |

In production, `/api/import` is not registered. A request gets the normal not-found response.

Development requests may come from `http://localhost:5173`. Production does not add that browser permission.

## Frontend

Start it from the `frontend/` directory:

```bash
npm install
npm run dev
```

`frontend/src/App.tsx` shows the Lyrx title and one sentence. It does not call the API yet.

`frontend/src/contracts.ts` matches the backend song and error shapes. It is there so the next screen uses the same field names.

## Tests

From the `backend/` directory:

```bash
uv run pytest
```

The tests check four things:

- A valid song is accepted.
- Timing fields are rejected.
- Line numbers must start at 0 and have no gaps.
- Production cannot expose song import.

The frontend check is:

```bash
cd frontend
npm run build
```

## What not to add yet

Do not add screens, database tables, accounts, or lyric timing while finishing this foundation. The next planned pieces are the database and the real Song Library and Learn Song screens. Their specs already describe that work.

## When you change the code

Update this page in the same change if you add a folder, a route, a setting, or a data field. Keep the explanation in plain sentences. A new person should be able to read only this page and know what the code does today.
