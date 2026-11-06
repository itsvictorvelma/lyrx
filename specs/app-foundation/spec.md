# Application foundation specification

Prototype 2.

Related features:

- [Song creation](../song-creation/spec.md)
- [Song Library](../song-library/spec.md)
- [Learn Song](../learn-song/spec.md)
- [Audio player](../audio-player/spec.md)

## Learner path

The learner already has a song. They open Lyrx, type the name, and get four documents: Original, Hiragana, Romaji, and English. Then they practice. One optional MP3 can play with those documents.

This install is local and has one learner. There is no account.

There is no catalog of pre-checked songs for the learner to pick from. A fixed song list may exist only as a developer test fixture, never as a screen.

The lyrics get the screen. Saved songs and a new search are a menu or a library section.

## Goal

Provide the local shell for that path: one search, four lyric documents, and one optional MP3, without accounts, line timing, or a public host.

## Scope

- React + TypeScript + Vite frontend
- Plain CSS in `frontend/src/index.css`
- The app's own links in `frontend/src/routes/`
- FastAPI backend
- SQLite accessed only through SQLAlchemy
- Alembic migrations
- Shared request/response/error contracts
- Local media filesystem and media delivery boundary
- One Swytchcode call to Groq for a lyric completion, with the key kept out of the app
- Baseline accessibility, test, lint, type-check, and build configuration

## Architecture

### Frontend shell

- One application shell owns the header and the screen for the current address.
- The header offers a new search and saved songs. That offer is a menu, or it opens the library section. It is not a column that stays beside the lyrics.
- The main region is the search, and then the lyrics. On a saved song, the four documents fill that region.
- Addresses are read and changed by the app's own links.
- Addresses:
  - `/`, `/search`, and `/songs/new` — the one search in [Song creation](../song-creation/spec.md). A valid result fills this screen with the four documents.
  - `/songs` — the [Song Library](../song-library/spec.md) section. Songs saved on this install. Not shown beside the lyrics.
  - `/songs/:songId` — [Learn Song](../learn-song/spec.md). The lyrics fill the screen.
- An unknown address shows a not-found state and a link back to the search.
- No authentication provider, account context, global server-state library, or timing engine.
- No screen renders a fixed list of songs. A fixture list stays in developer tests.

### Backend shell

- FastAPI application with:
  - `GET /api/health`
  - `GET /api/songs`
  - `GET /api/songs/{song_id}`
  - `POST /api/generations` — one search, not saved
  - `POST /api/songs` — save a valid draft
  - `POST /api/songs/{song_id}/audio` — attach or replace one MP3
  - The media URL when an MP3 is stored
- Validate configuration at startup and fail clearly on missing/unsafe values.
- Keep business validation independent of HTTP so generation and repository tests do not need a running server or a Groq call.

### Persistence

- SQLAlchemy owns models, sessions, and repository queries.
- SQLite database URL is environment configured.
- Alembic owns schema creation and evolution; application startup must not call `create_all`.
- The schema has only `tracks` and `lyric_versions`.
- Store aligned-line documents as schema-versioned JSON text after domain validation.
- Use dialect-portable identifiers, booleans, timestamps, constraints, and indexes.
- This install uses SQLite. PostgreSQL is out of scope.

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

The contract rejects timestamp/timing fields. Line indexes are unique and monotonic within a version. Indexes start at 0 and have no gaps.

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

The Groq key is not an application environment variable. Swytchcode injects it. There is no second model key.

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
- The header control that opens search or saved songs has a visible name and a visible focus style.
- Route changes move focus to the screen heading or an announced route target.
- Global errors use an accessible alert/status pattern.
- Not-found and failure screens contain keyboard-operable recovery actions.
- Plain CSS preserves visible focus and sufficient contrast.
- Responsive behavior does not reorder semantic reading order.
- A wide window and a narrow window both give the lyrics the screen. Width does not add a song column.

## Security

- No users, sessions, tokens, password code, or authorization roles.
- Learner-facing writes are one search, save, and one MP3 upload, on this install. A saved song is not rewritten by a later search.
- `POST /api/import` is not registered.
- Generated media paths prevent traversal and hide local paths.
- Lyric text renders as text, never raw HTML.
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

- `/` renders the search. It does not render a catalog of songs.
- `/songs` renders saved songs as a section, and that section is not a column beside the lyrics.
- `/songs/new` and `/search` render the same search as `/`.
- `/songs/:songId` renders the lyrics. `/import` does not.
- A failed song list or a failed song can be retried.
- No screen is built from a fixed song list. A developer test may use a fixture list.

### Build

- Type check, lint, backend static checks, frontend production build, and migration consistency run in CI.

## Acceptance criteria

- The app opens on the search. A valid result shows Original, Hiragana, Romaji, and English.
- `/songs` is saved songs only, and it is not a permanent sidebar.
- `/songs/:songId` fills the screen with the lyrics.
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
- The saved-song list returns as a column beside the lyrics.
- A fixture song list is wired up as a screen.
- Contract drift across backend and frontend.

## Out of scope

- Accounts and a public multi-user host
- A catalog of pre-checked songs
- A permanent sidebar of songs
- PostgreSQL
- Background jobs, queues, object storage, CDN, analytics
- User preferences persisted server-side
- Line timing and timestamps
- Spotify playback, lyric following from the clock, a second model, and LangChain or LangGraph. Those are stated in [Audio player](../audio-player/spec.md), [Learn Song](../learn-song/spec.md), and [Song creation](../song-creation/spec.md).
