# 022 — Volume

Status: done (merged in PR #46, 2026-11-20)

## Goal

The learner sets how loud the song plays without leaving Lyrx: a volume slider and a mute button in the player bar, for both a YouTube video and an audio file.

## In scope

- A mute button and a volume slider next to the position slider in the player bar.
- Works for YouTube and for an audio file from the computer.
- The volume is remembered in this browser, for every song.

## Out of scope

- A keyboard shortcut for volume (the arrow keys already move between lines).
- Saving the volume with the song or on the server.

## Rules

- Volume runs from 0 to 100 in steps of 5. It starts at 100 when nothing is remembered.
- The slider is labelled "Volume", and screen readers hear it as a percentage ("60%").
- The mute button is labelled "Mute" when there is sound and "Unmute" at 0, and its icon changes too, not just its colour. Mute sets 0 and remembers the level before. Unmute brings that level back (100 if there was none). Moving the slider up from 0 also unmutes.
- The level is kept in `localStorage` (`lyrx-volume`), like the theme. A missing, broken, or blocked value means 100.
- A new player (another song, a new link, a file) starts at the current level. YouTube's player takes the level once it is ready.
- On a phone (the phone layout width), only the mute button shows: phones set loudness with their own buttons, and some ignore a page's volume.
- Reuses the existing tokens and the position slider's look.

## Security

- No new input reaches the server. The stored value is checked (a whole number from 0 to 100) before use.

## Acceptance checks

- AC-1: Moving the slider sets the YouTube player's volume. With an audio file, it sets the audio element's volume.
- AC-2: Mute sets 0 and the button becomes "Unmute". Unmute brings back the earlier level.
- AC-3: The level is remembered: a new player, and a page opened later, start at it. A broken stored value means 100.
- AC-4: The YouTube player gets the level when it becomes ready.

## Plan

- `lyrics/volume.ts`: the stored level (read, check, write) and the mute and unmute rules.
- `lyrics/playback.ts`: `AudioClock.setVolume(percent)`.
- `YouTubePlayer.tsx`: `setVolume` on the handle, the level applied in `onReady`. `AudioFilePlayer.tsx`: `element.volume`.
- `PlayerBar.tsx`: holds the level, applies it to the current player and to each new one. `PlayerControls.tsx`: the mute button and the slider.
- `styles.css`: `.volume`, with the slider hidden in the phone layout.
- Tests: `volume.test.ts`, and `PlayerBar.test.tsx` for AC-1 to AC-4 (the fake player records the volume).
