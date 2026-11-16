# Specs

The source of truth. Code exists only because an approved spec here says so.

## Workflow

1. Copy `_template/` to `NNN-short-name/`.
2. spec-writer fills in `spec.md` (`Status: draft`).
3. The user approves it and sets `Status: approved`.
4. The coordinator writes `plan.md` and `tasks.md` and explains them.
5. The agent loop builds it (see `AGENTS.md`), the explainer writes a walkthrough, then a PR is opened.
6. After the user merges the PR, set `Status: done`.

## Index

| # | Spec | Status |
|---|---|---|
| 001 | Paste lyrics, get four versions: Original, Hiragana, Romaji, English (also sets the stack) | draft |
| 002 | Lyrics from a link | not started |
| 003 | Reading page: the four versions side by side, hide/show, hover | not started |
| 004 | Song library: save and reopen songs | not started |
| 005 | MP3 player: attach one track to a song | not started |
