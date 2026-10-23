# Lyrx Prototype 1

Lyrx helps a learner rehearse a Japanese song with audio, romaji pronunciation, and direct English meaning.

Start with the [Prototype 1 build plan](AGENTS.md), then use the feature specifications in [`specs/`](specs/).

Song summary, song detail, lyric line, and error contracts live in [`backend/app/contracts.py`](backend/app/contracts.py) and [`frontend/src/contracts.ts`](frontend/src/contracts.ts). Lyric indexes are zero-based. Timing fields are rejected. The import route is registered only for local development when import is explicitly enabled.

## Local development

### Backend

```bash
cd backend
cp .env.example .env
uv run uvicorn app.main:create_app --factory --reload
```

Health check: `GET /api/health`

### Frontend

```bash
cd frontend
npm install
npm run dev
```
