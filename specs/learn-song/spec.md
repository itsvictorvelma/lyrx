---
cursor:
  subagentId: "bc-43f25a2f-93d8-5ec7-9282-d2774358e7bf"
---

# Learn Song specification

Parent plan: [Prototype 1 build plan](../../AGENTS.md)

Dependencies:

- [Application foundation](../app-foundation/spec.md)
- [Song Library](../song-library/spec.md)
- [Audio player](../audio-player/spec.md)
- [Developer song import](../content-import/spec.md)

## Goal

Let a learner rehearse a Japanese song using one screen that combines audio with three lyric documents: Original, Pronunciation (Romaji), and Direct English.

## Route

- `/songs/:songId`
- Available without authentication.
- Reads one publishable Song detail from FastAPI.
- Development may preview a draft only through an explicit development-safe mechanism; production never fetches unpublished content.

## Song detail contract

Required:

- Song ID
- Title
- Artist
- Source/target languages
- Audio URL
- Content version
- Ordered lyric units

Each lyric unit:

- Stable ID
- Monotonic index
- `originalText`
- `pronunciationRomaji`
- `translationEnglish`

Reject or fail safely when line IDs/indexes are duplicate/non-monotonic or required text is absent. Timing fields, including `startSeconds`, are rejected. There is no current-line highlight and no tempo control.

## Layout

Order:

1. Back link to Song Library
2. Song title/artist and language direction
3. Layer visibility controls
4. [Sticky audio player](../audio-player/spec.md)
5. Ordered lyric units

Each layer is one document pane, left to right:

1. **Original** — visually primary, Japanese text
2. **Pronunciation (Romaji)** — prominent pronunciation aid
3. **Direct English** — visually secondary context

Lines stay in index order inside each pane. There are no cells, row stripes, or per-line labels. A narrow screen keeps the panes side by side and snaps sideways from one document to the next. A wide screen lets the visible panes share the row. Responsive design may change max width, padding, type scale, and sticky-player placement, but does not stack the three documents or reorder them.

## Layer visibility

Controls:

- Original
- Pronunciation (Romaji)
- Direct English

Rules:

- All three are visible on first visit/default.
- Toggle choice applies to every lyric unit.
- At least one layer must remain visible.
- Persist only in browser `sessionStorage`.
- Storage is namespaced/versioned and validated on read.
- Invalid/unavailable storage falls back to all visible.
- Toggling does not alter source data, line order, scroll position, or player state.
- The UI communicates hidden/visible state without color alone.

Recommended handling when one layer remains:

- Disable the final visible layer's “hide” action or reject it with an immediate accessible explanation.

## Player relationship

- The player plays the song. It does not choose, highlight, or scroll a lyric line.
- There is no tempo, beats-per-line, line loop, line timing, or word timing.
- The player stays reachable while the lyrics scroll but must not cover focused lyric content.

## State and error behavior

### Loading

- Keep route/screen heading structure stable.
- Show song/player/lyrics loading status.

### Success

- Render every validated lyric unit once in index order.
- Do not infer or generate missing layers.

### Not found/unpublished

- Explain that the song is unavailable.
- Link back to Song Library.

### API failure

- Show safe error and retry.
- Do not discard valid session layer preferences.

### Malformed content

- Fail the lyric region safely instead of displaying misaligned rows.
- Show a user-safe unavailable-content message.
- Log song/version and validation code, not the full lyric text by default.

### Media failure

- Lyrics may remain readable.
- Audio player shows its own recoverable/unavailable state.

### Empty lyric set

- Treat as invalid imported content, not a normal public empty state.

## Accessibility

- Main heading includes song title.
- Lyrics are three documents. Each pane has a heading: Original, Pronunciation (Romaji), or Direct English.
- Hidden panes are omitted so the remaining documents share the width.
- Japanese text uses Japanese language annotation.
- English interface and Direct English use English annotation.
- Romaji is labeled Pronunciation (Romaji), never just “English.” Direct English is the translation pane.
- Toggle controls expose pressed state and have visible focus.
- Sticky player does not obscure focused lyric text at 200%/400% zoom.
- Reading order is the first pane from top to bottom, then the next pane.
- Typography and spacing remain legible for Japanese characters and Latin text.
- No color-only distinctions.

## Responsive behavior

- Narrow: safe-area-aware player placement; the panes stay side by side and the sheet snaps sideways.
- Medium/wide: centered readable measure; the visible panes share the width.
- Reserve/offset content space for the sticky player.
- Long Japanese/romaji/meaning strings wrap rather than clip.
- High zoom may scroll the lyric sheet sideways. The rest of the page does not gain a second horizontal scrollbar.
- Toggling layers does not produce large unexpected layout/focus jumps.

## Security and privacy

- No account or learner write.
- Imported text renders as plain escaped content.
- No analytics, recording, microphone, or personal data.
- No internal paths in the response.
- Only publishable content resolves in production.
- Session storage contains only three booleans/schema version, no song text.

## Tests

### Unit/component

- Correct pane order and exact labels
- API order retained
- Duplicate/non-monotonic/missing line rejection
- Toggle each layer
- At-least-one-visible invariant
- Session persistence and invalid-storage fallback
- Player actions do not mutate visibility/scroll state
- Loading/not-found/API/malformed/media errors

### Accessibility

- Heading/list/group semantics
- Language annotations
- Toggle names/states/focus
- Keyboard-only layer operation
- Automated scan and manual screen-reader smoke

### Responsive

- Narrow, medium, and wide viewports
- 200% and 400% zoom
- Long content wrapping
- Sticky-player content offset
- All layer-visibility combinations

### End-to-end

1. Navigate from Song Library to Learn Song.
2. Confirm all three panes are visible, in order, without a table grid.
3. Hide/show each layer and enforce at least one.
4. Navigate/back or reload within session and restore visibility.
5. Exercise player controls without changing lyric state.
6. Exercise the player and confirm it does not highlight or scroll a line. There is no tempo control.

## Sequencing

1. Freeze Song detail/line contract.
2. Build data validation and screen states.
3. Build the three lyric documents.
4. Add layer controls and session persistence.
5. Integrate Audio Player without line highlighting or follow-scroll.
6. Complete accessibility and responsive tests.

Can proceed in parallel with Audio Player once its layout envelope and event contract are frozen.

## Acceptance criteria

- A publishable song opens directly by URL without login.
- Every imported line is shown once, in order, inside each visible pane.
- Labels are exactly Original, Pronunciation (Romaji), and Direct English.
- All three toggles work globally; at least one remains visible.
- Toggle state survives within the browser session only.
- Player remains reachable and independent of lyrics.
- Manual scroll survives player actions.
- Loading, unavailable, malformed, API, and media failures are understandable/recoverable as applicable.
- Screen meets keyboard, language, focus, zoom, wrapping, contrast, and sticky-content requirements.
- There is no line timing, current-line highlight, follow-scroll, tempo control, word timing, or loop.

## Risks

- Romaji appears to be an English translation.
- A narrow layout stacks the three documents into one scrolling page.
- Sticky player covers content/focus.
- Session state creates a blank screen if all layers become hidden.
- Malformed persisted/imported data silently misaligns meaning.

Mitigate with exact labels/order, side-by-side panes at every width, offset/zoom tests, at-least-one invariant, and runtime contract validation.

## Non-goals and deferred work

- Line start times, audio scanning, current-line highlight, follow-scroll, or tempo pacing
- Word/mora timing, line/A-B loop
- Word/mora segmentation
- Editing or reporting content
- Saved progress/favorites/history
- Authentication/private songs
- Recording, pitch, microphone, scoring
- Machine translation/romaji
