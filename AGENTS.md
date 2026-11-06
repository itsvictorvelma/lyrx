# Lyrx

Lyrx is one local app for rehearsing a Japanese song. The learner asks for the lyrics. The page shows Original, Hiragana, Romaji, and English, and can play one MP3 the learner attaches. There is no login.

[How the code fits together](docs/codebase.md) is the map of the code that exists today. Measured Groq limits are in [benchmarks/](benchmarks/). Files under [specs/](specs/) are older feature write-ups. They are not this plan. Do not edit them unless Victor asks.

## What the learner can do

- Read a saved song as four documents, in this order: Original, Hiragana, Romaji, English.
- On a wide window the four documents sit side by side and the page scrolls once. Hide and Show fade that column's text and leave the column in place. On a narrow window the same four names are tabs.
- Hover or focus marks the same line across the open documents. Playback does not mark a line or move the page.
- Ask for a song in one chat, read the draft, and save it. The chat transcript is not stored. An unsaved draft is lost on refresh.
- Attach one MP3. The song stays readable with no audio.
- Hide any document, including the last one. The choice lasts for the browser session.

The player bar has play/pause, seek, elapsed time and duration, back and forward 10 seconds, volume and mute, and the speeds 0.75×, 1×, and 1.25×. With no MP3, the bar says that no audio is attached.

## How lyrics are made

There is one lyric path. The server calls Groq through Swytchcode method `groq.chat.completions.create`. The Groq key stays in the Swytchcode connection. The browser never sees it.

A named song takes its original lines from LRCLIB. Groq fills the kanji readings and the English, in groups of lines. Kana already in the line is kept. Romaji is spelled from the hiragana. A request that does not match a recording asks Groq for the whole draft. The server checks the draft before the page treats it as lyrics. An invalid or oversized reply creates no song and does not start a second completion.

There is no LangChain, no LangGraph, and no authoring package. Do not add them. Do not add a second offline draft path.

The free-plan token ceiling and the measured call are in [benchmarks/groq-token-usage.md](benchmarks/groq-token-usage.md). A prompt that would pass 8,000 tokens in a minute is refused with `generation_too_large` and Groq is not called.

## Boundaries

- No accounts, cookies for identity, or user profiles.
- No public host. Generation and upload stay on this install.
- No line timing, audio scan, follow-scroll, word or mora timing, looping, autoplay, tempo control, or microphone.
- No lyric-file import. `POST /api/import` is not registered.
- The only upload is one MP3. Audio is a file on disk, never a database blob.
- SQLite for this install, through SQLAlchemy. Schema changes go through Alembic only. PostgreSQL comes before any public multi-user deploy.
- Generated text is rendered as React text, never as HTML.
- No analytics and no second model provider.

## Layout

Keep the frontend and backend split. Group code by what it does. Do not add a folder for a single file.

- `frontend/src/routes/` — the page address and links
- `frontend/src/library/` — the saved-song list
- `frontend/src/lyrics/` — the four documents
- `frontend/src/player/` — the player and MP3 attach
- `frontend/src/new-song.tsx` — the chat that starts a song
- `backend/app/generation/` — the Groq draft, including the LRCLIB lookup
- `backend/app/reading.py` — hiragana and romaji
- `backend/app/routers/` — HTTP routes
- `backend/app/services/` and `backend/app/repositories/` — saved songs and the database

## API

- `GET /api/health`
- `GET /api/songs`
- `GET /api/songs/{song_id}`
- `POST /api/generations` — one draft, not saved
- `POST /api/songs` — save a draft
- `POST /api/songs/{song_id}/audio` — attach or replace one MP3
- The media URL when an MP3 is stored

A correction is another generation when the caller sends the current draft. Learn Song does not show that chat. There is no separate lyric-replace route.

A saved song has a stable id, title, artist, Japanese as the source language, English as the target language, an optional duration, and status `published`. Each line has `originalText`, `readingHiragana`, `pronunciationRomaji`, and `translationEnglish`. Indexes start at 0 and have no gaps. Timing fields are rejected. An older saved line may omit hiragana; the song still opens.

Errors use one shape: `code`, `message`, optional `details`, and `requestId`. Responses do not include stack traces, paths, SQL, or secrets.

## Where this goes

Keep improving the live Groq path and the reading screen. Do not add a graph framework.

## Not in this app

- Line start times, audio scanning, follow-scroll, word timing, looping, autoplay, or a tempo control
- Recording, a microphone, or pitch scoring
- Accounts and a public multi-user host
- Stored chat transcripts and a streaming token display
- Public uploads, moderation, or transcoding
- Playlists, recommendations, sharing, payments, or analytics
- YouTube, Spotify, or another lyrics source besides the LRCLIB lookup this path already uses
- A second model provider, or a paid Groq tier
- PostgreSQL until a public multi-user deploy
- Another language pair

## Development

- `scripts/check.sh` runs the checks CI runs.
- Work is tracked as GitHub issues from the agent-task template.
- Skills in `.cursor/skills/`: `plan-tickets`, `dispatch-ticket`, `review-pr`. They load when you ask for them by name.
- Two failed `scripts/check.sh` runs on a branch, then stop. Only Victor resets that count.
- Only Victor merges pull requests and edits `specs/`. Edit this file only when Victor asks.
- Default tests must not call Groq.
