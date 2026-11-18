# 003 — Tasks

Each task is one test-writer → implementer → check.sh → reviewer round. Tests use invented lyrics, a fake LRCLIB, a fake Gemini, and (for dictionary edge cases) a fake analyzer. The network guard stays on. `scripts/check.sh` passes at the end of every task.

Line timings (spec AC-20 to AC-22) moved to spec 005 and are not built here.

## Part 1: the free pipeline for pastes (PR 1)

- [x] T1 (AC-23 to AC-34, AC-36, AC-37, AC-65 request-body part): The cleanup. `lyric_cleanup.py`; `read_paste` returns cleaned lines; the size limits and `input_too_large` go; the body cap becomes 256 KiB with `not_lyrics`. Re-point the uncommitted spec 002 cleanup tests to these ACs. The paste route still uses Claude at this point.
  - [x] T1 follow-ups (from the T1 review): nested empty bracket pairs collapse in the same pass (`君(（）)が` → `君が`, spec clarification in "The shared removal"), with an idempotence test; add an `empty_input` case to the log-line tests (one log line, lines=0, characters=0). Done with T2's round.
- [x] T2 (AC-38 to AC-45, AC-47 to AC-49 at module level): Readings. Add `fugashi` and `unidic-lite`. `japanese_analyzer.py`, `hiragana.py`, and the romaji particle rule in `romaji.py`. `tests/fake_analyzer.py`.
  - [x] T2 follow-up (from the T2 review, do with T3's round): test-writer adds two fake-analyzer cases in tests/test_hiragana.py: `ヶ月` (suffix) read `カゲツ` → readingVerified true; `関ヶ` read `セキノ` → false.
- [x] T3 (AC-50, AC-51, AC-55 to AC-59 at module level): The Gemini request and reply checks in `gemini.py`, against `tests/fake_gemini.py` on the fake transport. The key goes in a header, never in a URL.
  - [x] T3 follow-ups (from the T3 review, do with T4's round): the AC-58 test asserts `error.__cause__ is None and error.__suppress_context__`, so removing `from None` fails a test; a `ponytail:` comment in `gemini.py` that a lyric line containing `</lyrics>` is not escaped; a `ponytail:` comment that the Gemini reply is read with no byte cap (bounded by `maxOutputTokens`, fixed host); `parse_envelope` and `parse_reply` catch the same parse errors; one-line docstrings on `build_user_message`, `build_body`, `parse_envelope`. For T5: the real Gemini transport must not pick up a proxy from the environment, with a test, and the route never logs an exception's `__context__`.
- [x] T4 (AC-53, AC-54 at module level): `translation.py`: chunks, order, stop at the first failure. The numbered message stays in `gemini.py` (`build_user_message`).
  - [ ] T4 follow-ups (from the T4 review, do with T5's round): a test in `test_gemini.py` that a deeply nested envelope and reply text give `translation_invalid`; if it passes without the `RecursionError` branch, drop it from `parse_envelope` and `parse_reply`. In `translation.py`, `return chunks` instead of `list(chunks)`, and loop as `for index, text in lines:` instead of `line[1]`.
- [ ] T5 (AC-46, AC-52 to AC-60, AC-61 server part): Switch the paste route to the new pipeline (`four_versions.py`), with `englishError`. Delete the Claude pipeline, its tests, and the `anthropic` dependency, and the unused `details` parameter of `ApiError`. `GEMINI_API_KEY` in config and `.env.example`. The paste route's log fields.
- [ ] T6 (AC-61 page part, AC-71 removed codes, AC-72 paste, AC-73, AC-76): The paste side of the page: `englishError` in the reply checks, the "No English yet" note, "Some readings may be wrong.", no English row when empty, the removed codes and the limit sentence builder.
- [ ] README: the Gemini key setup, the free-tier note, the folder map.
- [ ] Manual check (with the user's key and go-ahead, nothing committed): one real paste. Confirm the Gemini request shape and reply parsing against the live API.
- [ ] Final review of the Part 1 diff, the explainer's walkthrough, the PR.

## Part 2: search and pick (PR 2)

- [ ] T7 (AC-10, AC-11, AC-65 record part, AC-1 headers): `lrclib.py`: fixed host, `https`, no redirects, no proxies, timeout, streaming caps, JSON and record-schema checks. Trim spec 002's unused DNS and SNI parts of `tests/fake_network.py` and delete `tests/pages.py`.
- [ ] T8 (AC-1 to AC-9, AC-12): The search route: `song_search.py` and `looks_japanese.py`.
- [ ] T9 (AC-13 to AC-19, AC-35): The pick route: `song_versions.py`.
- [ ] T10 (AC-62 to AC-64): Error bodies, the log fields of the new routes, the Host check and methods on the new routes.
- [ ] T11 (AC-66 to AC-71, AC-72 song part, AC-74, AC-75): The search page: form, results, getting a song, the song line, error messages, reply checks.
- [ ] README: the search flow and folder map.
- [ ] Manual check (with the user's go-ahead): one real search and pick.
- [ ] Final review of the Part 2 diff, the explainer's walkthrough, the PR. Then spec 003 is `done`.
