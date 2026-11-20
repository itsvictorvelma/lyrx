# 027 — Tidy the codebase

Status: approved

## Goal

Make the code easier to find your way around, with no change in behaviour: a clearer frontend folder layout, one place for each shared thing, and fewer small wrappers. Every page, API route, reply, and log line stays exactly as it is.

## Audit (2026-11-20)

- **Backend (2,900 lines):** already close to the rules. Two copies of the same streaming-POST error handling in `groq.py` and `gemini.py`, and two `*_or_none` wrappers in `library.py`. Nothing dead.
- **Frontend (4,800 lines of code, 3,000 of tests):**
  - `lyrics/` holds the whole app's shared code (`api.ts`, `types.ts`, `shortcuts.ts`, `SearchProgress`, `KanaRain`) next to the song page. So `account/` and `home/` import from `lyrics/`.
  - The player is mixed in with the song page.
  - `header/SearchForm` is used by home, and `library/SongArt` is used by home.
  - Duplicates:
    - two error-message functions with the same fallback texts (`App.tsx`, `AccountPage.tsx`);
    - three copies of the `localStorage` try/catch (theme, hidden columns, volume);
    - inline SVG icons spread over 9 files, with the close (×) icon drawn 3 times and the play icon twice;
    - `LoopIcon` and `VideoIcon` borrowed from `PlayerControls`;
    - the "same-site link" click handler written 3 times;
    - repeated checks in the `api.ts` type checks.
  - 11 exports that no other file uses.
  - CSS: no dead classes.

## In scope

1. **Frontend folders, grouped by feature (moves only, tests move with their file):**
   ```
   src/
     main.tsx  App.tsx  styles.css
     api.ts        every server call and reply check (merges lyrics/api.ts + account/accountApi.ts)
     types.ts      every shared data shape (from lyrics/types.ts + account/types.ts)
     routing.ts    addresses, navigate, goBack, and the same-site link handler
     browser.ts    media queries + stored settings (merges mediaQuery.ts, adds the one storage try/catch)
     icons.tsx     every inline SVG icon, once
     account/      AccountPage.tsx, account.ts (context, useAccount, isGuest)
     header/       Header.tsx, ThemeButton.tsx
     search/       SearchForm.tsx, SearchProgress.tsx, KanaRain.tsx
     shortcuts/    shortcuts.ts, ShortcutList.tsx, SiteShortcuts.tsx (moved out of App.tsx)
     home/         HomePage.tsx, HeroLine.tsx, heroTiming.ts
     library/      LibraryPage.tsx, SongTile.tsx, SongArt.tsx, songTiles.ts, RemovedMessage.tsx
     song/         (was lyrics/) SongPage, VersionsTable, ColumnButtons, OtherMatches,
                   SaveButton, hiddenColumns.ts, followLine.ts, fakeSongPage.tsx
     player/       PlayerBar, PlayerControls, YouTubePlayer, AudioFilePlayer,
                   playback.ts (absorbs lineLoop.ts and volume.ts)
   ```
2. **Merge small files** into the module that uses them, per AGENTS.md (under about 40 lines): `account/types.ts` and `account/useAccount.ts` become `account/account.ts`; `mediaQuery.ts` goes into `browser.ts`; `lineLoop.ts` and `volume.ts` go into `playback.ts`.
3. **One source each:**
   - `errorMessage(result)` in `api.ts`. The account page keeps its one extra case: `invalid_request` shows the rules text.
   - One stored-setting reader and writer for theme, hidden columns, and volume.
   - One `icons.tsx`.
   - One `followLink(path)` for same-site links.
   - `isSavedSong` reuses `isPlayback`.
4. **Remove dead exports:** drop `export` from names no other file uses: `BACK_TO_LINE_TEXT`, `GUEST_LIBRARY_TEXT`, `LOOPING_TEXT`, `LoopRange`, `NOT_AVAILABLE_TEXT`, `PartState`, `RainColors`, `RULES_TEXT`, `SEARCH_INPUT_ID`, `SHOW_TEXT`, `STEADY_AT`.
5. **Backend:**
   - `translation/reply_limits.py` becomes `translation/streamed_post.py`, holding the one streaming POST with its byte cap, deadline, and timeout and connect-error mapping. Groq and Gemini keep only their own status rules.
   - `library.find_song_or_none` and `saved_ids_or_none` fold into `find_song` and `saved_ids`, so a database that cannot be read counts as "not cached" or "none saved".
6. Update the `AGENTS.md` layout line for the new frontend folders.
7. **README rewrite** for a public GitHub page (deployment is next): a short pitch, the demo GIF, fresh screenshots of the current app (home, song light/dark, library, phone), features, how it works, tech stack, setup, run, checks, folder map, credits. Plain and scannable. The GIF stays unless a better one can be made.

## Out of scope

- Any change to behaviour, text, styles, API shape, the database, dependencies, or config.
- Rewriting tests beyond import paths and merged files. No test is deleted. A test that tested a removed wrapper is pointed at the function that replaced it.
- `styles.css` stays one file (1,828 lines). Splitting it is a separate decision.

## Rules

- Moves first, in their own commit (`git mv`, so history follows), then merges, then de-duplication. Each commit passes `scripts/check-quiet.sh`.
- Nothing is removed unless no caller remains (checked with grep and `tsc`).

## Security

- No change to input checks, outside calls, logging, or what touches disk. The streamed-POST merge keeps the same caps, deadline, no redirects, and no proxy. The reviewer checks this line by line.

## Acceptance checks

- AC-1: `scripts/check.sh` passes: ruff, mypy `--strict`, pytest, Prettier, ESLint, `tsc`, Vitest, and the build.
- AC-2: The test count is the same as or higher than before (backend and frontend), with no test deleted.
- AC-3: The top-level shared files (`api.ts`, `types.ts`, `routing.ts`, `browser.ts`, `icons.tsx`) never import from a feature folder. A feature imports only what another feature exports.
- AC-4: `grep` finds no inline `<svg` outside `icons.tsx`. The `KanaRain` canvas is not an SVG and is not affected.
- AC-5: `localStorage` appears only in `browser.ts` (and in tests).
- AC-6: The API reply bodies, status codes, and log lines are unchanged. The existing backend tests are untouched apart from the two folded wrappers.
- AC-7: The README folder map matches the tree, and every image it links exists.
- AC-8: The screenshots show the current design (taken from the running app, invented or LRCLIB-free demo content only where lyrics would show; no real lyrics committed beyond what the existing screenshots already show).

## Added after review (asked for by the user, 2026-11-20)

- The header keeps its search box during the whole wait after a search from home (it used to appear halfway, when the address changed).
- On a phone, the player bar sits in centered rows: transport, Mute, and speed; then sync; then video, Change audio, and shortcuts.
- README: no roadmap; Light theme and Your songs share the width equally.

## Left alone (flagged for you)

- `database.upgrade_saved_songs`: the one-time upgrade of a database from before accounts. It is dead once every copy is upgraded. Remove it when you're sure the server's file is new.
- `backend/tests/test_removed_code.py`: it guards against old modules coming back. Harmless, but stale.
- The phone breakpoint is written twice: `PlayerBar` (`max-width: 719px`) and `KanaRain` (720px). They are kept, since merging them touches CSS-linked behaviour.
- `server/host_check.py` and `origin_check.py` are both short, but each has one job. Spec 020 turns them into settings anyway.
- `HANDOFF.md` (untracked) is out of date: 014 and 026 are merged. You can delete it or update it.
- `specs/README.md` still lists 014 and 026 as approved. They are merged, so they get set to `done` in this PR.

## Plan

- Commit 1: `git mv` the frontend files into the new folders; fix imports. Checks pass.
- Commit 2: merge the small files (`account.ts`, `browser.ts`, `playback.ts`, `api.ts`, `types.ts`), move `SiteShortcuts` out of `App.tsx`, add `icons.tsx`, `followLink`, `errorMessage`, stored-setting helpers, drop dead exports. Checks pass.
- Commit 3: backend `streamed_post.py` and the folded library wrappers. Checks pass.
- Commit 4: README, screenshots, AGENTS.md layout line, specs README.
- Screenshots: headless Chrome against the user's running app (`127.0.0.1:5173`), only if it is running; Claude does not start it.
