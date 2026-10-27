# How the code fits together

This page describes the code that exists today. It is the map for anyone opening the project.

The long-term product plan is [AGENTS.md](../AGENTS.md). Each screen has a spec in [specs/](../specs/). Those files say what the product should do. This file says what is already built.

## The short version

Lyrx helps a learner rehearse a Japanese song. The page shows the audio, the Japanese words, the pronunciation, and the direct English meaning.

Today there are two small programs:

- `backend/` is the API. It stores songs and serves the audio.
- `frontend/` is the web page. It has Song Library, a development import screen, and Learn Song.

## Backend

Start the API from the `backend/` directory:

```bash
cp .env.example .env
uv run uvicorn app.main:create_app --factory --reload
```

If startup says `Field required` for `environment` or `database_url`, `backend/.env` is missing. The copy command above fixes it. Run the command from `backend/`, not the repository root.

Check it with `GET http://localhost:8000/api/health`. A healthy API returns:

```json
{"status": "ok"}
```

### Settings

`backend/app/config.py` reads `backend/.env`.

Copy `backend/.env.example` to `backend/.env` before starting the API. The example file lists every setting.

Two rules are enforced in code:

1. Production cannot turn song import on. If `ENVIRONMENT` is `production` and `IMPORT_ENABLED` is `true`, the API refuses to start.
2. Audio files and temporary uploads must be different folders.

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

Timing fields are rejected, including a start time stored on an older copy of the line. These names are not allowed:

`activeLine`, `cue`, `end`, `endTime`, `offset`, `start`, `startSeconds`, `startTime`, `timestamp`, `timestamps`, `timing`

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
| `GET /api/songs` | Always | Lists published songs |
| `GET /api/songs/{songId}` | Always | Returns one song, its audio address, and its lyric lines in order |
| `POST /api/import` | Development only, and only when `IMPORT_ENABLED=true` | Saves `original.txt`, `pronunciation.txt`, `translation.txt`, and `audio.mp3` |

In production, `/api/import` is not registered. A request gets the normal not-found response.

Development requests may come from `http://localhost:5173`. Production does not add that browser permission.

## Database

The database has two tables, created by Alembic. The API does not create them when it starts.

| Table | What it stores |
| --- | --- |
| `tracks` | Song id, title, artist, languages, duration, draft/published status, and the audio file's storage name and checksum |
| `lyric_versions` | One saved copy of the aligned lyric lines for a song, stored as JSON text |

The tables have no timing column. A saved lyric JSON file that still contains `startSeconds` is read without that field.

From the `backend/` directory, create or update the local database with:

```bash
uv run alembic upgrade head
```

That uses `DATABASE_URL` from `backend/.env`. The example points at `backend/lyrx.db`. That file stays on your machine and is not committed.

## Frontend

Start it from the `frontend/` directory:

```bash
npm install
npm run dev
```

The page has three routes:

| Route | What it shows |
| --- | --- |
| `/` | Song Library. Each song is a link to Learn Song. |
| `/import` | Import Song. The link and the form are included only in a development build. |
| `/songs/:songId` | Learn Song. Original, romaji, and English, plus the player. |

`frontend/src/App.tsx` chooses the route from the browser address. `frontend/src/library.tsx` reads `GET /api/songs`. `frontend/src/learn.tsx` reads one song. `frontend/src/player.tsx` plays that song's `audioUrl`. The player state stays inside the player, so the clock does not redraw the lyrics.

Learn Song is a light reading page. It starts with all three documents visible. On a wide window they sit side by side and the page scrolls once. Each heading is Original, Romaji, or English, and that heading holds Hide or Show. The choice is saved in `sessionStorage` under `lyrx.layers.v1` for this browser tab only. One document always stays visible. There are no cells or per-line labels. On a narrow window the same three names are tabs, and one document is on screen.

The player is a compact bar under the header. It shows the song title, play/pause, a seek bar, the elapsed time and duration, back and forward 10 seconds, volume, mute, and the speeds 0.75×, 1×, and 1.25×. Play, pause, and mute are icons. The player does not mark a lyric line or move the page. The lyrics scroll under it.

The import form is in `frontend/src/import-form.tsx`. It posts to `http://localhost:8000`. Set `IMPORT_ENABLED=true` in `backend/.env`, then restart the API. The saved song is published immediately. Its address is made from the title, so the form does not ask for a song id. The same files can be imported again without creating a copy. To replace a song, check “Replace the saved song with this title.” After a successful import, the page opens that song.

Colors, type, and spacing live as variables at the top of `frontend/src/index.css`.

## Tests

From the `backend/` directory:

```bash
uv run pytest
```

The tests check:

- A valid song is accepted.
- Timing fields, including `startSeconds`, are rejected. A stored line that still has `startSeconds` is returned without it.
- Line numbers must start at 0 and have no gaps.
- Production cannot expose song import.
- The migration creates the two song tables and can remove them again.
- Starting the API does not create a database file.
- A valid import can be read back from the song list and song detail.
- The same import does not create a second copy.
- A mismatched lyric file does not save a song or an audio file.

The frontend checks are:

```bash
cd frontend
npm test
npm run lint
npm run build
```

`npm test` checks lyric order, layer visibility, and the player clock. It does not open a browser.

## What not to add yet

Do not add accounts, line start times, audio scanning, current-line highlight, follow-scroll, word-by-word timing, looping, or a microphone. The player only plays the audio.

## When you change the code

Update this page in the same change if you add a folder, a route, a setting, or a data field. Keep the explanation in plain sentences. A new person should be able to read only this page and know what the code does today.
