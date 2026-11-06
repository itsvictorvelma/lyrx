# Song Library specification

Prototype 2.

Dependencies and destinations:

- [Application foundation](../app-foundation/spec.md)
- [Song creation](../song-creation/spec.md)
- [Learn Song](../learn-song/spec.md)

## Goal

Let the learner return to songs saved on this install.

The library is a menu or a section. It is not the screen the app opens on, and it is not a column beside the lyrics. The learner starts by typing a song name, as specified in [Song creation](../song-creation/spec.md).

There is no catalog of pre-checked songs. A song appears here after the learner saves it. A fixed song list may exist only as a developer test fixture, never as a screen.

## Route and availability

- Route: `/songs`
- Reached from the header menu, or opened as the library section.
- Available on the local app.
- No login, account, or personalization.
- The action that starts a song opens the search (`/`, `/search`, or `/songs/new`).
- Opening a card goes to `/songs/:songId`, and the lyrics then fill the screen. The list does not stay beside them.
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

Saved songs are published. The list is the songs on this install. It is not a list shipped with the app.

The text filter runs in the browser over the loaded list. It matches title and artist, case-insensitive. There is no search query parameter. This filter is not the lyric search.

## Screen content

- Screen heading: Song Library
- A short explanation that these are songs the learner saved after a search
- A control that opens the search
- A text field labeled Search saved songs
- A semantic list of song cards
- Each card shows title, artist, Japanese → English, and formatted duration when known
- Each card is a link to `/songs/:songId`

Do not add sort controls, genres, playlists, recommendations, artwork, social counts, or pagination. Do not add a list of songs the learner has not saved.

## State behavior

### Loading

- Keep the heading. Show a concise loading status. Do not move focus.

### Empty

- Explain that no songs are saved yet.
- The search is the way forward.
- The filter has nothing to match.

### Success

- Render each saved song once with a stable key.
- Card action is a real link.
- The filter hides non-matching cards and does not refetch.

### No filter match

- Say that no saved song matches. Keep the control that opens the search.

### Request failure

- Show a safe message and retry.

## Responsive behavior

- The library section is usable at narrow and wide widths.
- At every width, choosing a song or a new search leaves the list. The lyrics fill the screen.
- Cards are a single column at narrow widths.
- Wider layouts may change the container width. They do not pin this list beside the lyrics, and they do not hide the search action or the filter.
- Usable at 200% zoom without a horizontal page scrollbar.

## Accessibility

- One main landmark and one level-one heading.
- The filter has a visible label, Search saved songs.
- The song collection uses list semantics.
- Each card's accessible name includes title and artist.
- Language direction is text.
- Loading, empty, no-match, and error status are announced.
- The filter, the search action, and retry are keyboard operable with visible focus.

## Security and privacy

- No account state.
- Titles and artist names render as text.
- Do not show filesystem paths or internal notes.
- The library is the songs on this machine. It is not a shared public catalog, and it is not a catalog of pre-checked songs.

## Tests

### Unit/component

- Loading, empty, one-song, filter match, no match, and failure
- Duration formatting, including unknown duration
- Card name and link
- No import action
- The list renders saved songs only
- A fixture song list is not rendered as this screen

### API integration

- List fields and a stable order
- No local paths in the payload

### End-to-end

- The app opens on the search, not on Song Library.
- The header menu or the library section opens Song Library.
- An empty library offers the search.
- After a song is saved, the card opens Learn Song, and the list is not still beside the lyrics.
- The filter narrows the cards that are already loaded.
- Browser back returns to the library section.

## Acceptance criteria

- `/songs` renders without authentication.
- The app does not open on this screen.
- The list is saved songs only.
- A fixed song list is not a screen.
- Search saved songs filters the loaded list in the page.
- The search action opens the one search.
- A card opens `/songs/:songId` with the lyrics filling the screen.
- The list is not a permanent sidebar.
- Loading, empty, no-match, failure, and retry are explicit.
- There is no import action.

## Risks

- Song Library can be mistaken for a catalog of songs the learner has not saved. The heading copy says these are saved songs, and an empty library points at the search.
- The label Search saved songs can be mistaken for the lyric search. The lyric search is the song-name field in [Song creation](../song-creation/spec.md).
- A wide layout can put the list back in a column beside the lyrics.

## Out of scope

- A catalog of pre-checked songs
- A fixed song list as a screen
- A permanent sidebar
- Server-side search, sorting, and pagination
- Playlists, favorites, history, and progress
- Artwork
- Recommendations or social features
- Accounts
- A public catalog
