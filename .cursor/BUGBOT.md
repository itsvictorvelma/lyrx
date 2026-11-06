# Lyrx review rules

Flag these in every pull request, in addition to normal bug review:

- **Scope:** line timing (including `startSeconds`), end times, word or mora timing, tempo, sync offsets, or timing columns; new screens or routes beyond AGENTS.md and docs/codebase.md; accounts; analytics; autoplay; looping; microphone; a public host; a second lyrics source besides the LRCLIB lookup in `backend/app/generation/`.
- **Plan documents:** any edit to `specs/`. Only Victor changes those. An `AGENTS.md` edit is blocking unless the pull request says Victor asked for it.
- **Generation:** LangChain, LangGraph, an authoring package, or a second offline draft path.
- **Contract parity:** `backend/app/contracts.py` changed without the matching change in `frontend/src/contracts.ts`, or the reverse.
- **Database:** schema change without an Alembic revision and downgrade; raw SQL or SQLite-only behavior; tables created at app startup.
- **Production boundary:** `POST /api/import` registered.
- **Errors:** responses that leak stack traces, filesystem paths, SQL, or secrets, or that skip the documented error envelope.
- **Rendering:** lyric text rendered as HTML.
- **Tests:** deleted, skipped, or weakened tests; behavior changes without tests.
- **Docs:** a new folder, route, setting, or data field without an update to `docs/codebase.md`.
