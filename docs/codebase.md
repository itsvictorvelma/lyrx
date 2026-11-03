# How the code fits together

This page describes the code that exists today. It is the map for anyone opening the project.

The long-term product plan is [AGENTS.md](../AGENTS.md). Each screen has a spec in [specs/](../specs/). Those files say what the product should do. This file says what is already built.

## The short version

Lyrx helps a learner rehearse a Japanese song. The page shows the audio, the Japanese words, the pronunciation, and the direct English meaning.

Today there are two small programs:

- `backend/` is the API. It stores songs and serves the audio.
- `frontend/` is the web page. It has Song Library, a development import screen, and Learn Song.

There is also a development-only helper, `backend/authoring/`, that will draft romaji and English files for a person to review. The API never uses it.

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
- `startSeconds` — optional time, in seconds, when that line begins

Line numbers start at 0. They must be `0`, `1`, `2`, and so on, with no gaps or duplicates.

`startSeconds` is the only timing value a line may carry. These names are still not allowed:

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
| `GET /api/songs` | Always | Lists published songs |
| `GET /api/songs/{songId}` | Always | Returns one song, its audio address, and its lyric lines in order |
| `POST /api/songs/{songId}/line-times` | Always | Saves a new start time for one or more lines |
| `POST /api/songs/{songId}/scan` | Always | Reads the saved audio and sets a start time on every line |
| `POST /api/import` | Development only, and only when `IMPORT_ENABLED=true` | Saves `original.txt`, `pronunciation.txt`, `translation.txt`, and `audio.mp3`. When `ALIGN_ON_IMPORT=true`, it also scans the audio |

In production, `/api/import` is not registered. A request gets the normal not-found response.

Development requests may come from `http://localhost:5173`. Production does not add that browser permission.

## Database

The database has two tables, created by Alembic. The API does not create them when it starts.

| Table | What it stores |
| --- | --- |
| `tracks` | Song id, title, artist, languages, duration, draft/published status, and the audio file's storage name and checksum |
| `lyric_versions` | One saved copy of the aligned lyric lines for a song, stored as JSON text |

A line start time is stored inside the lyric JSON. The tables have no timing column.

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
| `/songs/:songId` | Learn Song. Stacked Japanese, pronunciation, and direct meaning, plus the player. |

`frontend/src/App.tsx` chooses the route from the browser address. `frontend/src/library.tsx` reads `GET /api/songs`. `frontend/src/learn.tsx` reads one song. `frontend/src/player.tsx` plays that song's `audioUrl`. The player state stays inside the player, so the clock does not redraw the lyrics.

Learn Song starts with all three layers visible. The buttons are Japanese, Pronunciation (Romaji), and Direct Meaning. The choice is saved in `sessionStorage` under `lyrx.layers.v1` for this browser tab only. One layer always stays visible.

The player has play/pause, a seek bar, the elapsed time and duration, back and forward 10 seconds, volume, mute, and the speeds 0.75×, 1×, and 1.25×. Learn Song listens to that clock. It highlights the current line and can scroll that line into view.

On a narrow window the player sits at the bottom. On a wide window it stays under the header while the lyrics scroll. The page is wide enough on a desktop that several lines fit. Follow the song is on by default. Scrolling yourself turns follow off for the rest of the browser tab.

Follow uses each line's `startSeconds`. The current line is the latest start at or before the playhead. Before the first start, no line is marked. **Set this line to now** saves the playhead as that line's start. **Stamp next line** does the same and then moves to the following line. **Play from** seeks to a line that already has a time. **Scan line times** reads the saved mp3, matches the Japanese text to the words it hears, and saves a start on every line. The first scan downloads a speech model and can take a few minutes. Sung words over a band are a first pass: an entrance, a rest, or a long phrase can still land early or late. Set that line to now to move it. Scan again replaces the saved times. There is no tempo or beats-per-line control.

`ALIGN_ON_IMPORT=true` runs that same scan while a song is imported. A repeated import of the same text and audio keeps the times already saved, including corrections. `ALIGN_MODEL` chooses the speech model. `base` is the default. `small` is slower and usually closer.

The import form is in `frontend/src/import-form.tsx`. It posts to `http://localhost:8000`. Set `IMPORT_ENABLED=true` in `backend/.env`, then restart the API. The saved song is published immediately. Its address is made from the title, so the form does not ask for a song id. The same files can be imported again without creating a copy. To replace a song, check “Replace the saved song with this title.” After a successful import, the page opens that song.

Colors, type, and spacing live as variables at the top of `frontend/src/index.css`.

## Authoring tool

`backend/authoring/` is a development-only helper. It will read an `original.txt` and use a language model to draft `pronunciation.txt` and `translation.txt`. A person reviews the drafts, adds `audio.mp3`, and imports the bundle the normal way. Today it only has its settings; the LangGraph workflow is not written yet.

Its packages (LangChain, LangGraph, and the Gemini and Groq connectors) are in the `authoring` dependency group in `backend/pyproject.toml`. `uv sync` installs them by default. A production install leaves them out with `uv sync --no-default-groups`.

Its settings come from `backend/.env.authoring`, not `backend/.env`, so the API never needs a model key. Copy `backend/.env.authoring.example` and fill in:

- `AUTHORING_MODEL` — provider and model, for example `google_genai:<model id>` or `groq:<model id>`
- `GOOGLE_API_KEY` or `GROQ_API_KEY` — the key for that provider
- `AUTHORING_OUTPUT_DIR` — where drafts go; `./drafts` by default

`backend/.env.authoring` and `backend/drafts/` stay on your machine and are not committed.

`pyproject.toml` caps `cryptography` below version 49. Version 49 and later have no ready-made build for Intel Macs, so installing them would need a Rust compiler.

## Tests

Run every check at once from the repository root:

```bash
scripts/check.sh
```

It runs the backend tests, then the frontend tests, lint, and build. GitHub runs the same script on every pull request (`.github/workflows/ci.yml`).

Outside GitHub, the script counts failed runs on each branch in `.agent-state/`. After two failures, Cursor agents are blocked from running checks on that branch until you look at the problem and run `scripts/check.sh --reset`. Section "Agent setup" below explains why.

To run only the backend tests, from `backend/`:

```bash
uv run pytest
```

The tests check:

- A valid song is accepted.
- `startSeconds` is accepted. Other timing fields are rejected.
- Line numbers must start at 0 and have no gaps.
- Production cannot expose song import.
- The migration creates the two song tables and can remove them again.
- Starting the API does not create a database file.
- A valid import can be read back from the song list and song detail.
- The same import does not create a second copy.
- A mismatched lyric file does not save a song or an audio file.
- Starting the API does not load the authoring tool or LangChain.
- The check guardrail hook spots real check runs and reset attempts, and ignores the same words inside quotes, heredocs, and failure reports.
- Authoring settings need a `provider:model` value and that provider's key.

To run only the frontend checks, from `frontend/`:

```bash
npm test
npm run lint
npm run build
```

`npm test` checks lyric order, layer visibility, and the player clock. It does not open a browser.

## Agent setup

These files tell Cursor agents how to work in this repository. They do not change the app.

| File | What it does |
| --- | --- |
| `.cursor/rules/scope-guard.mdc` | Always on. The short list of things Prototype 1 must not add. |
| `.cursor/rules/execution-guardrail.mdc` | Always on. Two failed check runs, then write a failure report and stop. |
| `.cursor/rules/backend.mdc` | Only for files in `backend/`. Database, error, and contract rules. |
| `.cursor/rules/frontend.mdc` | Only for files in `frontend/`. Layer order, labels, and accessibility rules. |
| `.cursor/hooks.json` and `.cursor/hooks/check_guardrail.py` | Blocks an agent's third check run on a branch, and blocks agents from resetting the count. |
| `.cursor/skills/` | `plan-tickets`, `dispatch-ticket`, and `review-pr`. They load only when you ask for them by name. |
| `.cursor/BUGBOT.md` | Project checks Bugbot adds to its pull request reviews. |
| `.github/ISSUE_TEMPLATE/agent-task.yml` | The ticket format: goal, acceptance criteria, the files to start from, scope, tests, and dependencies. |
| `.cursorindexingignore` | Lock files agents can open but that stay out of code search. |

A local agent that hits the limit writes its report to `.agent-reports/ISSUE-<n>-FAILED.md`. That folder is not committed. A cloud agent posts the report on its draft pull request instead.

## What not to add yet

Do not add accounts, word-by-word timing, looping, or a microphone. Line start times and the current-line highlight are already part of Learn Song. The player still only reports the clock. Learn Song decides which line is current.

## When you change the code

Update this page in the same change if you add a folder, a route, a setting, or a data field. Keep the explanation in plain sentences. A new person should be able to read only this page and know what the code does today.
