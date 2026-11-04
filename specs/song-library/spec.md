---
cursor:
  subagentId: "bc-43f25a2f-93d8-5ec7-9282-d2774358e7bf"
---

# Song Library specification

Parent plan: [Prototype 1 build plan](../../AGENTS.md)

Dependencies and destinations:

- [Application foundation](../app-foundation/spec.md)
- [Song creation](../song-creation/spec.md)
- [Learn Song](../learn-song/spec.md)

## Goal

Open on the songs this install has saved. Filter that list by title or artist, and start a new song from here.

The list is not a catalog of music the learner has not saved. A song appears after save.

## Route and availability

- Route: `/`
- Available on the local app.
- No login, account, or personalization.
- The primary action opens `/songs/new`.
- There is no Import Song link.

## Data contract

The screen reads `GET /api/songs`.

Each item:

- Stable song ID
- Title
- Artist
- Source language
- Target language
- Duration when an MP3 has been measured
- Publication status

Saved songs are published. The list is the songs on this install.

The text filter runs in the browser over the loaded list. It matches title and artist, case-insensitive. There is no search query parameter in Prototype 1.

## Screen content

- Screen heading: Song Library
- A short explanation that songs are requested in chat, then saved here
- A control that starts a new song
- A text field labeled Search saved songs
- A semantic list of song cards
- Each card shows title, artist, Japanese → English, and formatted duration when known
- Each card is a link to `/songs/:songId`

Do not add sort controls, genres, playlists, recommendations, artwork, social counts, or pagination.

## State behavior

### Loading

- Keep the heading. Show a concise loading status. Do not move focus.

### Empty

- Explain that no songs are saved yet.
- The new-song action is the way forward.
- The filter has nothing to match.

### Success

- Render each song once with a stable key.
- Card action is a real link.
- The filter hides non-matching cards and does not refetch.

### No filter match

- Say that no saved song matches. Keep the new-song action.

### Request failure

- Show a safe message and retry.

## Responsive behavior

- Cards are a single column at narrow widths.
- Wider layouts may change the container width. They do not hide the new-song action or the filter.
- Usable at 200% zoom without a horizontal page scrollbar.

## Accessibility

- One main landmark and one level-one heading.
- The filter has a visible label.
- The song collection uses list semantics.
- Each card's accessible name includes title and artist.
- Language direction is text.
- Loading, empty, no-match, and error status are announced.
- The filter, new-song action, and retry are keyboard operable with visible focus.

## Security and privacy

- No account state.
- Titles and artist names render as text.
- Do not show filesystem paths or internal notes.
- The library is the songs on this machine. It is not a shared public catalog.

## Tests

### Unit/component

- Loading, empty, one-song, filter match, no match, and failure
- Duration formatting, including unknown duration
- Card name and link
- No import action

### API integration

- List fields and a stable order
- No local paths in the payload

### End-to-end

- The app opens on Song Library without login.
- An empty library offers a new song.
- After a song is saved, the card opens Learn Song.
- The filter narrows the cards that are already loaded.
- Browser back returns to the library.

## Sequencing

1. Freeze the song summary contract.
2. Keep the list API and card links.
3. Add the filter and the new-song action.
4. Remove the import link.

Requires the foundation. The new-song action needs [Song creation](../song-creation/spec.md).

## Acceptance criteria

- `/` renders without authentication.
- The list is saved songs only.
- Search saved songs filters that list in the page.
- New song opens `/songs/new`.
- A card opens `/songs/:songId`.
- Loading, empty, no-match, failure, and retry are explicit.
- There is no import action.

## Risks

- A filter can be mistaken for a search of every song the model knows. The label is Search saved songs, and an empty library points at new song.
- Nested click targets on a card make it inaccessible.

## Non-goals and deferred work

- Server-side search, sorting, and pagination
- Playlists, favorites, history, and progress
- Artwork
- Recommendations or social features
- Accounts
- A public catalog
