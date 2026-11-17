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
| 001 | Paste lyrics, get four versions: Original, Hiragana, Romaji, English (also sets the stack) | done |
| 002 | Lyrics from a link | approved |
| 003 | Reading page: the four versions side by side, hide/show, hover | not started |
| 004 | Song library: save and reopen songs | not started |
| 005 | MP3 player: attach one track to a song | not started |

## Open questions for later specs

From the Impeccable critique of the spec 001 page (2026-11-16). The user chose to carry these to spec 003:

- Is the reading page for reading or for studying? A study mode could hide a row (for example the English) so the learner can test themselves.
- Should the paste form collapse once a result exists, so the song fills the screen?
- Make the Japanese the visual primary: a larger Original and Hiragana, English in the muted color, a gap between the Japanese pair and the Latin pair.
- Blank lines should read as verse breaks: no number, no divider, a larger gap, and line numbers that count only lyric lines.
- Show progress during a long wait (seconds elapsed), and allow cancelling a request.
- Explain the limits up front, and say what "Reading not verified" means.
- Consider dropping the repeated row labels after the first group, and stacking label above value on narrow screens.
