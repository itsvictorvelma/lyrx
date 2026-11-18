# 007 — Compact reading layout

Status: shelved (replaced by the columns layout in 008, 2026-11-17)

## Goal

Show each lyric line as one compact block (the Japanese first and largest, the English quiet) so a whole song can be read by scrolling a little. Today each line is four labeled rows stacked on top of each other. One line fills the screen, and a learner who pasted 4 lines thought only the first one had been translated.

## In scope

- A new look for the result of spec 001. Page only (`frontend/`). The server and the reply shape do not change.
- One compact group per lyric line: Original (largest), then Hiragana, then Romaji, then English in the muted color.
- The row names ("Original", "Hiragana", "Romaji", "English") shown once, in a legend above the result, instead of on every line. Each row keeps a label that screen readers announce but the eye does not see.
- A visible line number on each lyric line.
- Blank lines shown as verse breaks: a larger gap, no number, no empty group. Line numbers count only lyric lines.
- The result heading counts only lyric lines.
- After a result, the paste form folds away into one "Paste new lyrics" button, so the song fills the screen.
- Narrow screens: the groups stack and wrap with no horizontal scroll.

## Out of scope

- Study mode: hiding or showing a row, testing yourself (a later spec).
- Showing progress during the wait (seconds elapsed) and cancelling a request.
- Saving songs (spec 004) and audio (spec 005).
- Side-by-side columns, hover highlight, tabs, furigana placed over each kanji.
- Explaining what "Reading not verified" means (see **Open questions**).
- The link form of spec 002. This spec is built before spec 002's page work; how the two fit together is an open question.
- Any server, API, or reply change. Any new dependency, color, or UI library.

## Inputs and outputs

Input: the same list of lines the page already gets from `POST /api/versions` (spec 001). Each line has `index`, `original`, `hiragana`, `romaji`, `english`, and `readingVerified`. A blank line has all four text fields `""`.

Output: the page shows the result in the new layout.

Example (invented lyrics). The reply has five entries; entry 2 is blank:

| index | original | hiragana | romaji | english |
|---|---|---|---|---|
| 0 | 星の歌 | ほし の うた | hoshi no uta | A song of stars |
| 1 | 夜に光る | よる に ひかる | yoru ni hikaru | Shining at night |
| 2 | | | | |
| 3 | 風がふく | かぜ が ふく | kaze ga fuku | The wind blows |
| 4 | 君と行こう | きみ と いこう | kimi to ikou | Let's go with you |

The page shows roughly this (sizes and color described in brackets):

```
Four versions (4 lines)
Original · Hiragana · Romaji · English

1  星の歌                [largest]
   ほし の うた
   hoshi no uta
   A song of stars       [muted]
2  夜に光る
   よる に ひかる
   yoru ni hikaru
   Shining at night

3  風がふく              [larger gap above: new verse]
   かぜ が ふく
   kaze ga fuku
   The wind blows
4  君と行こう
   きみ と いこう
   kimi to ikou
   Let's go with you

[Paste new lyrics]       (shown above the result, where the paste form was)
```

## Rules

### Words used here

- **Lyric line:** an entry whose `original` is not `""`. A line with no Japanese (for example `We sing tonight`) is a lyric line too.
- **Blank line:** an entry whose `original` is `""`.
- **Group:** everything the page shows for one lyric line.

### One group per lyric line

- Each lyric line is one group, in the order of the reply.
- A group shows, top to bottom: its line number, the Original, the Hiragana, the Romaji, the English. The order on screen is the same as the order in the page's HTML, so screen readers read it in the same order the eye does.
- The line number sits to the left of the Original, in its own narrow column, so the four rows line up under each other.
- The Original is the largest text in the group. The plan picks the sizes; the recommendation is `1.5rem` for the Original and the normal size (`1rem`) for the other three rows.
- The English uses the muted color `--color-muted`. The other rows use the normal text color.
- A small gap separates the Japanese pair (Original, Hiragana) from the Latin pair (Romaji, English).
- The Original and the Hiragana are marked `lang="ja"`, as in spec 001, so the Japanese font stack and screen-reader voice apply.
- Groups are separated by spacing only. The plan may keep a thin `--color-border` line between groups if it reads better; this is not tested.

### Labels once, not on every line

- The visible words "Original", "Hiragana", "Romaji", "English" appear once, in a legend between the heading and the first group. The legend names the four rows in group order. Each name in the legend uses the same size and color as its row, so the legend also shows which row is which.
- No group shows a visible label.
- Each row in each group still has its label as text that is hidden from the eye but read by screen readers. The hiding uses the standard "visually hidden" CSS pattern (position, clip, and a 1px size). It must not use `display: none` or `visibility: hidden`, because those hide the text from screen readers too.

### Line numbers and verse breaks

- Each group shows its line number as visible text. Numbers start at 1 and count only lyric lines, with no gaps: blank lines are not counted.
- A blank line creates no group, no list item, and no number. The next group starts a new verse and gets a larger gap above it than the gap between groups.
- The page does not trust the server to have tidied blank lines. A blank line at the start or the end creates no gap. Several blank lines in a row create one gap.
- All groups are items of one ordered list, so a screen reader's "item 3" matches line number 3. The list's own markers are turned off, so each number shows once.

### The heading

- The result heading reads "Four versions (N lines)", where N is the number of lyric lines. One lyric line reads "Four versions (1 line)".
- When a result arrives, focus moves to this heading, as in spec 001 task T9.

### "Reading not verified"

- A line with `readingVerified: false` shows the text "Reading not verified" in its group, right after its hiragana, as in spec 001. The note is text, not color alone. A verified line shows no note.
- The note may use the muted color, because the words carry the meaning.

### The paste form folds after a result

- Before any result, and while a request is running, the paste form shows as in spec 001.
- When a result arrives, the paste form (text area, "Get four versions" button) is hidden. In its place, above the result, a button "Paste new lyrics" is shown. The waiting status line stays empty and does not need to be visible.
- Pressing "Paste new lyrics" shows the paste form again, with the text the learner last submitted still in the text area, and moves focus to the text area. The "Paste new lyrics" button goes away. The result stays on the page until the learner submits again.
- Submitting from the reopened form behaves as in spec 001: the previous result is cleared, the waiting status shows, and the next result folds the form again.
- On an error the form never folds. The text area shows with the pasted text kept and gets focus, as in spec 001. There is no "Paste new lyrics" button.
- Hidden means hidden from everyone: the folded text area is not visible and not reachable by keyboard or screen reader. Its text is kept so it comes back when the form reopens.

### Narrow screens

- The layout has no fixed-width label column (the old `5.5rem` column goes away with the visible labels).
- Long words and long Latin text wrap inside the group (`overflow-wrap: anywhere`), so a narrow window never scrolls sideways.
- Nothing in the stylesheet uses `white-space: nowrap`.
- The reviewer also checks the page by hand at a 320 px wide window. This hand check is not an acceptance check, because the test browser (jsdom) does not lay out pages.

### What does not change

- No new colors or custom properties. The stylesheet declares only the five approved colors: `--color-text`, `--color-muted`, `--color-border`, `--color-page`, `--color-error` (light and dark values).
- The Japanese font stack, the visible focus outline, the error messages, and the alert region stay as they are.
- All model output is rendered as React text. `dangerouslySetInnerHTML` is not used.

### How this changes spec 001

- Spec 001's page rule "Each group shows four labeled rows" and its AC-37 are replaced by this spec's AC-1 to AC-8. Their tests are rewritten, not deleted.
- Spec 001's heading count (all lines, blank ones included) is replaced by AC-9.
- Spec 001's AC-34 to AC-36 and AC-38 to AC-41 still hold. AC-34 and AC-36 apply before a result and while waiting.

## Security

- Untrusted input and how it is validated: the lines in the server's reply, which hold model output. The page already checks their shape in `api.ts` (spec 001); this spec does not change that. Every field is still rendered as React text, never as HTML, so text such as `<b>x</b>` shows as those characters (AC-19). The legend and labels are fixed strings in the code.
- What is sent to the Claude API or fetched from the network: nothing new. The page sends the same single `POST /api/versions` as spec 001. This spec adds no request.
- What is logged and what touches disk: nothing. The page logs nothing and stores nothing. The kept paste text lives only in the page's memory and is gone when the tab closes.

## Acceptance checks

All checks are Vitest tests with jsdom and Testing Library. `fetch` is mocked. All lyrics are invented. Unless a check says otherwise, the reply is the five-entry example under **Inputs and outputs**. "Group" means one item of the result list.

### The groups

- AC-1: The result list has exactly 4 items, one per lyric line, in reply order. In each item the text of the Original, Hiragana, Romaji, and English appears in that order in the HTML (for example item 1 holds `星の歌`, `ほし の うた`, `hoshi no uta`, `A song of stars` in that order).
- AC-2: In each group, the Original and the Hiragana text sit in elements with `lang="ja"`.
- AC-3: Between the heading and the list, a legend shows the words "Original", "Hiragana", "Romaji", "English" in that order. Outside the legend, no visible text on the page is one of those four words.
- AC-4: Each group holds the labels "Original", "Hiragana", "Romaji", "English", in that order, each inside an element that uses the visually-hidden class, and each label comes right before its row's text.
- AC-5: (stylesheet) The visually-hidden rule in `styles.css` uses `position: absolute` and `clip` (or `clip-path`) with a 1px size, and contains neither `display: none` nor `visibility: hidden`.

### Line numbers and verse breaks

- AC-6: The four groups show the visible line numbers `1`, `2`, `3`, `4` in order: the blank entry at index 2 is not counted and has no group. The group for `風がふく` (number 3) is marked as the start of a verse, and no other group is.
- AC-7: A reply of `[blank, 星の歌, blank, blank, 夜に光る, blank]` (as entries 0–5) gives exactly 2 groups, numbered `1` and `2`. Only the `夜に光る` group is marked as a verse start. No empty list item exists.
- AC-8: (stylesheet) The result list turns its own markers off (`list-style: none`). The verse-start rule gives a larger top gap than the spacing between ordinary groups.

### Heading

- AC-9: For the five-entry example, the result heading reads exactly "Four versions (4 lines)". For a reply with one lyric line and one blank line, it reads "Four versions (1 line)". In both cases the heading has focus after the result arrives.

### Look

- AC-10: (stylesheet) The Original row's `font-size` is larger than the font size of the Hiragana, Romaji, and English rows. The English row's `color` is `var(--color-muted)`. The rule for the first Latin row (Romaji) adds a top gap.
- AC-11: (stylesheet) The only custom properties declared in `styles.css` are `--color-text`, `--color-muted`, `--color-border`, `--color-page`, and `--color-error`, and no hex or `rgb(` color appears outside the two blocks that declare them.

### Reading not verified

- AC-12: A reply where line `星の歌` has `readingVerified: false` shows the text "Reading not verified" inside that group, after its hiragana text and before its romaji text. No other group shows that text.

### The paste form folds

- AC-13: Before any submit, the text area labeled "Japanese lyrics" and the "Get four versions" button are shown, and there is no "Paste new lyrics" button. While the request is pending, the same holds.
- AC-14: After a successful result, there is no text box named "Japanese lyrics" and no "Get four versions" button in the accessibility tree. A "Paste new lyrics" button is shown before the result heading in page order, and focus is on the result heading.
- AC-15: Pressing "Paste new lyrics" shows the text area with exactly the text that was submitted, moves focus to the text area, removes the "Paste new lyrics" button, and leaves the result list on the page.
- AC-16: From the reopened form, editing the text and submitting sends one new `POST /api/versions` with the edited text, clears the old result while waiting, and on the new result folds the form again with focus on the new heading.
- AC-17: When a submit returns an error (for example `model_unavailable`), the text area shows with the pasted text kept and has focus, the error message is in the alert region, and there is no "Paste new lyrics" button. This also holds for an error after reopening the form from a previous result.

### Narrow screens and safety

- AC-18: (stylesheet) The result groups have `overflow-wrap: anywhere`, no rule in `styles.css` contains `white-space: nowrap`, and the old fixed label column (`flex: 0 0 5.5rem`) is gone.
- AC-19: A line whose `original` and `english` hold `<b>x</b>` shows the literal text `<b>x</b>` in its group, and no `b` element is created.

## Open questions

1. **Hiragana above or below the Original?** Furigana usually sits above. Recommendation: below, as specified. The reply's hiragana is a whole-line reading with spaces, not aligned to each kanji, so placing it above does not give true furigana. Below also keeps spec 001's order (Original, Hiragana, Romaji, English) in both the HTML and the screen.
2. **Exact sizes.** Recommendation: Original `1.5rem`, every other row `1rem`, a `0.25rem` gap before the Romaji, a `1.5rem` gap before a new verse, and `0.75rem` between groups. The checks only test that the Original is largest and the verse gap is larger, so the sizes can be tuned without rewriting tests.
3. **Can the reopened form be folded again without submitting?** Recommendation: no. "Paste new lyrics" is one-way, which keeps it a plain button (no expanded/collapsed state to announce). The learner who changes their mind can just scroll down to the result, which is still there.
4. **How does this fit spec 002's link form?** Spec 002 puts a link form above the paste box. After a link result, its notice says the lyrics "are also in the paste box. You can fix them there". If the paste form is folded, that box is hidden. Recommendation: when spec 002's page work is built, the fold hides both forms, the button is renamed "New lyrics" (it then opens both), and spec 002's notice is reworded to "...press New lyrics to fix them." Record this as a small spec 002 amendment before its page task, not in this spec.
5. **Explain "Reading not verified".** The design critique asked for this. Recommendation: add, in this spec if the user agrees, one sentence shown under the legend only when at least one line is unverified: "Reading not verified: Lyrx could not confirm this reading matches the kana in the original line, so check it." It would be one extra AC. Left out of scope until the user decides.
6. **Wording of the heading.** The request mentioned saying how many lines were "translated". Recommendation: keep "Four versions (4 lines)", which is short and already tested. A line with no Japanese (for example an English line) is counted as a lyric line even though it is copied, not translated; saying "translated" would be slightly wrong for it.
