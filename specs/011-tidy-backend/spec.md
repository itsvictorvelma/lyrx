# 011 — Tidy the backend

Status: approved (by the user, 2026-11-18: "go ahead and do backend cleanup along with checking whether we need cleanup.py or not … simple is better ALWAYS")

## Goal

A newcomer can tell what every backend file is for from where it sits. No change in what the app does.

## In scope

- **Folders by area:** `lyrics/` (LRCLIB, search, lines, Japanese detection), `translation/` (chain, chunks and retries, prompt, checks, Groq, Gemini, result shapes), `server/` (body limit, Host check, crash guard, request log). App-wide files stay at the top.
- **Schemas split:** `schemas.py` keeps only what the page sends and receives. Each outside service's reply shape moves into that service's file; internal result shapes go to `translation/results.py`.
- **Thin files merged:** `song_versions.py` + `four_versions.py` → `song.py`; `kana.py` + `looks_japanese.py` + Japanese detection → `lyrics/japanese.py`; `retries.py` → `translation/chunks.py`; `http_clients.py` → each client next to its service.
- **`lyric_cleanup.py` deleted** with its tests. It was written for pasted lyrics; on 88 real Japanese songs from LRCLIB (3,972 lines, checked 2026-11-18) it changed 0 lines. Trimming lines and collapsing blank lines stay, in `lyrics/lines.py`.
- **Tests** move into the same folders. README folder map and AGENTS.md layout rule updated.

## Out of scope

- Any change to routes, replies, error codes, prompts, or the page.

## Security

No change. The same guards run in the same order.

## Acceptance checks

- AC-1: Every test that existed before still exists and passes, except the cleanup tests and the paste-era line tests (replaced by tests of `read_lyrics`).
- AC-2: `schemas.py` holds only request, reply, and error shapes.
- AC-3: `lyric_cleanup.py` and `CLEANUP_SPLIT_LENGTH` are gone.
- AC-4: A real song opens end to end (search, open, reopen from the library).

## Plan

Moves with `git mv` so history follows each file; imports rewritten by a one-off script; then the merges above. Checked by `scripts/check-quiet.sh`, a per-file test count against main, and one real run (only counts printed).
