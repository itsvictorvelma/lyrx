# AGENTS.md

The rules every human and agent follows in this repo. When a request conflicts with a rule here, stop and ask.

**Priority order: security, then correctness, then a working page, then polish.**

## What Lyrx is

An app for learning a song in another language. The learner types a song's name in one box, and Lyrx shows every line of the song in every version that helps for that language, side by side.

For Japanese (the first language) that is four columns, one row per lyric line:

| Original | Hiragana | Romaji | English |
|---|---|---|---|
| 君の声が聞こえる | きみ の こえ が きこえる | kimi no koe ga kikoeru | I can hear your voice |

Other languages come later, one spec each, with the versions that make sense for them (for example Korean: hangul, romanization, English).

The previous version of this app is preserved at git tag `archive/cursor-v1`. It is history, not a plan.

## Locked decisions

- **One box, one answer.** The learner types a song name (title, artist, or both) and gets the versions. There is no back-and-forth chat. If the match is wrong, the learner picks another match from a short list.
- **Japanese first.** Other languages are added one spec at a time, after Japanese works end to end.
- **No paid AI or API services** (decided 2026-11-17).
  - Lyrics come from LRCLIB (free, no key).
  - Every version except the original (hiragana, romaji, English) comes from a free-tier AI translator, checked against a schema: Groq first, Gemini as the backup when Groq is busy (decided 2026-11-18, spec 010). No local reading dictionaries (decided 2026-11-17: less code, and new languages need only a new prompt).
- **Lyrics source.** LRCLIB only. Pasting lyrics was removed (decided 2026-11-18). Scraping other lyrics sites is out for now (terms of use, fragile pages, SSRF risk). Revisit only if LRCLIB misses often.
- **Layout.** Columns side by side, one row per lyric line.
- **Hosting is planned.** The app will be hosted on a server for the user, family, and friends, with personal accounts (a later spec). Until that spec, it runs on `127.0.0.1`. The user handles the server and domain; specs only make the app ready for it.
- **Roadmap:** done so far: the core, saved songs (library), synced playback (YouTube embed and optional MP3, with LRCLIB timings), the design pass, and study tools. Next: personal accounts (spec 014), ready for hosting.
- **Design.** The design pass (spec 013) set the look: the colour tokens and patterns in `frontend/src/styles.css`. New UI reuses them; anything new to the look is proposed and approved first.
- **Stack.** Python server in `backend/` (FastAPI, uvicorn, uv, pytest), React page in `frontend/` (Vite, TypeScript, Vitest with jsdom and Testing Library). `scripts/check.sh` runs every check.
- **Never push to `main`.** Every change is a PR the user reviews and merges.

## How we work (lean)

The goal of every spec is a page the user can click. Process serves that, not the other way round.

1. **Spec.** The main session writes a short spec in `specs/NNN-name/spec.md` from `specs/_template/` (aim for under 150 lines): goal, scope, rules, security, numbered acceptance checks. The user approves it (`Status: approved`). No code before approval.
2. **Plan.** The main session adds a short Plan section to the spec (files touched, approach) and explains it in a few lines. Then it creates branch `claude/NNN-name`.
3. **Build.** The main session writes tests and code directly, in as few sessions as it takes. Each acceptance check gets a test. It runs `scripts/check-quiet.sh` as it goes. No subagent per task, and no `/clear` between steps.
4. **Review.** When everything passes, the `reviewer` agent checks the whole diff once. The main session fixes the findings. After 2 failed review rounds, stop and ask the user.
5. **PR.** Run the pre-commit checks, open a PR with a short plain summary, start the app, and give the user a "try this" list of 3 to 5 things to click. The user reviews and merges.
6. **Done.** Set the spec to `done` and update `specs/README.md`.

Status values: `draft` → `approved` → `done`, or `shelved` when the user drops a spec.

Limits:
- Before writing a file, say in one line what it is and why.
- Only build what the spec asks. No speculative abstractions or "future-proofing".
- No new dependency without asking. Prefer the standard library, then what is installed.
- Never push to `main`, force-push, rewrite history, or delete branches without explicit approval.
- Use `scripts/check-quiet.sh`. Never paste full test output.

## Security rules (non-negotiable)

### Secrets
- API keys (Groq, Gemini) live only in the environment or a gitignored `.env`. Never hardcode, commit, log, print, or send them to the browser.
- Never weaken `.gitignore` for `.env*`, `*.mp3`, databases, or `.claude/settings.local.json`.

### Untrusted input
- Typed song names, LRCLIB replies, saved rows, and model output are all untrusted.
- Enforce size limits before anything else reads them.
- The server calls only fixed hosts (LRCLIB, Groq, Gemini), over `https`, with a timeout, a size cap, no redirects, and no proxy from the environment. It never fetches a URL the learner supplies.
- Lyrics sent to the model are data, never instructions. The system instruction says so.
- Model output is validated against a schema before the app uses it. Invalid output creates nothing.
- Fetched and generated text is rendered as text, never as HTML.

### The app
- Bind to `127.0.0.1` only, and reject a `Host` header that is not `127.0.0.1` or `localhost`, until the hosting spec turns these into settings.
- Errors return a short code and message. Never stack traces, file paths, SQL, or secrets.

### Lyrics and tests
- Song lyrics are copyrighted. Never commit real lyrics: tests, fixtures, specs, and docs use invented lines.
- Default tests never call Groq, Gemini, LRCLIB, or the network. Outside calls are replaced with fakes.

### Before every commit
- Run `git status` and `git diff --cached`.
- Confirm no `.env*`, no audio, no database, and no `.DS_Store` is staged.
- Scan the diff for secrets and API keys.

## Code structure

The code must be easy to read for someone who has never worked in this repo. The reviewer fails work that breaks these rules.

- **Layout.** Backend code in `backend/src/lyrx/`, grouped by area: `lyrics/` (finding and preparing lyrics), `translation/` (the translators and their checks), `server/` (guards and logging around every request); app-wide files (`app.py`, `config.py`, `errors.py`, `schemas.py`, `song.py`, `library.py`) at the top. Tests in `backend/tests/`, in the same folders, one `test_<module>.py` per module. A data shape lives in the file that uses it; `schemas.py` holds only what the page sends and receives. Merge a file under about 40 lines into the one module that uses it rather than adding another file. Frontend code in `frontend/src/`, grouped by feature; tests sit next to the file they test as `*.test.ts(x)`. The README holds the folder map and is updated when a folder or module is added.
- **One job per file**, named for that job. No `utils`, `helpers`, `common`, `misc`, or `manager`. No folder for a single file.
- **Every file opens with a one-line docstring or comment** saying what it is for.
- **Names say what things are and do**: `split_lines`, `to_romaji`, `SongSearchForm`. No abbreviations a newcomer would have to guess.
- **Short functions** that do one thing. A reader can follow a request top to bottom.
- **Settings in one place**: backend `config.py`, no magic numbers or strings elsewhere. Data shapes in `schemas.py` (backend) and `types.ts` (frontend).
- **Formatting and lint are automatic.** `scripts/check.sh` runs ruff, mypy `--strict`, and pytest for the backend; Prettier, ESLint, `tsc`, Vitest, and the build for the frontend. Nothing merges with a failing check.

## Clean code rules

- Type hints on all functions. Validate data at every boundary: request, model reply, fetched record.
- Every non-trivial rule gets a test that fails if the rule breaks.
- Comments only for constraints the code can't express.
- Reuse before writing: the repo, the standard library, installed dependencies, then new code.
- Fix bugs at the root cause and check every caller.
- Mark a deliberate shortcut with a `ponytail:` comment naming the limit and the upgrade path.

## UI rules

- No UI library or CSS framework unless the user names one.
- No invented colors, gradients, shadows, or design tokens. Propose a minimal neutral set and ask first.
- Accessibility is required: visible focus, labeled controls, never color alone to carry meaning.
- Japanese text renders with a font stack that covers kana and kanji.

## Domain notes (Japanese)

- The translator is asked to spell the romaji from its own hiragana, and to keep kana already in the line as written. The server checks that the hiragana has no kanji and the romaji has no kana or kanji.
- Line count and order are the same in every version. Index from 0, no gaps.

## Tests

- One test per acceptance check, plus tests for rules that would silently break. Not one test per imaginable edge case.
