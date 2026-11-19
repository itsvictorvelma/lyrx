# 017 — Kana rain while a song loads

Status: approved

## Goal

Finding and translating a song takes 10–30 seconds. Today the learner watches shimmering placeholder rows. Give them something fun to look at that fits the app: columns of pink kana falling down the screen, "hacker" style, with the steps still readable on top. Asked for by the user on 2026-11-19, to come before spec 015.

## In scope

- **Kana rain** fills the loading screen behind the steps. Columns of katakana and hiragana fall at slightly different speeds. The head of each column is bright and the trail fades out.
- **Colours follow the theme**, with no new colours:
  - Dark: `--accent` characters on `--bg`.
  - Light: the light `--accent` (deep pink) on the light `--bg`.
  - The trail fades toward `--bg`.
  - It switches when the theme button is pressed during a load.
- **A real word now and then.** Every few seconds one column spells a short invented-list word top to bottom in kana (for example うた, こえ, よる, ほし, そら, ゆめ), drawn brighter, so a learner can catch it. The list is a short fixed array in the code, not lyrics.
- **Steps on a terminal card** (added at the user's request, 2026-11-19: "cyberpunk terminal vibe"). The steps, their marks, and the seconds sit on a `--surface` card in the centre, above the rain, so they keep their contrast.
  - The card has square corners, an `--accent` border with the accent glow, and a title bar (`lyrx@歌詞 ~ translate`).
  - Its text uses the system monospace font.
  - The status line starts with a `>` prompt and ends with a blinking block cursor.
  - Step marks are text: `[ OK ]` for done, a braille spinner `[ ⠹ ]` for in progress, and `[ -- ]` for waiting. They are hidden from screen readers, which still hear "(done)", "(in progress)", "(waiting)".
  - Under reduced motion the cursor and spinner stand still.
- **The placeholder rows are removed.** The rain replaces them.
- **It stops cleanly.** The animation stops and its timer is released as soon as the song opens, an error shows, or the learner leaves the page.
- **Reduced motion.** When the system asks for reduced motion, the rain is a still field of faded kana, drawn once, with no animation.
- **Phone.** Fewer, larger columns at narrow widths. The card stays centred and readable.

## Out of scope

- Using the song's own lyrics in the rain (they don't exist until the translation is done).
- Sound, progress percentages, or cancelling a search (cancelling is a separate idea in the specs index).
- The rain anywhere other than the loading screen.

## Inputs and outputs

None. Page only; no server or API change.

## Rules

1. Drawn on one `<canvas>` with `requestAnimationFrame`, about 20 frames a second. No new dependency.
2. The canvas is decorative: `aria-hidden="true"`, and the status text stays the only thing screen readers hear.
3. Colours are read from the CSS tokens at runtime (`getComputedStyle`), never written as hex values in the script.
4. The canvas matches the screen's pixel density, so the kana are sharp, and resizes with the window.
5. The words list and timing numbers are named constants in the component file.

## Security

- **Untrusted input:** none; the rain draws only a fixed set of characters from the code.
- **Outside services:** none.
- **Logs and disk:** nothing new.

## Acceptance checks

- AC-1: While a song loads, the loading screen shows the rain canvas (decorative, `aria-hidden`) behind the steps card, and no placeholder rows.
- AC-2: The steps and the seconds still read as before ("Finding the song…", then "Getting the lyrics and translating…") and are announced by the status line.
- AC-3: When the song opens or an error shows, the animation frame loop is cancelled (no frame is requested after unmount).
- AC-4: Under reduced motion, the rain draws once and requests no animation frames.
- AC-5: The rain takes its colours from `--accent` and `--bg` of the current theme, and changes when the theme changes.
- AC-6: The step card's text still passes 4.5:1 contrast in both themes (the existing contrast test covers `--surface`).
- AC-7: The card shows the title bar, the prompt, and the text marks `[ OK ]` and `[ -- ]`. Marks, prompt, and cursor are `aria-hidden`, and the spinner does not move under reduced motion.

## Plan

- `frontend/src/lyrics/KanaRain.tsx` (new): the canvas, `startRain` (draw loop, resize, theme watcher, still mode), and `readRainColors`.
- `SearchProgress.tsx`: the rain plus the terminal card; text step marks and a braille `Spinner`. The placeholder rows are removed.
- `styles.css`: `.search-progress`, `.kana-rain`, `.progress-card`, `.terminal-bar`, the step marks, and the cursor `blink` keyframes; the shimmer styles are removed.
- Tests: `KanaRain.test.tsx` covers AC-1 to AC-5 and AC-7, with a fake canvas and frame queue. AC-6 is covered by the existing `styles.test.ts` contrast check.
