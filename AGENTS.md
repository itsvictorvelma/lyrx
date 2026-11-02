---
cursor:
  subagentId: "bc-43f25a2f-93d8-5ec7-9282-d2774358e7bf"
---

# Lyrx Prototype 1 build plan

The code that exists today is explained in [docs/codebase.md](docs/codebase.md). This file is the product plan, not a description of the current code.

## Purpose

Build a small web application that helps one learner rehearse a Japanese song in one place. The learner asks for the lyrics in chat. The app shows the Japanese words, the hiragana reading, the romaji, and the direct English meaning, and can play an MP3 the learner attaches.

Prototype 1 runs as one local install. There is no login.

## Approved product scope

- Source language: Japanese.
- Support language: English.
- First tester: one learner on this machine.
- Primary job: pronunciation and performance practice.
- Supporting job: show the hiragana reading and the direct English meaning.
- No application authentication or accounts.
- Screens:
  1. Song Library — saved songs, a text filter, and a way to start a new song
  2. New song — chat that produces a lyric draft, then save, with an optional MP3
  3. Learn Song — the saved song, the same four documents, the player, and chat that can replace the lyrics
- A wide window reads Original, Hiragana, Romaji, and English as four documents. A narrow window uses tabs. There is no line timing, audio scan, current-line highlight, or tempo control.
- The only upload is one MP3. Lyric text files are not imported.

Feature specifications:

- [Application foundation](specs/app-foundation/spec.md)
- [Song creation](specs/song-creation/spec.md)
- [Song Library](specs/song-library/spec.md)
- [Learn Song](specs/learn-song/spec.md)
- [Audio player](specs/audio-player/spec.md)

## Non-negotiable user experience

Each lyric layer is one document, in this left-to-right order:

1. **Original** — Japanese as written
2. **Hiragana** — full reading
3. **Romaji** — pronunciation, not a translation
4. **English** — direct meaning

Lines stay in order inside a document. On a wide window the four columns keep their width and the page scrolls once. Hide and show sit in each column heading and fade that column's text only. On a narrow window, Original, Hiragana, Romaji, and English are tabs, and hiding text does not move the page.

Romaji is reader-friendly Hepburn-style Latin spelling of Japanese sounds. Hiragana is the reading of the original line, not a translation.

All four documents are open on a first visit. The choice lasts for the browser session and applies to every lyric unit. Any layer, including the last one, can be hidden.

The player is a compact bar stuck under the header while lyrics scroll. It contains only:

- Play/pause
- Continuous seek
- Elapsed time / duration
- Back 10 seconds / forward 10 seconds
- Volume / mute
- 0.75× / 1× / 1.25× playback rates

When no MP3 is attached, the player says so and does not pretend to load audio. Playback time does not highlight or scroll the lyrics.

Chat is how lyrics are created and replaced. One conversation is one song. The page shows the four documents from the model's structured reply. Save writes the song. The chat transcript is not stored.

## Technical architecture

### Frontend

- React + TypeScript + Vite
- Tailwind CSS
- One application shell
- Routes:
  - `/` — Song Library
  - `/songs/new` — new song
  - `/songs/:songId` — Learn Song
- Prefer component-local state and focused hooks. Do not add a global state package without a demonstrated cross-screen need.
- Store layer visibility in `sessionStorage`. Do not persist lyric text or chat in the browser beyond the unsaved page.
- An unsaved draft is lost on refresh.

### Backend and persistence

- Python + FastAPI
- SQLite for Prototype 1
- SQLAlchemy for all database access
- Alembic from the first schema revision
- Externally configured database URL
- PostgreSQL migration required before public multi-user or multi-instance operation
- Audio stored on the filesystem, never as a relational database blob
- Reverse proxy serves media over HTTPS with correct MIME type and byte-range support
- Lyric generation calls Groq through Swytchcode method `groq.chat.completions.create`. The Groq credential stays in the local Swytchcode connection.

### Runtime boundaries

- `GET /api/songs` — list saved songs
- `GET /api/songs/{song_id}` — fetch one song and its ordered lyric units
- `GET`/range request to the returned media URL when an MP3 exists
- `POST /api/generations` — one Groq completion, returns a validated draft
- `POST /api/songs` — save a draft
- `PUT /api/songs/{song_id}/lyrics` — replace saved lyrics
- `POST /api/songs/{song_id}/audio` — attach or replace one MP3

`POST /api/import` is not registered.

Generation and upload exist for this local install. Putting them on the public internet, in front of other people, is out of scope until there are accounts and a spend limit. The Groq key is never sent to the browser.

## Canonical contracts

### Song summary

- Stable `id`
- `title`
- `artist`
- `sourceLanguage`
- `targetLanguage`
- Optional `durationSeconds` after media inspection
- Publication status

A saved song is published.

### Song detail

- All Song summary fields
- `audioUrl` or null when no MP3 is stored
- Ordered `lines`
- Content/version identifier

### Lyric unit

- Stable `id` or, on an unsaved draft, a deterministic index-derived id
- Zero-based `index`
- `originalText`
- `readingHiragana`
- `pronunciationRomaji`
- `translationEnglish`

No timestamp, end time, active-line, `startSeconds`, or word/mora timing field is allowed.

### Generation

The request and the Groq call are specified in [Song creation](specs/song-creation/spec.md).

The free-plan budget for `openai/gpt-oss-120b` is 8,000 tokens per minute and 200,000 tokens per day. Prompt tokens and completion tokens both count. One user message is one completion. The server does not send the chat transcript. The measured call and the ceilings are recorded in [benchmarks/groq-token-usage.md](benchmarks/groq-token-usage.md).

### API error envelope

Use one documented error shape for API failures:

- Stable machine-readable error code
- Human-readable message
- Optional field/file/line details
- Request correlation identifier when available

Do not expose stack traces, filesystem paths, SQL, secrets, or Groq response bodies.

## Data model

Minimum entities:

- `tracks`
  - identity and display metadata
  - media object/path key and checksum, empty until an MP3 is stored
  - measured duration
  - publication status
- `lyric_versions`
  - track reference
  - source/target languages
  - schema version that requires `readingHiragana`
  - validated aligned-line JSON
  - provenance/status and creation metadata

Do not add users, sessions, credentials, roles, playlists, progress, timing, rights, or chat-transcript tables.

Use dialect-portable SQLAlchemy types and constraints. Avoid SQLite-specific queries and implicit behavior. Every schema change requires an Alembic revision and upgrade/downgrade review.

## Content rules

1. The model returns one JSON draft. The server validates it before the page treats it as lyrics.
2. Every stored line has all four texts. A blank layer on an otherwise filled line is rejected.
3. Empty songs and missing title or artist are rejected.
4. Indexes are `0`, `1`, `2`, and so on, with no gaps.
5. Hiragana is required. The learner hides the document on the reading screen when they do not want it.
6. Revisions replace the whole line list. The server does not merge a partial model reply into the old lines.
7. The MP3 is validated by signature, size, duration, and checksum. The storage name is generated.
8. Validate before committing. A failed lyric replace or audio replace leaves the previous saved bytes in place.
9. Lyric save and MP3 upload are separate requests. A failed upload can leave a saved song with no audio.

## Screen responsibilities

### Song Library

- List saved songs.
- Filter the loaded list by title and artist.
- Start a new song.
- Open Learn Song from a card.
- Provide loading, empty, no-match, and request-failure states.

### New song and lyric chat

- Specified in [Song creation](specs/song-creation/spec.md).
- Collect one message, show the four documents, save, and optionally hold one MP3 until save.
- On a saved song, the same composer replaces the lyrics after an explicit save.

### Learn Song

- Fetch Song detail.
- Render Original, Hiragana, Romaji, and English.
- On a wide window, hide and show each document from its heading.
- On a narrow window, switch documents with tabs.
- Host the sticky player without coupling playback time to lyrics.
- Host the chat composer specified for a saved song.
- Preserve manual scroll and visibility state during player actions.
- Provide loading, not-found, malformed-content, missing-audio, media-failure, and general request-failure states.

## Accessibility baseline

- Semantic headings, landmarks, lists, labels, and buttons.
- Logical tab order and visible focus indicators.
- Full keyboard operation for routes, chat, toggles, and player controls.
- Touch targets sized for mobile use.
- Controls expose names, values, pressed/muted state, and playback rate to assistive technology.
- Seek and volume controls have accessible value text.
- Status and validation messages are announced without moving focus unexpectedly.
- Japanese content has an appropriate language annotation. Hiragana uses Japanese. Romaji is labeled Romaji. English UI and the English document are separately identifiable.
- Reduced motion is respected.
- Sticky player never hides focused content and accounts for mobile safe areas.
- Do not rely on color alone for layer identity, state, or errors.

## Security and privacy

- No accounts, cookies for identity, or user profiles.
- The Groq key stays in the Swytchcode credential store. It is not in the frontend bundle, the repository, or API responses.
- Keep audio, generated lyrics, and databases out of Git.
- Use generated storage keys and prevent path traversal.
- Limit the audio upload to one file, MPEG audio, and a configurable size.
- Escape all generated text through normal React rendering. Never render it as HTML.
- Return generic server errors and log sensitive diagnostics only to restricted server logs.
- No analytics, voice capture, or third-party music, catalog, or lyrics APIs.
- No public multi-user deployment of generation or upload in this prototype.

## Error-state policy

Every asynchronous boundary must define:

- Loading state
- Empty/success state
- Recoverable error with retry
- Non-recoverable/validation error with corrective guidance
- Unknown error without leaked internals

Important cases:

- API unavailable or timeout
- Song not found
- Groq rate limit, oversized song, invalid draft, and missing credential
- Media URL missing because no MP3 is attached
- Unsupported or unreadable MP3, or range-request failure
- Malformed stored lyrics, including a line with no hiragana
- Database transaction or media-copy failure
- Invalid session-stored layer settings; fall back to all visible

## Test strategy

### Unit

- Draft validation and hiragana required
- Generation request builder, token cap, and `generation_too_large`
- Song publication on save
- SQLAlchemy repository behavior
- Player time formatting, seek clamping, mute, playback-rate transitions, and the no-audio state
- Layer visibility reducer and storage fallback for four layers

### Backend integration

- Alembic upgrade from empty database and downgrade review
- Save, lyric replace, and failed-write rollback
- MP3 attach, reject, and failed replace
- Song list and detail contracts
- `POST /api/import` is not registered
- Media URL and byte-range delivery
- SQLite tests use real SQLite, not a mock
- Default tests do not call Groq

### Frontend component

- Each screen's loading, success, empty, and error states
- Library filter
- Lyric order and the labels Original, Hiragana, Romaji, and English
- Layer toggles and session restoration
- Player controls, missing audio, and sticky layout
- Keyboard and accessible-name assertions

### End-to-end

1. Ask for a song, see four documents, save, and open it from the library.
2. Filter the library.
3. Revise a saved song and see the replacement after reload.
4. Attach a valid MP3 and reject an invalid one.
5. All player controls at normal and boundary positions, including no audio attached.
6. Toggle each layer and reload within the same session.
7. Responsive checks at narrow and wide viewports.
8. `/import` and `POST /api/import` are absent.
9. Automated accessibility scan plus manual keyboard smoke test.

## Build sequence

The foundation, the read API, the three-column reading screen, and the player already exist. The next work replaces lyric import with generation.

1. **Contracts** — `readingHiragana`, nullable audio, generation and save shapes, shared errors.
2. **Generation** — request builder, `POST /api/generations`, `/songs/new`, and save.
3. **Retire import** — remove `/import` and `POST /api/import` once save can create a song.
4. **Library** — filter and the new-song action.
5. **Audio attach** — MP3 upload and the player state when `audioUrl` is null.
6. **Revision** — chat on a saved song and `PUT /api/songs/{song_id}/lyrics`.
7. **Hardening** — accessibility, responsive four-column layout, and regression.

Do not start a dependent step until its contract checks are in tests. Default tests must not spend Groq tokens.

## Prototype acceptance

Prototype 1 is complete when:

- A learner can ask for a song and see Original, Hiragana, Romaji, and English from one structured Groq reply.
- An invalid or oversized reply creates no song and does not start a second completion.
- Save adds the song to the library. Search saved songs filters that list.
- The same chat can replace a saved song's lyrics after an explicit save.
- The learner can attach one MP3. The song remains readable with no audio.
- Learn Song shows the four documents side by side on a wide window and as tabs on a narrow window.
- Each layer can be hidden without moving the other columns, for the browser session.
- The sticky player supports the approved controls. Playback time does not highlight or scroll the lyrics.
- The app has no login, loop, autoplay, line timing, audio scan, word-level timing, microphone, lyric-file import, or public upload host.
- SQLite schema changes run only through Alembic, and application access uses SQLAlchemy.
- Required automated tests pass without calling Groq, and the manual accessibility and responsive checks pass.

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| The model returns valid JSON and wrong words | The learner reads the four documents, then saves. |
| A revision exceeds 8,000 tokens | The server refuses with `generation_too_large` and does not call Groq. |
| Swytchcode retries a 429 and the app retries too | One execution per send. The app does not start its own repair call. |
| Romaji or hiragana is read as the English meaning | Labels and order stay Original, Hiragana, Romaji, English. |
| Four columns do not fit a narrow window | Narrow windows use tabs. |
| Sticky player obscures lyrics or focus | Safe-area-aware layout and viewport tests. |
| The Groq key or an MP3 leaks into Git or the browser | Credential stays in Swytchcode. Generated storage names. Media and databases stay untracked. |
| SQLite assumptions block PostgreSQL | Dialect-portable SQLAlchemy, Alembic, external URL. |

## Explicitly deferred

- Line start times, audio scanning, current-line highlight, follow-scroll, word/mora timing, A/B looping, autoplay, or a tempo-based lyric pace
- Recording, microphone monitoring, pitch scoring, duet/live features
- Authentication, accounts, and a public multi-user host
- Stored chat transcripts and streaming token display
- Public uploads, remote administration, moderation, transcoding
- Catalog search, playlists, recommendations, sharing, social, payments, analytics
- YouTube/Spotify playback and lyrics-website or catalog APIs
- A second model provider, or a paid Groq tier
- PostgreSQL until preparation for public multi-user deployment
- Additional language pairs until the Japanese to English experience is validated

## Change control

This plan replaced developer import of three lyric files and one MP3. The learner now asks Groq for the four lyric layers, saves them locally, and attaches the MP3. That changes the earlier non-goals for machine-generated lyrics, a provider call, and learner-side writes. The writes are save, lyric replace, and one audio upload on this install. The Groq key and the recordings stay local.

Any further feature must identify:

1. The validated Prototype 1 learning it supports.
2. Which non-goal it changes.
3. New legal, security, or data implications.
4. Contract and migration impact.
5. Added tests and acceptance criteria.

Do not silently add deferred fields or inactive UI. Keep Prototype 1's contracts as small as its approved behavior.
