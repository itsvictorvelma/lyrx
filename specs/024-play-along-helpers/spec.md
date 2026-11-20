# 024 — Play-along helpers: speed and Find on YouTube

Status: approved (batch 1, asked for by the user on 2026-11-20)

## Goal

Two small things that make playing along easier: slow a song down to catch a fast line, and find the song's YouTube video in one click instead of searching by hand.

## In scope

- A playback speed button in the player bar: 1×, 0.75×, 0.5×.
- A "Find on YouTube" link that opens a YouTube search for the song in a new tab.
- A short hint in the empty player bar that explains the two ways to play along.

## Out of scope

- Finding and linking the video automatically (needs a YouTube API key; parked).
- Speeds above 1×, a speed shortcut, remembering the speed.

## Rules

Speed
- One button after the volume control. Each press moves 1× → 0.75× → 0.5× → 1×. Its text is the speed ("0.75×"), and its label is "Playback speed: 0.75×".
- Works for YouTube (`setPlaybackRate`, applied again once the player is ready) and for an audio file (`playbackRate`).
- A new player for the same song keeps the chosen speed. A new song starts at 1×.
- Line highlighting, seeking, and looping keep working, because they follow the player's own clock.

Find on YouTube
- A link styled like the other pill buttons, next to "Add YouTube link", wherever the audio chooser shows.
- It opens `https://www.youtube.com/results?search_query=<title> <artist>` (URL-encoded) in a new tab with `rel="noopener noreferrer"`.
- With no audio yet, a line above the chooser says: "Play along: find the song on YouTube and add its link, or play a file from your computer."

## Security

- The link is built in the browser from the song's title and artist, URL-encoded, to a fixed `https` host. The server fetches nothing.
- The new tab gets no opener and no referrer.

## Acceptance checks

- AC-1: The speed button cycles 1× → 0.75× → 0.5× → 1× and sets the YouTube player's rate, also once it is ready.
- AC-2: With an audio file, the speed button sets the audio element's `playbackRate`.
- AC-3: "Find on YouTube" points to the YouTube search for the song's title and artist, URL-encoded, opening in a new tab without opener or referrer.
- AC-4: With no audio, the hint shows. Once audio is playing, it is gone.

## Plan

- `lyrics/playback.ts`: `AudioClock.setPlaybackRate(rate)`, `PLAYBACK_SPEEDS`, `nextSpeed`, `youTubeSearchUrl(track, artist)`.
- `YouTubePlayer.tsx` / `AudioFilePlayer.tsx`: apply the rate (YouTube: kept and applied again in `onReady`, like the volume).
- `PlayerBar.tsx`: holds the speed and applies it to each new player; passes title and artist to the chooser. `PlayerControls.tsx`: the speed button. `SongPage.tsx`: passes title and artist.
- `styles.css`: the hint, reusing existing tokens.
- Tests: `playback.test.ts` (next speed, search URL) and `PlayerBar.test.tsx` (AC-1 to AC-4).
