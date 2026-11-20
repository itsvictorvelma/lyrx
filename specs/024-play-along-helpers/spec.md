# 024 — Play-along helpers: speed and Find on YouTube

Status: done (batch 1, asked for by the user on 2026-11-20)

## Goal

Two small things that make playing along easier: slow a song down to catch a fast line, and find the song's YouTube video in one click instead of searching by hand.

## In scope

- A playback speed button in the player bar: 1×, 0.75×, 0.5×.
- A "Find on YouTube" link that opens a YouTube search for the song in a new tab.
- The empty player bar becomes one row, as tall as the player: Find on YouTube, the link box always open, and Play a file (redone twice after the user saw it: scattered buttons, an underlined link, then a panel that was too tall and loud).

## Out of scope

- Finding and linking the video automatically (needs a YouTube API key; parked).
- Speeds above 1×, a speed shortcut, remembering the speed.

## Rules

Speed
- One button after the volume control. Each press moves 1× → 0.75× → 0.5× → 1×. Its text is the speed ("0.75×"), and its label is "Playback speed: 0.75×".
- Works for YouTube (`setPlaybackRate`, applied again once the player is ready) and for an audio file (`playbackRate`).
- A new player for the same song keeps the chosen speed. A new song starts at 1×.
- Line highlighting, seeking, and looping keep working, because they follow the player's own clock.

Find on YouTube and the empty player bar
- With no audio yet (or after "Change audio"), the bar is one row, as tall as the player: a "Find on YouTube" pill, the link box (the header search pill: "Paste the YouTube link here", labelled "YouTube link", with "Play video" inside, greyed out until a link is typed), and a "Play a file" pill. The row is a group named "Play along with the song". The link box is always open: find, copy, paste, play. No popup.
- "Find on YouTube" is a link styled as a pill button (no underline). It opens `https://www.youtube.com/results?search_query=<title> <artist>` (URL-encoded) in a new tab with `rel="noopener noreferrer"`.
- The keyboard shortcuts button sits at the right end of the bar. On a phone the link box takes a full row.

## Security

- The link is built in the browser from the song's title and artist, URL-encoded, to a fixed `https` host. The server fetches nothing.
- The new tab gets no opener and no referrer.

## Acceptance checks

- AC-1: The speed button cycles 1× → 0.75× → 0.5× → 1× and sets the YouTube player's rate, also once it is ready.
- AC-2: With an audio file, the speed button sets the audio element's `playbackRate`.
- AC-3: "Find on YouTube" points to the YouTube search for the song's title and artist, URL-encoded, opening in a new tab without opener or referrer.
- AC-4: With no audio, the row shows Find on YouTube, the link box, and Play a file. Once audio is playing, it is gone.

## Plan

- `lyrics/playback.ts`: `AudioClock.setPlaybackRate(rate)`, `PLAYBACK_SPEEDS`, `nextSpeed`, `youTubeSearchUrl(track, artist)`.
- `YouTubePlayer.tsx` / `AudioFilePlayer.tsx`: apply the rate (YouTube: kept and applied again in `onReady`, like the volume).
- `PlayerBar.tsx`: holds the speed and applies it to each new player; passes title and artist to the chooser. `PlayerControls.tsx`: the speed button. `SongPage.tsx`: passes title and artist.
- `styles.css`: the one-row chooser reusing `.search-box` and `.find-button`, and pill links without underline; existing tokens only.
- Tests: `playback.test.ts` (next speed, search URL) and `PlayerBar.test.tsx` (AC-1 to AC-4).
