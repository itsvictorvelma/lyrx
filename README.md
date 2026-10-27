# Lyrx Prototype 1

Lyrx helps a learner rehearse a Japanese song with audio, romaji pronunciation, and direct English meaning.

Read [How the code fits together](docs/codebase.md) for the code that exists today. The [Prototype 1 build plan](AGENTS.md) and [`specs/`](specs/) describe the product that still needs to be built.

## Local development

### Backend

```bash
cd backend
cp .env.example .env
uv run uvicorn app.main:create_app --factory --reload
```

If startup says `Field required`, `backend/.env` is missing. Copy the example file and run this from `backend/`. Use `uv run`, not system Python. System Python raises `ModuleNotFoundError: No module named 'sqlalchemy'`. The server target is `app.main:create_app --factory`, not `app.main:app`. After a dependency change, run `uv sync` in `backend/`.

Health check: `GET /api/health`

### Frontend

```bash
cd frontend
npm install
npm run dev
```
