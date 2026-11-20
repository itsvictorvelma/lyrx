# 025 — Polish: titles, link previews, favicon, back, undo, filter

Status: approved (batch 2, asked for by the user on 2026-11-20)

## Goal

Lyrx looks finished when someone opens a shared link or moves around: each tab names its page, links show a preview, the back arrow goes back, removing a song can be undone, and a long library can be filtered.

## In scope

- A browser tab title for each page.
- A link preview (Open Graph and Twitter card tags) and a preview image.
- A favicon.
- The song page's back arrow goes back to the page you came from.
- Removing a song shows "Removed … · Undo" instead of the browser's confirm box.
- A filter box on Your songs once it holds more than 8 songs.

## Out of scope

- The "Found in x s" timing line stays as it is (the user's choice).
- A preview per song (needs the server to render each page; a site-wide preview only).
- The absolute address of the preview image (the domain is not known until spec 020).

## Rules

Titles
- Home: "Lyrx · Read Japanese songs line by line". Your songs: "Your songs · Lyrx". A song: "<title> · <artist> · Lyrx". While a song opens: "Opening… · Lyrx".

Link preview
- `index.html` gets a description, `og:title`, `og:description`, `og:type`, `og:image`, `twitter:card` (`summary_large_image`), and `theme-color` (the dark `--bg`).
- `frontend/public/og-image.png`, 1200×630: the night background, the wordmark, and the hero's example line with its readings (invented), in the existing colours.
- `og:image` is `/og-image.png` for now; a `ponytail:` comment says spec 020 makes it absolute with the domain.

Favicon
- `frontend/public/favicon.svg`: a rounded square in the dark background with 歌 in the accent pink; `apple-touch-icon.png` (180×180) for phones.

Back arrow
- Its label becomes "Back". When the song was opened from inside Lyrx, it goes back in history (home, Your songs, or a search). When the song was the first page (opened from a link), it goes to home.

Undo
- Remove takes the song off at once and shows a status message at the bottom: "Removed <title>" with an Undo button, for 6 seconds or until the next one replaces it.
- Undo saves the song again with its video and sync, so nothing is lost. `GET /api/songs` includes each song's `offsetMs` for this.
- The message is announced to screen readers (`role="status"`) and the Undo button is reachable by keyboard; it is not hidden on focus or hover while open.

Filter
- With more than 8 saved songs, Your songs shows a labelled "Filter your songs" box above the tiles. It matches title or artist, ignoring letter case, as you type, and keeps the chosen sort. No match says: "No songs match "<text>"."

## Security

- The new tags and files are static. The filter and titles use song names as text only.
- Undo reuses the existing save route; no new server input.

## Acceptance checks

- AC-1: The tab title follows the page: home, Your songs, a song (title and artist).
- AC-2: `index.html` has the preview tags and the favicon links; the image and icons exist at those paths.
- AC-3: Back goes back in history after opening a song inside Lyrx, and goes home when the song was the first page.
- AC-4: Remove takes the song off with no confirm box and shows the Undo message; Undo saves it again with its video and sync, and it is back in the list.
- AC-5: `GET /api/songs` includes `offsetMs`.
- AC-6: With 9 songs the filter shows and matches title or artist, ignoring case; with 8 it is hidden; no match shows the message.

## Plan

- Backend: `library.list_songs` and `SavedSong` add `offset_ms` (`offsetMs`); test in `test_library.py` (AC-5).
- `index.html`: description, preview tags, favicon links. `frontend/public/`: `og-image.png`, `favicon.svg`, `apple-touch-icon.png` (rendered once from HTML with headless Chrome; the HTML source is not kept).
- `routing.ts`: `navigate` marks entries it adds (`{ lyrx: true }`); `goBack()` goes back for a marked entry, else home. `SongPage.tsx`: the back arrow uses it.
- `App.tsx`: the tab title per page; Remove without confirm, with the Undo message (`library/RemovedMessage.tsx`).
- `library/LibraryPage.tsx`: the filter (`songTiles.ts`: `filterSongs`).
- `lyrics/api.ts` + `types.ts`: `offsetMs` on saved songs.
- `styles.css`: the message and the filter, existing tokens only.
- Tests: `App.test.tsx` (AC-1, AC-4), `routing.test.ts` (AC-3), `LibraryPage.test.tsx` and `songTiles.test.ts` (AC-6), `index.test.ts` reading `index.html` (AC-2).
