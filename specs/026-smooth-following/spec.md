# 026 — Smooth following: steady scroll, one line rhythm, a lit sung line

Status: approved (2026-11-20, after the user compared options in the mockup)

## Goal

Following a song should feel smooth and calm to look at. Today the lyrics sit still, then jump a few lines at once. The sung row fades out while the next fades in. Wrapped lines in different columns don't line up. This spec keeps the sung line in one steady place, gives every column the same line rhythm, and lights the sung line the way the home page's hero line is lit. The user tried these in a mockup first (https://claude.ai/artifact/EyjxCkgfs4CfsjMcXxc6ib).

## In scope

- **Steady following.** The sung line sits about 35% down the lyrics area. Each new line glides there over about 0.45 s with an ease-out curve. This replaces spec 018's "stay still until 60%, then glide to 20%" (the user's choice, 2026-11-20).
- **One line rhythm.** All four columns share one line height, so the wrapped lines of a row sit side by side across the columns. The first lines of a row share a baseline without the per-column `--shift` nudges. Density stays the same or gets slightly denser: row padding stays 0.5rem (0.75rem in Focus mode and on phones), and nothing is added between rows.
- **Lit sung line.** Every column of the sung row turns `--accent` pink with a soft text glow in `--accent-glow`: strongest on the original (like the home hero line), lighter on the other three. There is no box or background tint. Text fades between colours in about 0.35 s. This replaces the tinted box, and reverses spec 018's "no glow on the sung line" (the user's choice, 2026-11-20; if learners find it distracting, it changes).
- **Sliding marker.** A slim rounded accent bar at the left edge of the sung row glides from the old row to the new one and resizes to fit it. It is the shape cue, so the sung line is never shown by colour alone.

## Out of scope

- Word-by-word timing, and a progress bar for each line. LRCLIB only gives line timings, so a bar would not follow the words and could mislead (the user's choice, 2026-11-20).
- Dimming the other rows, or enlarging the sung line (spec 018 decided against these).
- Changing font sizes, colours, column widths, or the verse divider.
- Settings for the speed or position.

## Rules

- **Following:**
  - Following runs on every change of sung line while following is on.
  - A new glide starts from wherever the last one is, so quick lines never stack up or snap back.
  - Near the top or bottom of the song, the target is held within what can actually be scrolled.
- **What stays:**
  - Scrolling the lyrics yourself still pauses following, and "Back to the current line" still resumes it (spec 018). The app's own glides never count as the learner scrolling.
  - The lead-in (0.3 s), the next-line dot, Loop line, hidden columns, and Focus mode work as today. Changing the layout (Focus mode, the phone tabs) moves the glow and the scroll to the sung row again.
- **The lit line and marker:** they show only when a line is being sung. The sung row stays marked in the page for screen readers as today (`aria-current`). The pink text keeps its contrast on both themes' backgrounds (the same pair the hero line uses).
- **Reduced motion:** the scroll and the marker jump, and the colour changes at once.
- **Line rhythm:** it applies to normal, Focus, and phone layouts. A covered cell's Show button keeps the row's rhythm.
- **Design:** only existing colour tokens (`--accent`, `--accent-glow`); no new colours or shadows.

## Security

- **Untrusted input:** none new. Timings come from the already-checked song reply.
- **Outside services:** nothing new is sent anywhere.
- **Logs and disk:** nothing is logged or stored.

## Acceptance checks

- AC-1: The scroll target puts the sung row about 35% down the view, held within the scrollable range.
- AC-2: Every change of sung line starts a glide while following is on. None starts while it is paused, and a new glide replaces one still running.
- AC-3: The glide eases out over about 0.45 s. Under reduced motion the view jumps.
- AC-4: The app's own glides never pause following. The learner scrolling still does, and "Back to the current line" resumes it.
- AC-5: All four columns share one line height in normal, Focus, and phone layouts, and the stylesheet has no `--shift` nudges.
- AC-6: Exactly one marker shows while a line is sung, placed and sized to the sung row. None shows with no audio or no timings. It glides between rows, or jumps under reduced motion.
- AC-7: Every column of the sung row is `--accent` with an `--accent-glow` text glow, strongest on the original. The row has no background tint or box.
- AC-8: Loop line, the next-line dot, hidden columns, and Focus mode still pass their existing tests.

## Plan

Branch `claude/026-smooth-following`, from `main` (spec 014 is merged into it when that PR lands).

- `lyrics/followLine.ts`: `scrollTarget(rowTop, viewHeight, maxScroll)` puts the row at 35%, clamped. `glidePosition(from, to, elapsedMs)` gives the ease-out curve over 450 ms. The hook runs the glide with `requestAnimationFrame` and cancels a running one; under reduced motion it scrolls once. The glides use `scrollTo`, and only wheel, touch, and scroll keys pause following, as today.
- `lyrics/VersionsTable.tsx`: wraps the table with a `SungLineMarker`, which measures the sung row (and again when the table resizes) and places the bar with `transform` and `height`.
- `styles.css`:
  - One `--line-box` for normal and phone layouts, a larger one for Focus mode. Cells use `vertical-align: baseline`, and the seek button becomes `inline-flex`, so the cell's baseline is its first line.
  - The `--shift` nudges are removed.
  - The sung row's text colour and glow change, and the row tint and box go.
  - The marker's styles are added.
- Tests:
  - `followLine.test.ts`: the 35% target, the clamp, the glide curve, a new glide replacing a running one, and reduced motion.
  - `PlayerBar.test.tsx`: following and its pause.
  - `VersionsTable` marker: in an existing song page test.
  - `styles.test.ts`: the shared line box, no `--shift`, and the lit row.
