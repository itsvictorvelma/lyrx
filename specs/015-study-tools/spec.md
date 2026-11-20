# 015 — Study tools: hide a column, loop a line, keyboard shortcuts

Status: done (merged in PR #42, 2026-11-20)

## Goal

Turn the song page from something you read into something you practise with. The learner can cover a version to test themselves, repeat one line until they can sing it, and do both without leaving the keyboard.

## In scope

- **Hide a column**: cover the Hiragana, Romaji, or English column, and reveal one cell at a time.
- **Loop a line**: repeat the line being sung until the learner stops the loop.
- **Keyboard shortcuts** for the song page, with a short list the learner can open.

## Out of scope

- Hiding the Original column (it is what the learner is studying).
- Looping several lines, a slower playback speed, or an A–B range picked on the slider.
- Quizzes, scores, or progress tracking.
- Saving study settings per song or on the server (that waits for accounts, 014).
- Shortcuts anywhere other than the song page.

## Rules

### Hide a column

- The song head and the Focus strip get a "Hide" group with three toggle buttons: かな, Romaji, EN (`aria-pressed`). On a phone the group sits next to the column tabs.
- A hidden column keeps its header and its width. Each of its cells is replaced by a "Show" button with the same row height, so rows don't jump.
- Clicking a covered cell reveals that one cell. Revealed cells stay revealed until the column is shown again or hidden again.
- Which columns are hidden is remembered on this device (browser storage, wrapped in try/catch) and applies to every song. All columns are shown by default.
- A covered cell's button has an accessible name such as "Show romaji for: 君の声が" (the line's original text). Covered text is not in the page at all, so a screen reader can't read it out early.

### Loop a line

- The player bar gets a "Loop line" toggle (`aria-pressed`), disabled when the song has no line timings or no line is being sung.
- While looping, the looped line counts as the sung line (for the highlight and for previous/next), even during the lead-in to the line after it.
- Turning it on loops the line being sung: from its start to the next timed line's start (the end of the song for the last line), with the sync offset applied.
- When playback passes the loop's end, it jumps back to the loop's start. This is checked on the existing 200 ms poll, so a loop may run up to about 200 ms past the line's end.
- Previous line, next line, and clicking a line's original text move the loop to that line. Dragging the position slider turns the loop off.
- The looped row gets a visible mark that is not color alone (a small loop icon by the line). Following the sung line keeps working as it does now.
- Opening another song turns the loop off. The loop is never saved.

### Keyboard shortcuts

| Key | Does |
|---|---|
| Space | Play or pause |
| ← / → | Previous / next line |
| L | Loop line on or off |
| H / R / E | Hide or show Hiragana / Romaji / English |
| F | Focus mode on or off |
| Esc | Leave Focus mode |
| ? | Show or hide the shortcut list |

- Holding a key down fires its shortcut once.
- Shortcuts are ignored while focus is in a text field, a select, or the position slider, and while Ctrl, Cmd, or Alt is held, so typing and browser shortcuts keep working.
- Space is also ignored on a focused button or link, because the browser already presses those with Space.
- A shortcut whose button is disabled does nothing (for example ← without timings).
- A "Keyboard shortcuts" button (keyboard icon) in the player bar opens the same list. The list is a small panel with the table above, closed by Esc, ?, or its close button. Focus moves into it when it opens and returns to where it was when it closes (the button, when opened from it).
- Arrow up and down keep scrolling the lyrics as they do now.

## Security

- Untrusted input: none new. Covered and revealed cells still render lyrics as text.
- What is sent to an outside service: nothing new.
- What touches disk: three booleans for the hidden columns in browser storage. No lyrics.

## Acceptance checks

- AC-1: Pressing the Romaji hide toggle replaces every romaji cell with a "Show" button and removes the romaji text from the page; pressing it again brings the text back.
- AC-2: Clicking one covered cell reveals only that cell.
- AC-3: Hidden columns are remembered after a reload, and the page still works when browser storage throws.
- AC-4: With Loop line on, playback past the line's end jumps back to the line's start (fake player clock).
- AC-5: Next line while looping moves the loop to the next line; dragging the slider turns the loop off.
- AC-6: Loop line is disabled when the song has no timings.
- AC-7: Space, ←, →, L, H, R, E, F, Esc, and ? each do what the table says.
- AC-8: Shortcuts do nothing while typing in the search box or the YouTube link field, or while Ctrl/Cmd/Alt is held; Space on a focused button presses only that button.
- AC-9: The shortcut list opens from its button and from ?, closes with Esc, and gives focus back to the button.

## Plan

New files in `frontend/src/lyrics/`, each with its test next to it:

- `hiddenColumns.ts`: `useHiddenColumns()`, which holds the hidden columns (read from and written to browser storage) and the revealed cells, plus `toggleColumn` and `revealCell`.
- `lineLoop.ts`: `loopRange(lines, lineIndex, offsetMs, durationMs)`, a pure function.
- `shortcuts.ts`: `shortcutFor(event)` (key → action, or null when the key is ignored) and `useShortcuts(actions)`, which adds one `keydown` listener on `window`.
- `ColumnButtons.tsx`: the "Hide" group, and the phone tabs moved out of `SongPage.tsx` (they share the column labels).
- `ShortcutList.tsx`: the shortcut panel (`role="dialog"`, focus in on open and back out on close).
- `fakeSongPage.tsx`: the fake YouTube player and fake server, moved out of `PlayerBar.test.tsx` so `SongPage.test.tsx` can reuse them.

Changed:

- `SongPage.tsx` holds the loop line and whether the shortcut list is open. It wires up the shortcuts and passes `hidden`, `revealed`, and `loopLine` to the table. A small effect on `progress.timeMs` seeks back when playback passes the loop's end. Line moves (previous, next, clicking a line) move the loop; the slider turns it off. The page is keyed per song, so opening another song resets the loop.
- `VersionsTable.tsx`: covered cells become "Show" buttons, and the looped row gets a loop icon and the class `looped`.
- `PlayerBar.tsx` and `PlayerControls.tsx`: the "Loop line" toggle and the "Keyboard shortcuts" button.
- `styles.css`: covered cells, the loop mark, and the panel, using the existing tokens only.
- `README.md` folder map.

Spec bookkeeping in the same PR: 019 marked done, and 015 and 019 rows updated in `specs/README.md`.
