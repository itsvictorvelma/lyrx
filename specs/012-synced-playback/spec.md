# 012 — Synced playback

Status: done (merged in PR #29, 2026-11-18)

## Goal

The learner plays the song, from YouTube or their own MP3, and the line being sung lights up in the table. Following along while listening is how a song is actually learned.

## Why it can be simple (checked 2026-11-18 on 79 real Japanese songs from LRCLIB)

- 75 of the 79 have timed lyrics (`syncedLyrics`: one `[mm:ss.xx]` start time per line).
- In 73 of those 75 the timed lines are exactly the plain lines, in order.
- So the table keeps the plain lyrics as today, and each line gets its start time. When the two do not match, the song has no timings and plays without highlighting.

## In scope

- **Line timings.** Each line gains `startMs` (milliseconds, or `null`): matched from LRCLIB's timed lyrics when their non-blank lines equal the plain lines, else `null` for every line. Blank lines are always `null`.
- **YouTube by link.** A "YouTube link" box under the song title. The pasted link becomes a video id; the video plays in the page through YouTube's privacy-enhanced embed (`youtube-nocookie.com`). Accepted links: `youtube.com/watch?v=…`, `youtu.be/…`, `music.youtube.com/watch?v=…`, `youtube.com/shorts/…`. Anything else: "That doesn't look like a YouTube link."
- **Your own MP3.** A "Play a file" button picks an audio file from the learner's computer. It plays in the browser only; it is never uploaded or stored.
- **Highlight.** While audio plays, the row being sung is highlighted (a background and a left bar, not color alone) and scrolled into view (instantly when the learner prefers reduced motion). Clicking a row's original text jumps the audio to that line.
- **Sync nudge.** "Earlier" and "Later" buttons move the timings by 0.25 s, shown as "Sync: +0.50 s", for videos with an intro or a different cut. Limited to ±30 s.
- **Saved with the song.** The video id and the sync nudge are saved with the song in the library, so the next open restores them. A song that is not saved (it has a "Not available" line) can still play; its link is not kept.
- **No timings.** A song without timings still plays; the page says "No line timings for this song."
- **Older saved songs** have no timings. Removing and opening them again fetches them.

## Out of scope

- Finding the YouTube video automatically (a later spec: needs a YouTube API key).
- Remembering MP3 files, editing timings by hand, word-by-word highlighting, looping a line.
- Visual design beyond plain and readable (the design pass).

## Inputs and outputs

- `POST /api/song-versions` reply: each line gains `"startMs": 12340 | null`; the reply gains `"playback": { "videoId": "dQw4w9WgXcQ" | null, "offsetMs": 0 }`.
- `PUT /api/songs/{id}/playback` with `{ "videoId": "…" | null, "offsetMs": 500 }` → `204`. `404 song_not_found` when the song is not saved. A video id that is not 11 characters of `A-Z a-z 0-9 _ -`, or an offset outside ±30,000 ms → `400 invalid_request`.

## Rules

1. Timed lyrics are parsed with one anchored pattern per line (`[m:ss]`, `[mm:ss.xx]`, or `[mm:ss.xxx]`); lines without a valid tag are skipped. Times must not go backwards; if they do, the song has no timings.
2. The offset is added to every start time: the current line is the last line whose `startMs` plus the offset is at or before the playback time. "Later" adds 0.25 s (the highlight comes later, for a video with an intro); "Earlier" takes 0.25 s away.
3. The page parses the link to a video id; the server checks the id again before saving. The server never fetches anything from YouTube.
4. The library gains `video_id` and `offset_ms` columns, added to an existing database on first use; existing rows get `null` and `0`.

## Security

- **Untrusted input:** the pasted link (only an 11-character id is kept, and it is checked on the page and on the server); LRCLIB's timed lyrics (size already capped; parsed line by line without backtracking); the picked file (played by the browser's own player through a local object URL, never sent anywhere).
- **Outside services:** the page loads YouTube's player script and embed from YouTube; the server makes no new outside calls. The embed uses `youtube-nocookie.com`.
- **Stored:** the video id and offset in the local library. Never the MP3.

## Acceptance checks

Backend (pytest, fakes):

- AC-1: A record whose timed lines match its plain lines gives every lyric line its `startMs`; blank lines get `null`.
- AC-2: Timed lines that do not match, times that go backwards, or no timed lyrics → every `startMs` is `null`.
- AC-3: Tags `[1:02]`, `[01:02.5]`, `[01:02.50]`, `[01:02.500]` all parse; a malformed tag is skipped.
- AC-4: `PUT /api/songs/{id}/playback` saves the id and offset; the next open returns them in `playback`.
- AC-5: A bad video id or an offset beyond ±30 s → `400 invalid_request`; an unsaved song → `404 song_not_found`.
- AC-6: A library made before this spec gains the new columns and its songs still open.

Page (Vitest):

- AC-7: Each accepted link form gives the right video id; other links show the error and nothing is embedded.
- AC-8: At a given playback time, the right row is highlighted; with an offset, the highlight moves accordingly.
- AC-9: Clicking a row seeks the player to that line's start plus the offset.
- AC-10: "Earlier" and "Later" change the shown offset by 0.25 s and save it for a saved song.
- AC-11: A song without timings says "No line timings for this song."

## Plan

- **Backend:** `lyrics/lrclib.py` reads `syncedLyrics`; `lyrics/lines.py` gains `start_times` (parse the tags, match to the plain lines); `song.py` puts `start_ms` on each line; `schemas.py` gains `start_ms`, `Playback`, `PlaybackRequest`; `library.py` gains the two columns (added to old databases), returns `playback`, and `save_playback`; `app.py` gains `PUT /api/songs/{id}/playback`; `config.py` the id pattern and offset limit.
- **Frontend:** `lyrics/playback.ts` (link → video id, current line, offset text); `lyrics/YouTubePlayer.tsx` and `lyrics/AudioFilePlayer.tsx` (each reports its time and can seek); `lyrics/PlaybackPanel.tsx` (link box, Play a file, Earlier/Later, status); `VersionsTable.tsx` highlights a row and seeks on click; `api.ts` gains `savePlayback`. No new dependency: YouTube's player script is loaded by a script tag, with its few types written by hand.
