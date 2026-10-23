---
cursor:
  subagentId: "bc-43f25a2f-93d8-5ec7-9282-d2774358e7bf"
---

# Song Library specification

Parent plan: [Prototype 1 build plan](../../AGENTS.md)

Dependencies and destinations:

- [Application foundation](../app-foundation/spec.md)
- [Developer song import](../content-import/spec.md)
- [Learn Song](../learn-song/spec.md)

## Goal

Provide the simple landing screen from which a learner can find an available song and open Learn Song. Prototype 1 may contain only one song; the screen establishes the future catalog entry point without implementing catalog features.

## Route and availability

- Route: `/`
- Available in development and production.
- No login, account, personalization, or learner-side write.
- Development may show a link to Import Song.
- Production must not render an import action or link.

## Data contract

Request:

- Read-only song-list operation from the internal FastAPI API.

Each item:

- Stable song ID
- Title
- Artist
- Source language
- Target language
- Duration when known
- Publication/availability state as needed by the client

Production response contains publishable songs only. Development may include drafts only if they are clearly marked and the API contract explicitly requests/allows them.

## Screen content

- Screen heading: Song Library
- Concise explanation of Lyrx's purpose
- Ordered or unordered semantic list of song cards
- One card per available song
- Each card shows title, artist, Japanese → English language direction, and formatted duration when known
- Primary action opens `/songs/:songId`
- Development-only Import Song action

A one-card library for “Akuma no Ko” is acceptable.

Do not add search, filters, sorting controls, genres, playlists, recommendations, artwork ingestion, social counts, or pagination in Prototype 1.

## State behavior

### Loading

- Show a stable layout/skeleton or concise loading status.
- Preserve the screen heading and avoid focus jumps.

### Empty

- Production: explain that no songs are available.
- Development: explain that no songs are imported and offer Import Song.

### Success

- Render each API item once with a stable key.
- Card action is a real link so open-in-new-tab and browser navigation work.

### Request failure

- Show a safe message and retry.
- Preserve any already rendered valid content only if stale-data behavior is deliberately implemented and announced.

### Unavailable selection

- If a selected song becomes unavailable, Learn Song owns the detailed error; returning to Song Library must remain possible.

## Responsive behavior

- Cards form a readable single-column list at narrow widths.
- Wider layouts may adjust container width or card grid, but must not introduce additional information hierarchy or hide the primary action.
- Content remains usable at 200% zoom without horizontal page scrolling.
- Development import action does not crowd the learner's primary song action.

## Accessibility

- Main landmark and one level-one heading.
- Song collection uses list semantics.
- Each card has one clear accessible name combining title and artist.
- Do not use a clickable container with nested conflicting controls.
- Language direction is text, not color-only.
- Loading, empty, and error status are announced appropriately.
- Retry and import actions are keyboard operable with visible focus.
- Route navigation preserves expected browser behavior.

## Security and privacy

- No user data or account state.
- Do not show filesystem/media paths, rights evidence, internal status notes, or draft songs in production.
- Imported title/artist render as escaped text.
- Development controls depend on the actual environment boundary, not a query parameter or client storage.

## Tests

### Unit/component

- Loading, one-song, multi-song, empty, and failure states
- Duration formatting including unknown duration
- Song card accessible name/link
- Development import action present; production absent
- Draft filtering/labeling behavior

### API integration

- List includes required fields and stable order
- Production returns publishable songs only
- No rights evidence or local paths leak

### End-to-end

- App opens at Song Library without login.
- Selecting “Akuma no Ko” opens the correct Learn Song URL.
- Browser back returns to the same library state.
- Production has no navigation path to Import Song.

## Sequencing

1. Freeze Song summary contract.
2. Implement repository/publication filter and list API.
3. Build screen states and card link.
4. Add development import navigation.
5. Complete accessibility/responsive/E2E coverage.

Requires the application foundation and at least one imported development fixture. It may be built in parallel with Learn Song after contracts are frozen.

## Acceptance criteria

- `/` renders without authentication.
- One approved song is understandable and selectable without search.
- Selection routes to `/songs/:songId`.
- Loading, empty, failure, and retry states are explicit.
- Production displays publishable songs only and no import action.
- Screen is keyboard accessible, responsive, and usable at high zoom.
- No out-of-scope catalog functionality is present.

## Risks

- Building for hypothetical catalog scale bloats the prototype.
- Draft or rights metadata leaks publicly.
- Card interactions become inaccessible through nested click targets.

Mitigate with a minimal summary contract, server-side publication filtering, and semantic links/lists.

## Non-goals and deferred work

- Search, sorting, filters, pagination
- Playlists, favorites, history, progress
- Artwork pipeline
- Recommendations or social features
- Accounts/private libraries
- Public song submission
