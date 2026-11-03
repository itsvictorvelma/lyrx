# Lyrx review rules

Flag these in every pull request, in addition to normal bug review:

- **Scope:** any timing field or UI (timestamp, start/end, cue, offset, active line, word or mora timing), new screens or routes beyond AGENTS.md, accounts, learner writes, analytics, autoplay, looping, line seek, or provider/catalog API calls.
- **Plan documents:** any edit to `AGENTS.md` or `specs/`. Only Victor changes these; mark it as blocking.
- **Contract parity:** `backend/app/contracts.py` changed without the matching change in `frontend/src/contracts.ts`, or the reverse.
- **Database:** schema change without an Alembic revision and downgrade; raw SQL or SQLite-only behavior; tables created at app startup.
- **Production boundary:** the import route or mutation reachable when `environment` is `production`, or protected only by client-side hiding.
- **Errors:** responses that leak stack traces, filesystem paths, SQL, or secrets, or that skip the documented error envelope.
- **Rendering:** imported lyric text rendered as HTML.
- **Authoring isolation:** `backend/app/` importing `authoring` or any `langchain`/`langgraph` package.
- **Tests:** deleted, skipped, or weakened tests; behavior changes without tests.
- **Docs:** a new folder, route, setting, or data field without an update to `docs/codebase.md`.
