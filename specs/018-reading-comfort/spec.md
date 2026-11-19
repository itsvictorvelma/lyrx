# 018 — Reading comfort: calm following, tighter rows

Status: done (merged in PR #36, 2026-11-19)

## Goal

Reading along should be easy on the eyes. Today the song page re-centres on every line, the sung line glows, and every other row is dimmed. The rows are tall, and the columns spread across a wide screen. That is fine for singing along, but tiring for a learner who reads, glances back at a word, and reads again. The user approved the "Proposed" boards of the mockup as the baseline. People will review it later.

## In scope

- **Calm following.** The lyrics stay still while the sung line moves down the screen. They glide only when the sung line passes 60% of the lyrics area's height (or is above it), and then stop with that line 20% from the top. Under reduced motion they jump instead of gliding.
- **Lead-in.** A line becomes the sung line 0.3 s before its start time, so the eyes arrive in time.
- **Next line.** The next sung line (across a verse gap too) has a small accent dot at its left edge. The dot is decorative, so it isn't announced.
- **Gentle highlight.** The sung line keeps the accent-soft background and the 3px accent bar. There is no glow, and other rows are no longer dimmed while audio plays.
- **Romaji stays bright.** Romaji uses the main text colour, like the original and hiragana, because it is the pronunciation. Only English uses the dim colour.
- **Tighter rows.** Row padding drops from 0.875rem to 0.5rem. A verse gap is a thin `--line` divider with a little space, not a 2rem empty band.
- **Narrower reading width.** The table is capped at 72rem (was 74rem), with columns 27 / 26 / 25 / 22 %.
- **Sizes.**
  - Normal: original 20px, hiragana 17px, romaji 16px, English 15px.
  - Focus: original 26px, hiragana 21px, romaji 19px, English 17px.
  - The first lines of a row still share a baseline (the existing `--shift` approach, recomputed for these sizes).
- **Focus mode uses the screen.** The table is capped at 81rem (was 88rem), with row padding 0.75rem, so about 12 lines fit on a laptop screen.
- **Scroll to pause.** If the learner scrolls the lyrics while a line is being sung (mouse wheel, touch, or the keyboard's scroll keys inside the lyrics), following pauses. A "Back to the current line" button appears at the bottom of the lyrics. Pressing it jumps back to the sung line and resumes following. Opening another song starts with following on.

## Out of scope

- Hiding a column, looping a line, keyboard shortcuts (spec 015).
- Changes to the phone layout beyond what the shared rules above change.
- Choosing the sizes or speed in settings.

## Inputs and outputs

None. Page only.

## Rules

1. The lead-in, the 60% / 20% marks, and the row and size values are named constants or CSS rules, not scattered numbers.
2. The scroll decision is a pure function (sung row position, view position and height → where to scroll, or nowhere), so it can be tested without a browser.
3. Only the learner's own scrolling pauses following; the page's own scroll never does.
4. Colours stay the approved tokens; text still passes 4.5:1 in both themes.

## Security

No new input, outside service, or log. Lyrics still render as text.

## Acceptance checks

- AC-1: The scroll decision returns nothing while the sung row is within the top 60% of the view, and returns "row top minus 20% of the view" (never below 0) when it passes 60% or is above the view.
- AC-2: A line is the sung line from 0.3 s before its start time.
- AC-3: The row after the sung line (across a verse gap too) is marked as the next line; no other row is.
- AC-4: The styles have no glow on the sung line, don't dim other rows while playing, and give romaji the main text colour and English the dim colour.
- AC-5: Scrolling the lyrics while a line is sung shows "Back to the current line". Pressing it hides the button and following resumes.
- AC-6: The styles use the new sizes, row padding, widths, and the verse divider, in normal and Focus mode.

## Plan

- `frontend/src/lyrics/followLine.ts` (new): `scrollTarget(...)`, a pure function, and `useFollowLine(viewRef, currentLine, following)`, which scrolls the lyrics area when needed (smooth, or instant under reduced motion).
- `playback.ts`: `LEAD_IN_MS` and its use in `currentLineIndex`'s caller.
- `SongPage.tsx`:
  - It owns the lyrics area's ref and a `following` flag.
  - Wheel, touch, and scroll-key events on the lyrics area pause following.
  - It shows the "Back to the current line" button.
  - It uses `LEAD_IN_MS`.
- `VersionsTable.tsx`:
  - It loses its own `scrollIntoView` and the `playing` prop.
  - It marks the `next` row.
- `styles.css`: the table rules above, the next-line dot, the divider, and the back button. The glow and dim rules are removed.
- Tests: new `followLine.test.ts` (AC-1). `PlayerBar.test.tsx` gets AC-2, AC-3, and AC-5, and replaces the old dimming check. `styles.test.ts` gets AC-4 and AC-6.
