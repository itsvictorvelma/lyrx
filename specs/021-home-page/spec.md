# 021 — Home page

Status: done (merged in PR #45, 2026-11-20; mockup: https://claude.ai/artifact/A2vhoxzKkwNHUCEwURYpkd)

## Goal

The first page a visitor sees explains Lyrx in a few seconds and lets them try it at once. Today `/` is the library, which tells a newcomer (a friend, a recruiter) nothing. The library moves to `/library`.

## In scope

- A home page at `/`: a hero line, a large search box, "How Lyrx works" (first visit) or "Pick up where you left off" (returning), "Songs already in Lyrx", and a footer.
- The library moves to `/library`. The header gets a "Your songs" link and hides its search box on the home page.
- `?` opens a shortcut list on every page; `/` jumps to the search box.
- A public route that lists recently opened cached songs, without lyrics.

## Out of scope

- Accounts (spec 014). Until then, "returning" means the library has songs.
- New colours, fonts, or tokens: the page uses the existing ones in `styles.css`.
- Picking or pinning the songs in the row by hand.

## Rules

Hero
- Above the line: "Read any Japanese song, line by line." (small, dim).
- One invented line, 夜明けの街で君を待つ, in four parts (夜明けの / 街で / 君を / 待つ). Each part shows its hiragana and romaji under it. The English, "I wait for you in the town at dawn", sits below the whole line.
- Animation: the sung-line highlight (accent colour and glow, like the song page) moves part by part, about 650 ms each. A part's readings appear once it has been sung, and the English appears after the last part. It loops three times, then rests with everything shown, so it never moves forever.
- With reduced motion, the whole line shows at once with no movement.
- The line is shown to screen readers once, as a labelled figure with the full line and its English. The animated parts are hidden from them.

Search and shortcuts
- The large search box is the same search as the header (`SearchForm`), at a larger size. Under it: "Press / to search, ? for all keyboard shortcuts".
- `/` focuses the search box on any page where one is shown (the large one on home, the header one elsewhere). `?` shows or hides the shortcut list on every page. Off the song page the list holds `/` and `?`. On the song page it is today's list plus `/`. The same rules as today apply: keys are ignored in fields, with Ctrl/Cmd/Alt, and on key repeat.

Below the search
- First visit (no saved songs): "How Lyrx works", three numbered steps: Find a song / Read every line four ways / Play along and practise, each with one short line.
- Returning (one or more saved songs): "Pick up where you left off", one card with the most recently opened saved song (its art, title, artist, "Continue"), and a link "All your songs (N)" to `/library`.
- "Songs already in Lyrx" with "Already translated, so they open instantly.": up to `RECENT_SONGS_SHOWN = 12` songs, most recently opened first, in one row that scrolls sideways. Tiles reuse the library art (thumbnail or first character on its hue). Clicking a tile opens the song. With none, the section is hidden.

Footer (home page only)
- "Lyrics from LRCLIB. Hiragana, romaji, and English by Groq and Gemini.", "Built by Victor.", a link to the GitHub repo, and the `?` hint.

Routes
- `/` home, `/library` the library, `/song/{id}` a song. An unknown path shows home. A song that does not exist goes to home with the error, as it goes to the library today.
- `GET /api/recent-songs` returns `{ songs: [{ id, track, artist, album, durationSeconds, videoId }] }`: cached songs, most recently opened first, at most `RECENT_SONGS_SHOWN`. No lines. `videoId` is the saved video only, for the thumbnail (none until 014 makes it per person: then always null).

## Security

- The new route reads only song metadata from the cache: no lyrics, no personal data. It takes no input.
- Song names come from LRCLIB (untrusted) and are rendered as text, as everywhere.
- The footer links are fixed `https` addresses in the code.

## Acceptance checks

- AC-1: `/` shows the home page, `/library` the library, an unknown path home. The header's "Your songs" link goes to `/library`, and the wordmark to `/`.
- AC-2: On home, the header has no search box and the large search box finds and opens a song as the header one does.
- AC-3: With reduced motion, the hero shows all four parts, their readings, and the English at once. The figure's label holds the full line and the English.
- AC-4: Without reduced motion, the readings appear part by part and the animation stops after three loops with everything shown (fake timers).
- AC-5: With no saved songs, home shows the three steps and no Continue card. With saved songs, it shows the Continue card for the most recently opened one and "All your songs (N)", and no steps.
- AC-6: "Songs already in Lyrx" lists the recent songs and a click opens one. With an empty list the section is hidden.
- AC-7: `GET /api/recent-songs` returns at most `RECENT_SONGS_SHOWN` cached songs, most recently opened first, without lines, and saved and unsaved songs alike.
- AC-8: `?` opens and closes the shortcut list on home and on the library. `/` focuses the search box on home, the library, and the song page. Neither fires while typing in a field.
- AC-9: The footer shows the credits and the GitHub link.

## Plan

- Backend: `library.py` `list_recent_songs(limit)`; `schemas.py` `RecentSong`, `RecentSongsResponse`; `app.py` route `GET /api/recent-songs`; `config.py` `RECENT_SONGS_SHOWN = 12`. Tests in `test_library.py` and `test_app.py` (AC-7).
- Frontend, new `frontend/src/home/`: `HomePage.tsx` (sections and footer), `HeroLine.tsx` (the animated line), `heroTiming.ts` (the parts and the step timing, so it can be tested without React), tests next to them.
- `library/SongArt.tsx`: the tile art taken out of `SongTile` so the library, the Continue card, and the recent row share it.
- `routing.ts`: `home` and `library` routes. `App.tsx`: renders `HomePage` at `/`, loads recent songs on home, passes `showSearch` to the header.
- `header/Header.tsx`: "Your songs" link, search hidden on home. `header/SearchForm.tsx`: a `size` prop.
- `lyrics/shortcuts.ts`: `/` (`focusSearch`), and a site list next to the song list. `ShortcutList.tsx` takes its list as a prop. A small `SiteShortcuts` in `App.tsx` handles `?` and `/` off the song page; `SongPage` handles `/` too.
- `lyrics/api.ts` + `types.ts`: `listRecentSongs`, `RecentSong`. `fakeSongPage.tsx`: the new route.
- `styles.css`: home page styles from the existing tokens.
- Docs: README (folder map, what works), `specs/README.md`.
