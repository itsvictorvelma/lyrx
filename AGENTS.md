---
cursor:
  subagentId: "bc-43f25a2f-93d8-5ec7-9282-d2774358e7bf"
---

# Lyrx Prototype 1 build plan

The code that exists today is explained in [docs/codebase.md](docs/codebase.md). This file is the product plan, not a description of the current code.

## Purpose

Build a small web application that helps one learner rehearse a Japanese song for karaoke without switching between an audio player, Japanese lyrics, romaji, and English meaning.

Prototype 1 uses “Akuma no Ko” by Ai Higuchi as the working local-development song. Public deployment is prohibited until the recording, composition/lyrics, romaji adaptation, and English translation have documented permission for the intended use.

## Approved product scope

- Source language: Japanese.
- Support language: English.
- First tester: A learner.
- Primary job: pronunciation and performance practice.
- Supporting job: show direct English meaning as context.
- No application authentication or accounts.
- Three screens only:
  1. Song Library
  2. Import Song, available only in local development
  3. Learn Song
- No lyric synchronization in Prototype 1.

Feature specifications:

- [Application foundation](specs/app-foundation/spec.md)
- [Developer song import](specs/content-import/spec.md)
- [Song Library](specs/song-library/spec.md)
- [Learn Song](specs/learn-song/spec.md)
- [Audio player](specs/audio-player/spec.md)

## Non-negotiable user experience

Each lyric unit is ordered and vertically stacked at every breakpoint:

1. **Japanese**
2. **Pronunciation (Romaji)**
3. **Direct Meaning**

Pronunciation (Romaji) is reader-friendly Hepburn-style Latin spelling of Japanese sounds. It is not an English translation.

Learn Song has one global visibility toggle for each layer. All layers are visible initially. Toggle state lasts for the browser session, applies to every lyric unit, and must leave at least one layer visible.

The player stays reachable while lyrics scroll and contains only:

- Play/pause
- Continuous seek
- Elapsed time / duration
- Back 10 seconds / forward 10 seconds
- Volume / mute
- 0.75× / 1× / 1.25× playback rates

## Technical architecture

### Frontend

- React + TypeScript + Vite
- Tailwind CSS
- React Router
- One application shell
- Routes:
  - `/` — Song Library
  - `/import` — Import Song; development builds only
  - `/songs/:songId` — Learn Song
- Prefer component-local state and focused hooks. Do not add a global state package without a demonstrated cross-screen need.
- Store layer visibility in `sessionStorage`; do not persist user data server-side.

### Backend and persistence

- Python + FastAPI
- SQLite for Prototype 1
- SQLAlchemy for all database access
- Alembic from the first schema revision
- Externally configured database URL
- PostgreSQL migration required before public multi-user or multi-instance operation
- Audio stored on the filesystem, never as a relational database blob
- Reverse proxy serves media over HTTPS with correct MIME type and byte-range support

### Runtime boundaries

Public/runtime operations:

- `GET /api/songs` — list publishable songs
- `GET /api/songs/{song_id}` — fetch one song and its ordered lyric units
- `GET`/range request to the returned media URL

Development-only operation:

- Bundle import mutation used by Import Song
- The frontend route and backend mutation must both be absent or unregistered in production
- Client-side hiding alone is not a security boundary
- Development import service binds to localhost

No other public write API exists.

## Canonical contracts

### Song summary

- Stable `id`
- `title`
- `artist`
- `sourceLanguage`
- `targetLanguage`
- Optional duration after media inspection
- Publication status

### Song detail

- All Song summary fields
- `audioUrl`
- Ordered `lines`
- Content/version identifier

### Lyric unit

- Stable `id` or deterministic index-derived identifier
- Zero- or one-based `index`, chosen once and documented
- `originalText`
- `pronunciationRomaji`
- `translationEnglish`

No timestamp, start/end, active-line, or word/mora timing field is allowed in the Prototype 1 contract.

### Import bundle

Required files, named exactly:

```text
original.txt
pronunciation.txt
translation.txt
audio.mp3
```

Required form metadata:

- Stable song ID/slug
- Title
- Artist
- Source language
- Target language
- Exact recording/release notes
- Attribution
- Rights status
- Rights evidence reference

The three text files align strictly by line index.

### API error envelope

Use one documented error shape for API failures:

- Stable machine-readable error code
- Human-readable message
- Optional field/file/line details
- Request correlation identifier when available

Do not expose stack traces, filesystem paths, SQL, or secrets.

## Data model

Minimum entities:

- `tracks`
  - identity and display metadata
  - media object/path key and checksum
  - measured duration
  - rights and publication status
- `lyric_versions`
  - track reference
  - source/target languages
  - schema version
  - validated aligned-line JSON
  - provenance/status and creation metadata
- `rights_records`
  - asset type
  - source/rightsholder
  - permitted use and territory
  - effective/expiry dates
  - evidence reference

Do not add users, sessions, credentials, roles, playlists, progress, or timing tables.

Use dialect-portable SQLAlchemy types and constraints. Avoid SQLite-specific queries and implicit behavior. Every schema change requires an Alembic revision and upgrade/downgrade review.

## Content and import rules

1. Decode text as UTF-8; handle or reject BOM consistently.
2. Normalize CRLF/CR to LF before comparing.
3. Define terminal-newline handling once so editors do not create false mismatches.
4. All three files must have identical line counts after normalization.
5. A row may be blank only if all three corresponding rows are blank; omit fully blank separator rows from stored lyric units.
6. Reject any partially blank row.
7. Reject empty songs and missing required metadata.
8. Validate that `audio.mp3` is a readable MP3; do not trust extension or browser MIME alone.
9. Measure duration and calculate a cryptographic checksum.
10. Generate server-owned storage names; never use an uploaded path directly.
11. Validate everything before committing. Database and media writes must appear atomic; failures clean up temporary files.
12. Re-import is idempotent for the same song ID/content version. A materially different bundle requires explicit replacement confirmation in development.
13. A song cannot become publishable unless bundle validation and the rights gate both pass.

## Screen responsibilities

### Song Library

- Fetch and display publishable song summaries.
- For Prototype 1, a one-card library is acceptable.
- Route song selection to Learn Song.
- Show Import Song navigation only in development.
- Provide loading, empty, request-failure, and unavailable-song states.

### Import Song

- Development only.
- Collect the exact four-file bundle and metadata.
- Validate before mutation where practical, then rely on authoritative server validation.
- Present file/field/line-specific errors.
- Show a three-layer aligned preview after success.
- Return to Song Library after explicit completion.
- It is not a text editor, rights-management system, or public upload feature.

### Learn Song

- Fetch Song detail.
- Render responsive, vertically stacked lyric units.
- Provide the three global layer toggles.
- Host the sticky player without coupling playback time to lyrics.
- Preserve manual scroll and visibility state during player actions.
- Provide loading, not-found, malformed-content, media-failure, and general request-failure states.

## Accessibility baseline

- Semantic headings, landmarks, lists, labels, and buttons.
- Logical tab order and visible focus indicators.
- Full keyboard operation for routes, toggles, and player controls.
- Touch targets sized for mobile use.
- Controls expose names, values, pressed/muted state, and playback rate to assistive technology.
- Seek and volume controls have accessible value text.
- Status and validation messages are announced without moving focus unexpectedly.
- Error summaries link/focus the relevant field where possible.
- Japanese content has an appropriate language annotation; English UI/meaning is separately identifiable.
- Reduced motion is respected.
- Sticky player never hides focused content and accounts for mobile safe areas.
- Do not rely on color alone for layer identity, state, or errors.

## Security and privacy

- No accounts, cookies for identity, tokens, or user profiles.
- No learner-side writes.
- Import route and endpoint are not registered in production.
- Development import binds to localhost and validates origin/request size.
- Keep commercial audio, lyrics, rights evidence, and generated databases out of Git and container images unless explicitly approved.
- Store rights evidence outside publicly served directories.
- Use generated storage keys and prevent path traversal.
- Limit accepted file count, file type, and configurable file size.
- Escape all imported text through normal React rendering; never render imported HTML.
- Return generic server errors and log sensitive diagnostics only to restricted server logs.
- Public media and text require documented rights. Possession of files is not permission.
- No analytics, voice capture, personal data, or third-party music/catalog APIs.

## Error-state policy

Every asynchronous boundary must define:

- Loading state
- Empty/success state
- Recoverable error with retry
- Non-recoverable/validation error with corrective guidance
- Unknown error without leaked internals

Important cases:

- API unavailable or timeout
- Song not found/unpublished
- Media URL missing, unsupported, or range request failure
- MP3 metadata/duration not yet available
- Import filename or file-count errors
- Text encoding and line-count mismatch
- Partial blank rows
- Duplicate ID/version conflict
- Database transaction or media-copy failure
- Invalid session-stored layer settings; fall back to all visible

## Test strategy

### Unit

- Text normalization and aligned-line construction
- Blank-row behavior
- Import validation and error mapping
- Song publication rules
- SQLAlchemy repository behavior
- Player time formatting, seek clamping, mute, and playback-rate transitions
- Layer visibility reducer/storage fallback

### Backend integration

- Alembic upgrade from empty database and downgrade review
- Import atomicity and cleanup
- Idempotent re-import and conflict behavior
- Song list/detail contracts and publication filtering
- Production build has no import endpoint
- Media URL and byte-range delivery
- SQLite tests use real SQLite, not a mock

### Frontend component

- Each screen's loading, success, empty, and error states
- Import form field/file validation
- Lyric unit order and exact labels
- Layer toggles, at-least-one rule, and session restoration
- Player controls and sticky layout
- Keyboard and accessible-name assertions

### End-to-end

1. Development import of a valid bundle through Learn Song.
2. Rejection of mismatched line counts with no partial record/file.
3. Song Library → Learn Song navigation.
4. All player controls at normal and boundary positions.
5. Toggle each layer and reload within the same session.
6. Responsive checks at narrow, medium, and wide viewports.
7. Production configuration exposes no Import Song route or mutation.
8. Automated accessibility scan plus manual keyboard/screen-reader smoke test.

## Build sequence

1. **Foundation**
   - Repository layout and environment configuration
   - FastAPI health/read API skeleton
   - React/Vite/Tailwind/Router shell
   - SQLAlchemy models and first Alembic migration
   - Shared contracts and error shape
2. **Import path**
   - Normalization/validation domain logic
   - Atomic media/database import
   - Development-only endpoint and Import Song screen
3. **Read path**
   - Song list/detail repositories and endpoints
   - Song Library states and routing
4. **Learning experience**
   - Learn Song lyric units and layer toggles
   - Sticky audio player and exact controls
5. **Hardening**
   - Accessibility
   - Responsive behavior
   - Production import exclusion
   - Rights/publication gate
   - Full regression and deployment smoke tests

Do not start a dependent phase until its contracts and validation rules are covered by tests. Import and app-shell work may proceed in parallel after shared contracts are frozen; Learn Song and Audio Player may proceed in parallel after Song detail is frozen.

## Prototype acceptance

Prototype 1 is complete when:

- A valid four-file bundle imports atomically in development.
- Misaligned or invalid bundles are rejected with actionable errors and no partial state.
- Song Library lists the approved imported song and routes to Learn Song.
- Learn Song always stacks Japanese, Pronunciation (Romaji), and Direct Meaning in line order at every breakpoint.
- Each layer can be hidden/shown globally, at least one remains visible, and state lasts for the session.
- The sticky player supports the exact approved controls, remains accessible and unobtrusive, and never drives lyric state.
- The app has no login, learner write, karaoke tracking, line seek, loop, autoplay, automation, provider API, or public upload.
- Production does not register Import Song or its mutation.
- SQLite schema creation/upgrades run only through Alembic and application access uses SQLAlchemy.
- Rights provenance exists before any public song publication.
- Required automated tests and manual accessibility/responsive smoke tests pass.

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| Commercial content is exposed without permission | Rights status defaults to non-public; public release requires evidence review. |
| Three files silently drift out of alignment | Strict line-count/index validation and three-layer preview. |
| Romaji is mistaken for translation | Exact Pronunciation (Romaji) label, fixed stack order, linguistic review. |
| Sticky player obscures lyrics or focus | Safe-area-aware responsive layout and viewport/focus tests. |
| Development import leaks into production | Compile/runtime route guard plus backend route absence test. |
| SQLite assumptions block PostgreSQL | Dialect-portable SQLAlchemy, Alembic, external URL, regression suite. |
| Browser media behavior varies | Standard MP3, user-gesture start, boundary and target-browser tests. |
| Scope expands into karaoke platform work | Enforce non-goals and reject timing fields/features in review. |

## Explicitly deferred

- Karaoke tracking or current-line highlighting
- Any lyric timestamps, timing editor, forced alignment, word/mora timing, or sync offset
- Line seek, A/B/line looping, autoplay, or automated scrolling
- Recording, microphone monitoring, pitch scoring, duet/live features
- Authentication, accounts, saved learner progress, private libraries
- Public uploads, remote administration, moderation, transcoding pipeline
- Search, playlists, recommendations, sharing, social, payments, analytics
- YouTube/Spotify playback and provider/catalog/lyrics APIs
- Machine-generated romaji or translation
- PostgreSQL until preparation for public multi-user deployment
- Additional language pairs until the Japanese→English experience is validated

## Change control

Any proposed feature outside this plan must identify:

1. The validated Prototype 1 learning it supports.
2. Which non-goal it changes.
3. New legal/security/data implications.
4. Contract and migration impact.
5. Added tests and acceptance criteria.

Do not silently add deferred fields or inactive UI “for later.” Keep Prototype 1's contracts as small as its approved behavior.
