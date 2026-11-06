# Learn Song specification

Prototype 2.

Dependencies:

- [Application foundation](../app-foundation/spec.md)
- [Song Library](../song-library/spec.md)
- [Audio player](../audio-player/spec.md)
- [Song creation](../song-creation/spec.md)

## Goal

Let the learner practice a Japanese song on one reading screen. The screen shows four lyric documents: Original, Hiragana, Romaji, and English. The lyrics get the screen.

Hover or keyboard focus marks that line and the same index in the other visible documents. Playback time does not highlight a line and does not scroll the lyrics.

This screen reads a saved song. A later search does not rewrite it. Saving a song is specified in [Song creation](../song-creation/spec.md). The same four documents and the same line mark are used for a search result before it is saved.

## Route

- `/songs/:songId`
- Available without authentication.
- Reads one published Song detail from FastAPI.
- A saved song is not rewritten by a later search.
- The screen does not include a column of saved songs. Saved songs and a new search are the header menu or the library section.

## Song detail contract

Required:

- Song ID
- Title
- Artist
- Source/target languages
- `audioUrl`, or null when no MP3 is attached
- Content version
- Ordered lyric units

Each lyric unit:

- Stable ID
- Monotonic index, starting at 0 with no gaps
- `originalText`
- `readingHiragana`
- `pronunciationRomaji`
- `translationEnglish`

Reject or fail safely when line IDs or indexes are duplicate or non-monotonic, or when original, romaji, or English text is absent. A missing hiragana reading does not fail the song. When every line lacks hiragana, that column says nothing is there yet. Timing fields, including `startSeconds`, are rejected.

## Layout

Colors, type, and spacing come from `frontend/src/index.css`. Surfaces stay quiet: no boxed lyric cards, row stripes, or heavy buttons.

The lyrics fill the screen. Order on this screen:

1. Song title and artist
2. [Compact audio player](../audio-player/spec.md)
3. The four lyric documents

A new search and saved songs stay in the header menu, or in the library section. They are not a column on this screen.

Each document, left to right:

1. **Original** — strongest, Japanese text
2. **Hiragana** — the reading, same language as the original, quieter than the original
3. **Romaji** — medium, pronunciation
4. **English** — same reading size as romaji, slightly muted

Lines stay in index order inside each document. There are no cells, row stripes, or per-line labels. A wide window shows the open documents side by side and the page scrolls once. A narrow window shows one document, chosen with Original, Hiragana, Romaji, and English tabs. Responsive design may change max width, padding, and type scale, but it does not reorder the documents and it does not add a song column.

## Line mark

Hover or keyboard focus marks that line. The same index is marked in every other visible document. A hidden document is not marked. A narrow window has one visible document, so the mark stays on that line.

The mark follows the pointer and keyboard focus. It does not follow playback time. Playback does not scroll the page to a line.

A visible line can take keyboard focus, so the mark has a keyboard path.

## Layer visibility

Wide-window controls live in the column headings:

- Original
- Hiragana
- Romaji
- English

Each heading shows Hide when that document's text is visible and Show when it is hidden. Hiding fades the text over about 200ms and leaves the column width, heading, and line positions unchanged. The other columns do not reflow. `prefers-reduced-motion` removes the fade. Hidden text is not selectable and is removed from the accessibility tree. A hidden document is not a visible document for the line mark.

Narrow-window controls are tabs with those same four names, plus Hide or Show for the selected document. One tab is selected, so one document is on screen. Hiding its text does not change scroll position or layout. Choosing a tab does not erase another layer's visibility.

Rules:

- All four are visible on first visit/default.
- Layer visibility is stored under `lyrx.layers.v2` as four booleans. An older or invalid value falls back to all visible.
- The choice applies to every lyric unit.
- Any layer can be hidden, including the last one.
- Persist only in browser `sessionStorage`.
- Storage is namespaced/versioned and validated on read.
- Invalid/unavailable storage falls back to all visible.
- Toggling does not alter source data, line order, scroll position, column geometry, or player state.
- The button says Hide or Show, exposes `aria-pressed`, and has a visible keyboard focus style.

## Player relationship

- The player plays the attached MP3. It does not choose, highlight, or scroll a lyric line.
- Playback time is not an input to the line mark.
- There is no tempo, beats-per-line, line loop, line timing, or word timing.
- The player stays reachable while the lyrics scroll and does not cover focused lyric content.
- With no MP3, the song stays readable. The player state is specified in [Audio player](../audio-player/spec.md).

## State and error behavior

### Loading

- Keep route/screen heading structure stable.
- Show song/player/lyrics loading status.

### Success

- Render every validated lyric unit once in index order.
- Do not infer or generate missing layers.

### Not found/unpublished

- Explain that the song is unavailable.
- Offer the search and Song Library. Do not leave the learner on a blank screen.

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

- Treat an empty line list as invalid stored content, not a normal empty state.
- A line missing hiragana still opens. When every line lacks hiragana, that column says nothing is there yet.

## Accessibility

- Main heading includes song title.
- Lyrics are four documents. Visible headings and tabs read Original, Hiragana, Romaji, and English.
- On a wide window, hiding text does not collapse the column. The four columns keep their width.
- Japanese text and hiragana use Japanese language annotation.
- English interface text and the English document use English annotation.
- Romaji is labeled Romaji. English is the translation document.
- Hide, Show, and tab controls expose pressed or selected state and have visible focus.
- The line mark is reachable from the keyboard.
- The player does not obscure focused lyric text at 200% and 400% zoom.
- Reading order is the first pane from top to bottom, then the next pane.
- Typography and spacing remain legible for Japanese characters and Latin text.
- No color-only distinctions.

## Responsive behavior

- Narrow: Original, Hiragana, Romaji, and English tabs. One document is visible. The player stays with the song. No song column.
- Medium/wide: centered readable measure. The open documents share the width and the page scrolls once. There is no nested lyric scrollbar and no song column.
- The player occupies space with the song, so it does not cover the lyrics.
- Long Japanese, hiragana, romaji, and English strings wrap rather than clip.
- The page does not gain a horizontal scrollbar.
- Toggling layers does not produce large unexpected layout/focus jumps.

## Security and privacy

- No account. The write on this screen is attaching one MP3, specified in [Song creation](../song-creation/spec.md). A later search does not replace the saved lines.
- Generated text renders as plain escaped content.
- No analytics, recording, microphone, or personal data.
- No internal paths in the response.
- Only publishable content resolves in production.
- Session storage contains only four booleans and the schema version, no song text.

## Tests

### Unit/component

- Correct document order and the labels Original, Hiragana, Romaji, and English
- API order retained
- Duplicate, non-monotonic, or missing line rejection
- Toggle each layer
- Any layer, including the last one, can be hidden
- Session persistence and invalid-storage fallback
- Hover marks that line and the same index in the other visible documents
- Keyboard focus marks that line and the same index in the other visible documents
- A hidden document is not marked
- With one visible document, the mark stays on that line
- Player time updates do not mark a line or change scroll position
- Player actions do not mutate visibility
- Loading, not-found, API, malformed, and media errors
- The screen does not render a saved-song column

### Accessibility

- Heading, list, and group semantics
- Language annotations
- Toggle names, states, and focus
- Keyboard-only layer operation and keyboard line mark
- Automated scan and manual screen-reader smoke

### Responsive

- Narrow, medium, and wide viewports
- 200% and 400% zoom
- Long content wrapping
- Player content offset
- All layer-visibility combinations
- No song column at any width

### End-to-end

1. Open a saved song from the library section.
2. Confirm the four documents fill the screen, in order, without a table grid and without a song column.
3. Hide and show each document's text without moving the columns or the scroll position.
4. Navigate back or reload within the session and restore visibility.
5. Hover a line and confirm the same index is marked in the other visible documents. Repeat with keyboard focus.
6. Exercise the player and confirm playback time does not highlight a line or scroll the lyrics. There is no tempo control.

## Acceptance criteria

- A publishable song opens directly by URL without login.
- The lyrics fill the screen. Saved songs are not a permanent sidebar.
- Every saved line is shown once, in order, inside each visible document.
- Labels are Original, Hiragana, Romaji, and English.
- Hover and keyboard focus mark that line and the same index in the other visible documents.
- All four toggles hide or show text without reflow, including when every layer is hidden.
- Toggle state survives within the browser session only.
- The player remains reachable and independent of the lyrics.
- Playback time does not highlight or scroll the lyrics.
- Manual scroll survives player actions.
- Loading, unavailable, malformed, API, and media failures are understandable and recoverable as applicable.
- The screen meets keyboard, language, focus, zoom, wrapping, contrast, and player-offset requirements.
- There is no line timing, tempo control, word timing, or loop.

## Risks

- Romaji can be read as the English. The labels are Romaji and English.
- A narrow layout can squeeze four documents onto one screen. Narrow widths use tabs.
- The player can cover content or focus.
- Hiding a document can shift the other columns or the scroll position.
- A playback clock can be wired to the line mark.

## Out of scope

- Lyric following from the clock
- Line start times, audio scanning, tempo pacing, word or mora timing, and line looping
- Word or mora segmentation
- Editing saved lines from this screen
- Saved progress, favorites, and history
- Authentication and private songs
- Recording, pitch, microphone, and scoring
- A stored search transcript
- A permanent sidebar
- Spotify playback. That is specified in [Audio player](../audio-player/spec.md).
