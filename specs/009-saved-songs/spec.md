# 009 — Saved songs, and paste removed

Status: approved (by the user, 2026-11-18)

## Goal

Every song the learner opens is saved on their computer. Opening it again is instant and uses no Gemini quota, and the page lists the saved songs so the learner can come back to them.

## In scope

- **Saved automatically.** After a song opens successfully, it is saved: the song (LRCLIB id, track, artist, album, duration) and all its lines with their four versions. No save button.
- **Not saved when incomplete.** A song with any "Not available" line is not saved, so the next open asks Gemini again.
- **Opening a saved song** returns it from the database: no LRCLIB request, no Gemini call, no key needed. Its "last opened" time is updated.
- **Your songs.** A list on the page, most recently opened first, showing track, artist, and duration. Clicking one opens it. Each has a "Remove" button.
- **Search results** say "Saved" for songs already saved.
- **Timing line.** A song opened from the database shows "Opened from your songs in 0.0 s".
- **Paste removed** (decided by the user, 2026-11-18). Deleted with their tests: `POST /api/versions`, `read_paste`, the `empty_input` and `no_japanese` codes, the paste form and the "Paste the lyrics instead" link. When nothing is found, the page says "No song found for that name. Try the title and artist." The 256 KiB body cap stays for every route.
- **Fewer Gemini requests** (added by the user, 2026-11-18, after hitting the free-tier limit): chunks grow from 15 to 40 lines, so most songs take 1 or 2 calls instead of 4 or more. The model moves from Gemini Flash to Flash-Lite, whose free daily limit is far higher (about 500 requests against 20).
- **Storage:** one SQLite file through Python's built-in `sqlite3` (no new dependency). Its path is a setting, default `data/lyrx.db` at the repo root, which `.gitignore` already covers (`*.db`).

## Out of scope

- Accounts and per-person libraries (spec 012 adds a user to each saved song; nothing here assumes one learner forever).
- Refreshing a saved song's versions, editing them, folders, search inside the library, export.
- Playback and timings (spec 010).

## Inputs and outputs

- `POST /api/song-versions` `{ "id": 101 }`: as in spec 008. A saved song comes from the database.
- `POST /api/song-search`: each result gains `"saved": true | false`.
- `GET /api/songs` → `200 { "songs": [ { "id", "track", "artist", "album", "durationSeconds" } ] }`, most recently opened first. No lines.
- `DELETE /api/songs/{id}` → `204`, or `404 song_not_found` when the song is not saved. `id` is an integer ≥ 1; otherwise `400 invalid_request`.

## Rules

1. **Open order** (changes spec 008 rule "Open a song" 2): look in the database first. A saved song is returned at once. Only an unsaved song needs the Gemini key (`503 server_not_configured`), then LRCLIB and Gemini as before.
2. **Save** after the reply is built, in one transaction. A failure to save is logged (`save_failed`, no details) and the reply is still returned.
3. **Read back with checks.** Saved lines are validated against the line shape when read. A row that fails is deleted and treated as not saved (the song is fetched again).
4. Every query uses `?` parameters, never string formatting.
5. The database and its folder are created on first use. The file stays on the learner's computer.

## Security

- **Untrusted input:** the id in the path (checked integer), saved rows (validated on read, as above).
- **Lyrics on disk:** the database holds copyrighted lyrics locally. It is gitignored and never committed; tests use a temporary database with invented lines.
- **Cross-site requests:** `DELETE` and JSON `POST` need a CORS preflight, which the server never grants, and the Host check blocks DNS rebinding, so another website cannot remove songs.
- **Logged:** route, status, code, `from_library` (true or false), the number of saved songs for the list. Never lyrics or titles. Errors never include SQL or file paths.

## Acceptance checks

Backend (pytest, temporary database, fakes; no network):

- AC-1: Opening a song saves it; opening it again makes no LRCLIB and no Gemini request and returns the same reply.
- AC-2: A saved song opens with no Gemini key set.
- AC-3: A song with a missing line is not saved; the next open calls Gemini again.
- AC-4: `GET /api/songs` lists saved songs, most recently opened first, with no lines.
- AC-5: `DELETE /api/songs/{id}` removes the song (`204`); the next open fetches it again. Unknown id → `404 song_not_found`; bad id → `400 invalid_request`.
- AC-6: Search results mark saved songs with `saved: true`.
- AC-7: A saved row with broken lines is deleted and the song is fetched again; no `500`.
- AC-8: If saving fails, the reply is still `200` and the log says `save_failed`.
- AC-9: The database path comes from `config.py`, and the folder is created when missing.
- AC-13: `POST /api/versions` is gone (`404 not_found`), and no code or test refers to the paste route.

Page (Vitest):

- AC-10: "Your songs" lists the saved songs; clicking one opens it.
- AC-11: "Remove" removes the song from the list.
- AC-12: Search results show "Saved" for saved songs, and a song opened from the library shows "Opened from your songs in …".
- AC-14: The page has no paste form or paste link; "No song found" shows the new hint.

## Plan

- **Backend:** new `library.py` (the SQLite file: find, save, list, remove, which ids are saved); `app.py` gains `GET /api/songs` and `DELETE /api/songs/{id}`, and the open route looks in the library first; `song_search.py` marks saved results; `config.py` gets `DATABASE_PATH`. Paste removed from `app.py`, `lines.py`, `errors.py`, `schemas.py`.
- **Frontend:** new `SavedSongs.tsx` ("Your songs" with Remove); `api.ts` gains `listSavedSongs` and `removeSavedSong`; the paste form and link go; "Saved" on results; the timing line knows a library open.
- **Tests:** a temporary database for every test; `test_library.py`; route tests for the new rules; paste tests deleted or moved to the open route.
