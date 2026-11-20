# Specs

The source of truth. Code exists only because an approved spec here says so. See "How we work" in `AGENTS.md`.

1. Copy `_template/` to `NNN-short-name/` and write `spec.md` (`Status: draft`, under 150 lines).
2. The user approves it (`Status: approved`).
3. Add the Plan section, build, review once, open a PR with a "try this" list.
4. After the user merges, set `Status: done`.

Status values: `draft` → `approved` → `done`, or `shelved` when dropped (the file stays as history).

Numbers are permanent ids, never reused, because commits and PRs refer to them. Gaps are numbers that were planned and never written (004 to 006 were reserved for the old roadmap).

## Index

| # | Spec | Status |
|---|---|---|
| 001 | Paste lyrics, get four versions (also sets the stack) | done |
| 002 | Lyrics from a link | shelved |
| 003 | Song search (too large; its built code is reused by 008) | shelved |
| 007 | Compact stacked reading layout (replaced by the columns layout in 008) | shelved |
| 008 | Find a song: type a name, read it in four columns | done |
| 009 | Saved songs; paste removed | done |
| 010 | Two translators: Groq first, Gemini as backup | done |
| 011 | Tidy the backend: folders by area, schemas split, unused cleanup removed | done |
| 012 | Synced playback: YouTube by link and your own MP3, line highlighting from LRCLIB timings | done |
| — | Find the YouTube video automatically (needs a YouTube API key) | after 012 |
| 013 | Design pass: night-player look, library home, song page with docked player and Focus mode, phone layout | done |
| 016 | Save songs on purpose (Save button); fill in missing lines on reopen | done |
| 017 | Kana rain while a song loads | done |
| 018 | Reading comfort: calm following, lead-in, tighter rows, roomier Focus mode | done |
| 019 | Translator request limits: one overall deadline, a byte cap on Gemini replies | done |
| 015 | Study tools: hide a column, loop a line, keyboard shortcuts | done |
| 021 | Home page: hero line, large search, recent songs; library moves to /library | approved |
| 014 | Personal accounts: sign up, own saved songs, daily cap on new songs | approved |
| 020 | Deployment: Docker and Caddy on a server, settings from the environment | draft (after 014 and a few more features) |
| — | Next language | decided after 008 is in use |

## Ideas carried from the shelved specs

- Allow cancelling a long wait (the seconds already show, since 013).
- Show lines as they arrive instead of all at the end.
