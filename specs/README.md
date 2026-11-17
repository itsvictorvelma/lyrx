# Specs

The source of truth. Code exists only because an approved spec here says so.

## Workflow

1. Copy `_template/` to `NNN-short-name/`.
2. spec-writer fills in `spec.md` (`Status: draft`).
3. The user approves it and sets `Status: approved`.
4. The coordinator writes `plan.md` and `tasks.md` and explains them.
5. The agent loop builds it (see `AGENTS.md`), the explainer writes a walkthrough, then a PR is opened.
6. After the user merges the PR, set `Status: done`.

Status values: `draft` → `approved` → `done`. When the user drops a spec, its status becomes `shelved`; the file stays as history.

## Index

| # | Spec | Status |
|---|---|---|
| 001 | Paste lyrics, get four versions: Original, Hiragana, Romaji, English (also sets the stack) | done |
| 002 | Lyrics from a link | shelved |
| 003 | Song search: type a name, get the four versions (LRCLIB, local readings, Gemini English) | approved |
| 004 | Song library | not started |
| 005 | Audio player: YouTube embed with line highlighting from LRCLIB timings (moved from 003), MP3 upload optional | not started |
| 006 | Hosting for invited users | not started |
| 007 | Compact reading layout | draft |

## Open questions for later specs

From the Impeccable critique of the spec 001 page (2026-11-16). The user first chose to carry these to spec 003. They now feed spec 007 (compact reading layout):

- Is the reading page for reading or for studying? A study mode could hide a row (for example the English) so the learner can test themselves.
- Should the paste form collapse once a result exists, so the song fills the screen?
- Make the Japanese the visual primary: a larger Original and Hiragana, English in the muted color, a gap between the Japanese pair and the Latin pair.
- Blank lines should read as verse breaks: no number, no divider, a larger gap, and line numbers that count only lyric lines.
- Show progress during a long wait (seconds elapsed), and allow cancelling a request.
- Explain the limits up front, and say what "Reading not verified" means.
- Consider dropping the repeated row labels after the first group, and stacking label above value on narrow screens.
