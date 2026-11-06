# Lyrx

Lyrx is a local page for rehearsing a Japanese song: Original, Hiragana, Romaji, and English, plus one MP3 you attach. There is no login.

[How the code fits together](docs/codebase.md) describes the code. [AGENTS.md](AGENTS.md) is the plan. Measured Groq limits are in [benchmarks/](benchmarks/).

You need Python 3.12 or newer (CI uses 3.14), [uv](https://docs.astral.sh/uv/), and Node 24. Lyric generation also needs the Swytchcode CLI, with Groq connected. The library, the reading page, and the player run without that.

## API

From `backend/`:

```bash
cp .env.example .env
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:create_app --factory --reload
```

If startup says `Field required`, `backend/.env` is missing. Copy the example and run the command from `backend/`. Use `uv run`. System Python does not have the project packages. The server target is `app.main:create_app --factory`, not `app.main:app`.

`backend/.env.example` lists every setting. `MEDIA_ROOT` and `AUDIO_STAGING_ROOT` must be different folders. If an older `.env` still has `MAX_IMPORT_BYTES` or `IMPORT_STAGING_ROOT`, rename them to `MAX_AUDIO_BYTES` and `AUDIO_STAGING_ROOT`. `FRONTEND_API_BASE_URL` is unused.

Check `GET http://localhost:8000/api/health`. A healthy API returns `{"status": "ok"}`.

The Groq key is not in `.env`. Connect it once with `swytchcode auth connect Groq`. A search reads the original lines from LRCLIB, then asks Groq once for the readings and the English. A miss does not call Groq.

## Page

From `frontend/`:

```bash
npm install
npm run dev
```

Open `http://localhost:5173`. The page calls `http://localhost:8000`.

## Checks

From the repository root:

```bash
scripts/check.sh
```

That runs the backend tests, then the frontend tests, lint, and build. CI runs the same script.
