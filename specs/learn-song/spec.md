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

Let a learner rehearse a Japanese song using one screen that combines audio with line-aligned Japanese, reader-friendly romaji pronunciation, and direct English meaning.

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

Reject or fail safely when line IDs/indexes are duplicate/non-monotonic or required text is absent. Each line may include `startSeconds`. The screen highlights that line and can scroll to it. There is no tempo control.

## Layout

Order:

1. Back link to Song Library
2. Song title/artist and language direction
3. Layer visibility controls
4. [Sticky audio player](../audio-player/spec.md)
5. Ordered lyric units

Each lyric unit always stacks:

1. **Japanese** — visually primary
2. **Pronunciation (Romaji)** — prominent pronunciation aid
3. **Direct Meaning** — visually secondary context

The unit remains vertically stacked at all widths. Responsive design may change max width, padding, type scale, and sticky-player placement, but never converts layers to columns or reorders them.

## Layer visibility

Controls:

- Japanese
- Pronunciation (Romaji)
- Direct Meaning

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

- The player reports the playhead. Learn Song chooses the current line from `startSeconds`.
- Follow scrolls the current line into view. Scrolling by hand turns follow off.
- A line can be stamped to the playhead, and a saved start can seek the player.
- There is no tempo, beats-per-line, line loop, or word timing.
- The player stays reachable while the list scrolls but must not cover focused/currently read lyric content.

## State and error behavior

### Loading

- Keep route/screen heading structure stable.
- Show song/player/lyrics loading status without a fake active lyric.

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
- Lyrics are a semantic ordered list.
- Each lyric unit is a grouped list item with layer labels available to assistive technology.
- Japanese text uses Japanese language annotation.
- English interface/Direct Meaning use English annotation.
- Romaji is labeled Pronunciation (Romaji), never just “English.”
- Toggle controls expose pressed/checked state and have visible focus.
- Sticky player does not obscure focused lyric units at 200%/400% zoom.
- Reading order follows visual stack.
- Typography and spacing remain legible for Japanese characters and Latin text.
- No color-only distinctions.

## Responsive behavior

- Narrow: safe-area-aware player placement; one stacked unit per row.
- Medium/wide: centered readable measure; layers remain stacked.
- Reserve/offset content space for the sticky player.
- Long Japanese/romaji/meaning strings wrap rather than clip.
- High zoom does not create horizontal page scroll.
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

- Correct stack order and exact labels
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
2. Confirm all three layers are visible and stacked.
3. Hide/show each layer and enforce at least one.
4. Navigate/back or reload within session and restore visibility.
5. Exercise player controls without changing lyric state.
6. Scan or stamp a line, then confirm follow highlights that line. There is no tempo control.

## Sequencing

1. Freeze Song detail/line contract.
2. Build data validation and screen states.
3. Build stacked LyricUnit and ordered viewport.
4. Add layer controls and session persistence.
5. Integrate Audio Player without timeline coupling.
6. Complete accessibility and responsive tests.

Can proceed in parallel with Audio Player once its layout envelope and event contract are frozen.

## Acceptance criteria

- A publishable song opens directly by URL without login.
- Every imported line is shown once, in order, as a vertically stacked unit.
- Labels are exactly Japanese, Pronunciation (Romaji), and Direct Meaning.
- All three toggles work globally; at least one remains visible.
- Toggle state survives within the browser session only.
- Player remains reachable and independent of lyrics.
- Manual scroll survives player actions.
- Loading, unavailable, malformed, API, and media failures are understandable/recoverable as applicable.
- Screen meets keyboard, language, focus, zoom, wrapping, contrast, and sticky-content requirements.
- Line start times highlight and follow the current line. There is no tempo control, word timing, or loop.

## Risks

- Romaji appears to be an English translation.
- Responsive design turns aligned units into ambiguous columns.
- Sticky player covers content/focus.
- Session state creates a blank screen if all layers become hidden.
- Malformed persisted/imported data silently misaligns meaning.

Mitigate with exact labels/order, always-stacked contract, offset/zoom tests, at-least-one invariant, and runtime contract validation.

## Non-goals and deferred work

- Tempo or beats-per-line pacing
- Word/mora timing, line/A-B loop
- Word/mora segmentation
- Editing or reporting content
- Saved progress/favorites/history
- Authentication/private songs
- Recording, pitch, microphone, scoring
- Machine translation/romaji
