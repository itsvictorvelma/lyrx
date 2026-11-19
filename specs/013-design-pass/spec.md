# 013 — Design pass

Status: done (merged in PR #31, 2026-11-19)

## Goal

One cohesive look for the whole app: a night music player where the lyrics are the star. The learner lands on their library, opens a song, and reads along while the sung line glows. Agreed with the user on 2026-11-18 through an interview and a clickable mockup (https://claude.ai/artifact/Xrok4tVF2UDqgE7X2be2jk).

## In scope

- **Look.** Colour tokens below, defined once in `styles.css` as CSS variables. Dark and light follow the system setting; a sun/moon button in the header overrides it and is remembered on this browser. System fonts only, with a stack that covers kana and kanji. Header wordmark: "lyrx" with a small 歌詞 in the accent colour.
- **Pages, each with its own address.** `/` is the library. `/song/{id}` is the song page. The browser's Back and Forward buttons move between them, and reloading `/song/{id}` opens that song again. Built on the browser's History API, without a router package.
- **Header on every page.** The wordmark (links to `/`), the search box, and the theme button.
- **Library (home).**
  - Saved songs as a grid of tiles, most recently opened first. Sort buttons: Recent, A–Z, Artist.
  - A tile shows the YouTube thumbnail when the song has a linked video. Otherwise it shows the first character of the title on a colour derived from the title.
  - Each tile shows the title, the artist, and "Opened today / yesterday / N days ago".
  - Each tile has a Remove button, shown on hover and keyboard focus and always shown on touch screens. It asks "Remove {title} from your songs?" before removing.
  - **Empty library:** one welcoming line and an example search ("Type a song you love: title, artist, or both").
- **Searching.** The search box runs from any page. While it waits, the page shows the steps ("Finding the song" → "Getting the lyrics and translating"), each with a done, in-progress, or waiting mark. It also shows the seconds elapsed and placeholder rows that shimmer. When the best match opens, the address becomes `/song/{id}`.
- **Song page.**
  - **Header row:** back arrow, the title (large) and artist, a "Synced lyrics" or "No line timings" note, and "Not this one?". That opens the other matches from the last search in a small popover; it is hidden when there are none.
  - **Lyrics rows.** One row per line in four columns, sized original 21px, hiragana 19px, romaji 16px, English 15px in the dim colour. All four cells of a row stay level. A wrapped cell makes the whole row taller.
  - **Sung row.** It gets the accent-soft background, a 3px accent left bar, and a soft glow. While audio plays, the other rows use the dim colour. The lyrics glide so the sung row stays centred.
  - **Lyrics height.** The lyrics area fills the height between the header and the player bar. The page itself never scrolls on the song page.
- **Player bar,** fixed to the bottom of the song page.
  - Previous line, play/pause, next line, a position slider with the current time and duration, Earlier / Sync / Later, and a video button.
  - With no audio chosen, it shows "Add YouTube link" and "Play a file" instead. These open the existing link box and file picker from spec 012.
  - The YouTube video plays in a small window at the bottom right, which can be hidden and shown again. The lyrics get enough bottom space that the last line can scroll clear of it.
- **Focus mode.** A Focus button on the song page hides the header and the song's header row, leaving a slim strip (title, artist, Exit focus) and the player bar. Text grows: original 28px, hiragana 23px, romaji 18px, English 17px. Leaving the song page ends Focus mode.
- **Phone (narrower than 720px).**
  - The song page shows the original next to one chosen column. Tabs (かな, Romaji, EN) pick the column, and かな is the default.
  - The player bar becomes two rows, the video opens as a panel above the player bar, and library tiles are two per row.
- **Motion.** The highlight fades between lines. Tiles lift on hover. Pages fade up when they open. A shimmer runs while waiting. All animation and smooth scrolling are off when the system asks for reduced motion.

## Colours (approved 2026-11-18)

| Token | Dark | Light |
|---|---|---|
| `--bg` | `#0E0D12` | `#FAF8FA` |
| `--surface` | `#18161D` | `#FFFFFF` |
| `--surface-2` (raised) | `#24212B` | `#F1EDF2` |
| `--line` (dividers) | `#2A2731` | `#E4DFE6` |
| `--text` | `#F3F0F5` | `#1B1820` |
| `--dim` | `#9C97A8` | `#6A6575` |
| `--accent` (sakura) | `#FF7AB6` | `#C92A74` |

The accent-soft background and the glow are the accent at low opacity. Raised panels (popover, video window) have a soft drop shadow, as in the approved mockup. No other colours, except the derived tile colours (hue from the title, fixed lightness), the existing error colours (`--error`), and `--accent-ink` for text on the accent.

## Out of scope

- Hiding a column to test yourself, looping a line, and keyboard shortcuts (spec 015, next).
- Finding the YouTube video automatically, showing lines as they arrive, personal accounts.
- Serving `/song/{id}` from the Python server in production (the hosting spec). The Vite dev server already does it.

## Inputs and outputs

- `GET /api/songs`: each song gains `"videoId": "dQw4w9WgXcQ" | null` and `"lastOpenedAt": 1795048464000` (Unix time, milliseconds). Nothing else changes.
- Thumbnail address, built in the page only from a video id that passes the 11-character id pattern: `https://i.ytimg.com/vi/{videoId}/mqdefault.jpg`.

## Rules

1. The theme choice is stored in `localStorage` under one key, wrapped in try/catch. With nothing stored, or storage blocked, the system setting decides.
2. An address that is not `/` or `/song/{id}` (where id is a whole number from 1 to the existing maximum) shows the library.
3. The tile colour is a pure function of the title, so the same song always gets the same colour.
4. All text meets 4.5:1 contrast against its background in both themes, including dim rows during playback. Rows are dimmed with the `--dim` colour, never with transparency.
5. Every control is a real button, link, or input with a visible label or `aria-label`, and has a visible focus ring in the accent colour. State is never shown by colour alone: the sung row has a bar, and toggles use `aria-pressed`.

## Security

- **Untrusted input:** video ids from the server are checked against the existing pattern before a thumbnail address is built. Titles render as text. The `/song/{id}` address is parsed as a bounded whole number, never used as a path or URL.
- **Outside services:** the browser loads thumbnails from `i.ytimg.com` for songs with a linked video, so YouTube sees those requests, just as the spec 012 embed already does. The server calls no new host.
- **Logs and disk:** nothing new is logged. The theme choice lives in `localStorage`.

## Acceptance checks

- AC-1: Opening `/` shows the library tiles, most recently opened first. Sorting by A–Z and by Artist reorders them.
- AC-2: With no saved songs, the library shows the empty-state line and example.
- AC-3: A song with a video shows a thumbnail built from its id. A song without one shows its first character on a colour that is the same every time.
- AC-4: Remove asks for confirmation. Confirming removes the tile, and cancelling keeps it.
- AC-5: Searching shows the steps and elapsed seconds, then opens the song at `/song/{id}`.
- AC-6: Opening the address `/song/{id}` directly loads that song. Back returns to the library, and an unknown address shows the library.
- AC-7: The theme button switches dark and light and is remembered after a reload. With nothing stored, the system setting decides.
- AC-8: The sung row has the `current` state, and while audio plays the other rows are dimmed.
- AC-9: The player bar's play/pause, previous/next line, and position slider control the audio. With no audio chosen, the bar offers "Add YouTube link" and "Play a file".
- AC-10: Focus mode hides the header and song header and shows "Exit focus". Exit focus and leaving the page both end it.
- AC-11: Below 720px wide, the song page shows the original plus one column, and the かな / Romaji / EN tabs switch it.
- AC-12: `GET /api/songs` returns `videoId` and `lastOpenedAt` for each song.
- AC-13: Every text-and-background token pair in both themes passes 4.5:1. The styles turn off animation and smooth scrolling under `prefers-reduced-motion`.

## Plan

**Backend (small).** `schemas.py`: a `SavedSong` (a `Song` plus `videoId`, `lastOpenedAt`) used by `SavedSongsResponse`. `library.list_songs` selects `video_id` and `last_opened_at`, dropping a video id that fails the pattern (as `to_playback` does). Test in `test_library.py`.

**Frontend.** Grouped by feature:
- `routing.ts`: parse a path into a route, push a path, and a `useRoute` hook (popstate). New.
- `header/`: `Header.tsx` (wordmark, search, theme), `ThemeButton.tsx` (with the stored choice, system setting, and `data-theme` on `<html>`). `SearchForm.tsx` moves here.
- `library/`: `LibraryPage.tsx` (sort, grid, empty state), `SongTile.tsx`, `songTiles.ts` (thumbnail address, title hue, "Opened …" label, sort). Replaces `SavedSongs.tsx`.
- `lyrics/`:
  - `SongPage.tsx` (header row, Focus strip, phone tabs, lyrics, player bar; owns the clock polling now in `App.tsx`).
  - `PlayerBar.tsx` (replaces `PlaybackPanel.tsx`; keeps its link, file, and save logic) and `PlayerControls.tsx` (the controls row, split out to keep the bar short).
  - `SearchProgress.tsx` (steps, seconds, placeholder rows; replaces `WaitingStatus.tsx`).
  - `VersionsTable.tsx` stays a real table: a column class per cell, a `data-phone-column` attribute, a `playing` class, and the sung row centred.
  - `OtherMatches.tsx` becomes the "Not this one?" popover (still `<details>`).
- `playback.ts`: `AudioClock` gains `play`, `pause`, `isPlaying`, `durationMs`. The YouTube and file players implement them; the file player's `<audio>` loses its own controls.
- `App.tsx` becomes the shell: route, search state, saved songs, Focus mode, errors.
- `styles.css` is rewritten around the tokens. The existing error colours stay as `--error`, plus `--accent-ink` for text on the accent (play button), both checked by the contrast test.

**Tests.** `App.test.tsx` and `PlaybackPanel.test.tsx` are reworked for the new pages (the latter becomes `PlayerBar.test.tsx`). New `routing.test.ts`, `ThemeButton.test.tsx`, `songTiles.test.ts`, `LibraryPage.test.tsx`. `styles.test.ts` covers contrast, reduced motion, and the phone column rule.

**Side effects.** None outside the page. The README folder map gains `header/` and `library/`.
