# 016 — Save songs on purpose; fill in missing lines

Status: done (merged in PR #34, 2026-11-19)

## Goal

Two learner problems, one fix to how songs are kept.

1. **Previews fill the library.** Today every song you open lands in your songs, along with its video and sync. A learner who only wanted a quick look should be able to leave it out. The library becomes the songs you **Save**.
2. **"Not available" lines never get better.** A line the translator keeps failing (already asked twice in one open) keeps the whole song out of the cache. Every reopen re-translates all of it, and the video and sync can't be kept. Instead, the server should cache the song and, on each reopen, ask again for **only** the missing lines.

**Two words used below.** The **cache** is the server's invisible store of translations, so reopening a song is instant and free. The learner never sees it. **Saved** means in the learner's library: the song shows as a tile, and its video and sync are kept. Think of a browser: its cache versus your bookmarks.

## In scope

- **Every opened song goes in the cache**, including songs with "Not available" lines. Reopening is instant and spends no quota on lines that are already done.
- **Reopening a song with missing lines** asks the translators for only those lines, with the whole song as context, as the translator chain does today. Lines that now pass go into the cache. The rest stay "Not available" for the next reopen. If every translator is busy, the cached song opens as it is, with no error.
- **Save button** on the song page, next to "Not this one?". It reads "Save" for a song not in your library, and "Saved" (with `aria-pressed="true"` and a filled bookmark icon) for one that is.
  - **Save** adds the song to your library together with the video link and sync now in the player bar.
  - Pressing **Saved** again takes the song out of your library. It stays in the cache.
- **Video and sync are kept only for saved songs.** Unsaving clears them. While previewing, the link and sync work but are not kept, and saving keeps them. After saving, changes are kept as they are today.
- **Library and Remove.** The library lists only saved songs. A tile's Remove takes the song out of your library (same confirmation as today). It stays in the cache.
- **Songs already in your library stay saved** when the server upgrades, with their video and sync.
- **A song with missing lines can be saved.** Its missing lines are still asked again on each reopen.

## Out of scope

- Clearing the cache. Each song is small (a few KB). `ponytail:` it grows without limit; a later spec can drop unsaved songs not opened for 90 days.
- Choosing which translator answers the second ask, and editing a line by hand.
- Accounts: "saved" is one flag for the whole app until spec 014 makes it per person.

## Inputs and outputs

- `POST /api/song-versions` reply: unchanged shape, plus `"saved": true | false` on the reply. `fromLibrary` keeps its name and now means "from the cache". The page's timing line says "Already translated · opened in 0.1 s" instead of "Opened from your songs".
- `PUT /api/songs/{id}/saved` with `{ "videoId": "…" | null, "offsetMs": 0 }` saves the song with that playback and returns `204`. It returns `404 song_not_found` when the song is not in the cache, and `400 invalid_request` for a bad video id or offset (the same checks as playback).
- `DELETE /api/songs/{id}/saved` takes the song out of the library and returns `204`, or `404 song_not_found` when it is not saved. This replaces `DELETE /api/songs/{id}`, which is removed.
- `PUT /api/songs/{id}/playback`: unchanged, and still `404 song_not_found` for a song that is not saved.
- `GET /api/songs`: only saved songs, unchanged shape.

## Rules

1. The `saved_songs` table gains `saved INTEGER NOT NULL DEFAULT 1` (added to older files the way `video_id` was, so existing songs stay saved). A newly opened song is stored with `saved = 0`.
2. Reopening asks again only when a cached song has missing lines: a non-blank original whose three versions are empty. Only those lines are sent (the existing chunked path, with the whole song as context), never a full re-translation.
3. Lines from the new ask pass the same checks as today before they replace a missing line. A line that was fine is never replaced.
4. A busy or failed ask on reopen is logged as `refill_failed=<error code>` and never fails the reply. If the new lines can't be stored, they are still shown, and the failure is logged as `save_failed`.
5. Untrusted bodies are checked before use, with the same id bounds and playback checks as today.

## Security

- **Untrusted input:** route ids are bounded as today, and the `saved` body is validated by the existing `Playback` model. Model output for missing lines goes through the existing per-line checks.
- **Outside services:** the same translators as today. A reopen sends at most the missing lines, plus the song as context.
- **Logs and disk:** logs gain `refilled_lines` (a count) and `refill_failed` (a fixed error code), and no lyrics. The database gains one column. No lyrics are logged.

## Acceptance checks

- AC-1: Opening a new song does not add it to `GET /api/songs`, and its reply says `saved: false`.
- AC-2: Opening a song with a missing line caches it. Reopening sends only the missing line to the translator, and a line that now passes is shown and kept.
- AC-3: When every translator is busy on reopen, the cached song opens with its missing line still "Not available", and the reply is 200.
- AC-4: `PUT /api/songs/{id}/saved` saves the song with the given video and sync, and it then appears in `GET /api/songs`. An unknown song is `404`, and a bad video id is `400`.
- AC-5: `DELETE /api/songs/{id}/saved` removes the song from the library and keeps it in the cache: reopening calls no translator for a complete song.
- AC-6: Playback for an unsaved song is not kept (`404`, and quiet on the page). After saving, Earlier/Later are kept.
- AC-7: A library file from before this spec opens with all its songs still saved.
- AC-8: The song page's Save button saves the song with the current link and sync, then reads "Saved" with `aria-pressed="true"`. Pressing it again unsaves it.
- AC-9: Remove on a library tile asks first, then the tile is gone, and opening the song again is instant.

## Plan

**Backend.**
- `library.py`:
  - A `saved` column, added to older files with default 1.
  - `cache_song` (replaces `save_song`): new rows get `saved = 0`; a newer copy keeps `saved`, video, and sync.
  - `save_song_to_library` and `unsave_song`; `unsave_song` clears video and sync.
  - `replace_lines` stores refilled lines.
  - `list_songs` and `saved_ids` return saved songs only, and `save_playback` updates only saved rows.
  - `remove_song` is removed.
- `schemas.py`: `SongVersionsResponse.saved`.
- `translation/chunks.py`: `request_in_chunks` takes an optional whole-song context, so the wanted lines can be a few lines of a longer song.
- `song.py`: `missing_lines` and `fill_missing_lines(versions, translators)`, which send only the missing lines and return the versions with any newly passing lines.
- `app.py`:
  - Song-versions refills a cached song with missing lines (quietly, with log counts) and caches every new open.
  - New `PUT`/`DELETE /api/songs/{id}/saved`; `DELETE /api/songs/{id}` is removed.

**Frontend.**
- `api.ts`: `saveSong` and `unsaveSong` (replacing `removeSavedSong`), and the `saved` field checked on the reply.
- `types.ts`: `SongVersions.saved`.
- `SongPage.tsx`: the Save/Saved button. The song page keeps the current video id (reported by `PlayerBar`) and the sync, so Save sends both.
- `App.tsx`: Remove uses `unsaveSong`; the timing text changes.

**Tests.** The spec 009 and 012 tests that relied on "opening saves" open and then save. New tests cover AC-1 to AC-9 (backend in `test_library.py`, page in `App.test.tsx` and `PlayerBar.test.tsx`).

**Side effects.** Existing library files gain the column on first use. Nothing else outside the app.
