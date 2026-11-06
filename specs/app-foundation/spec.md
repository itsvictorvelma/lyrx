---
cursor:
  subagentId: "bc-43f25a2f-93d8-5ec7-9282-d2774358e7bf"
---

# Application foundation specification

Parent plan: [Prototype 1 build plan](../../AGENTS.md)

Related features:

- [Song creation](../song-creation/spec.md)
- [Song Library](../song-library/spec.md)
- [Learn Song](../learn-song/spec.md)
- [Audio player](../audio-player/spec.md)

## Goal

Create the smallest stable platform on which Song Library, new-song chat, and Learn Song can be implemented and tested without accounts, timing data, or a public multi-user host.

## Scope

- React + TypeScript + Vite frontend
- Plain CSS in `frontend/src/index.css`
- The app's own links in `frontend/src/routes/`
- FastAPI backend
- SQLite accessed only through SQLAlchemy
- Alembic migrations
- Shared request/response/error contracts
- Local media filesystem and media delivery boundary
- Swytchcode call to Groq for lyric generation, with the key kept out of the app
- Baseline accessibility, test, lint, type-check, and build configuration

## Architecture

### Frontend shell

- One application shell owns the header, the workspace, and the screen for the current address.
- Addresses are read and changed by the app's own links.
- Addresses:
  - `/` and `/songs` — Song Library
  - `/songs/new` and `/search` — new song
  - `/songs/:songId` — Learn Song
- An unknown address shows a not-found state and a link to Song Library.
- No authentication provider, account context, global server-state library, or timing engine.

### Backend shell

- FastAPI application with:
  - Health/readiness endpoint suitable for deployment checks
  - Song list, song detail, generation, save, and MP3 attach from [Song creation](../song-creation/spec.md)
  - Media URL generation
- Validate configuration at startup and fail clearly on missing/unsafe values.
- Keep business validation independent of HTTP so generation and repository tests do not need a running server or a Groq call.

### Persistence

- SQLAlchemy owns models, sessions, and repository queries.
- SQLite database URL is environment configured.
- Alembic owns schema creation and evolution; application startup must not call `create_all`.
- The schema has only `tracks` and `lyric_versions`.
- Store aligned-line documents as schema-versioned JSON text after domain validation.
- Use dialect-portable identifiers, booleans, timestamps, constraints, and indexes.

### PostgreSQL upgrade seam

Before public multi-user/multi-instance operation:

1. Provision PostgreSQL.
2. Apply the full Alembic chain to an empty PostgreSQL database.
3. Export/import validated data through a controlled migration.
4. Run repository, import, and API contract suites against PostgreSQL.
5. Switch the external database URL.
6. Verify rollback and backup procedures.

Prototype 1 must not claim PostgreSQL compatibility solely because SQLAlchemy is used.

## Shared contracts

### Song summary

Required fields:

- `id`
- `title`
- `artist`
- `sourceLanguage`
- `targetLanguage`
- `durationSeconds` when known
- `status`

### Song detail

Song summary plus:

- `audioUrl`, null when no MP3 is stored
- `contentVersion`
- ordered `lines`

### Line

- `id`
- `index`
- `originalText`
- `readingHiragana`
- `pronunciationRomaji`
- `translationEnglish`

The contract rejects timestamp/timing fields. Line indexes are unique and monotonic within a version.

### Error response

- `code`: stable machine-readable string
- `message`: safe user-facing summary
- `details`: optional structured field/file/line information
- `requestId`: optional trace value

Known domain/validation errors map to 4xx responses. Unknown faults map to a generic 5xx response without internal details.

## Environment contract

Required categories:

- Environment name
- Database URL
- Media root
- Public media base URL
- Frontend API base URL
- `GROQ_MODEL`, default `openai/gpt-oss-120b`
- Maximum audio upload size
- Allowed development origin

The Groq key is not an application environment variable. Swytchcode injects it.

Production invariants:

- `POST /api/import` is absent.
- Read routes still start when the Groq credential is missing. Generation returns `groq_unauthorized`.
- Media root is not the same directory as temporary upload staging.
- Debug mode and verbose error output are disabled.

## Validation and error states

- Invalid configuration: startup fails with the setting name, not its secret value.
- Database unavailable/migration missing: readiness fails; API returns safe service error.
- Invalid stored line document: detail endpoint fails safely and logs song/version identifiers.
- Missing media file: song detail may return an unavailable-media status or a documented safe error; never return a filesystem path.
- Unknown route/song: accessible not-found response.
- Invalid `sessionStorage` data: clear/fallback instead of crashing.

## Accessibility

- Application shell provides one main landmark and skip link.
- Route changes move focus to the screen heading or an announced route target.
- Global errors use an accessible alert/status pattern.
- Not-found and failure screens contain keyboard-operable recovery actions.
- Plain CSS preserves visible focus and sufficient contrast.
- Responsive behavior does not reorder semantic reading order.

## Security

- No users, sessions, tokens, password code, or authorization roles.
- Learner-facing writes are generation, save, and one MP3 upload, on this install. A saved song is not rewritten from chat.
- `POST /api/import` is not registered.
- Generated media paths prevent traversal and hide local paths.
- Imported strings render as text, never raw HTML.
- CORS is restricted to configured origins; do not use permissive credentials settings.
- Secrets are excluded from responses, source control, frontend bundles, and public media.
- Log request IDs and safe identifiers, not lyric payloads or local file paths by default.

## Tests

### Unit

- Contract parsing and rejection of timing fields
- Error-envelope mapping
- Environment validation
- Session-storage fallback

### Integration

- Alembic upgrade from empty SQLite
- Repository behavior required by save, audio attach, and reads
- Constraints for stable IDs and content versions
- Song list/detail response shape
- Missing/unpublished song behavior
- Media URL does not reveal filesystem paths
- OpenAPI excludes `POST /api/import`

### Frontend

- Address rendering and the not-found page
- `/songs/new` and Learn Song render. `/import` does not.
- A failed song list or a failed song can be retried

### Build

- Type check, lint, backend static checks, frontend production build, and migration consistency run in CI.

## Sequencing

1. Freeze contracts and error shape.
2. Configure frontend/backend workspace and environment validation.
3. Create SQLAlchemy models and first Alembic revision.
4. Implement repository and read API skeletons.
5. Create the React shell, the app's own links, and the development feature boundary.
6. Add baseline tests and CI gates.

This feature blocks every other specification.

## Acceptance criteria

- `/`, `/songs/new`, and `/songs/:songId` resolve.
- `/import` does not resolve.
- The backend has no import mutation.
- Empty-database setup succeeds through Alembic only.
- All database access goes through SQLAlchemy.
- Song contracts contain ordered lines and no timing fields.
- Error responses use the shared safe envelope.
- App shell is keyboard navigable and route/not-found states are accessible.
- Configuration and media paths do not leak secrets/local filesystem details.
- CI gates pass.

## Risks

- The Groq key is copied into the frontend or the repository.
- SQLite-specific behavior leaks into repository code.
- Contract drift across backend/frontend.
- An overly broad app shell introduces unapproved screens or state.

Mitigate with production route tests, PostgreSQL-oriented portability review, generated/shared contract checks where practical, and scope review against the parent plan.

## Non-goals and deferred work

- Authentication/accounts
- PostgreSQL operation in Prototype 1
- Background jobs, queues, object storage, CDN, analytics
- User preferences persisted server-side
- Karaoke timing, timestamps, synchronization services
- A public multi-user host
