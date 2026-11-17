# 003 — Tasks

Each task is one test-writer → implementer → check.sh → reviewer round. Tests use invented lyrics, a fake LRCLIB, a fake Gemini, and (for dictionary edge cases) a fake analyzer. The network guard stays on. `scripts/check.sh` passes at the end of every task.

- [ ] T1 (AC-23 to AC-37, AC-65 request-body part): The cleanup. `lyric_cleanup.py`; `read_paste` returns cleaned lines; the size limits and `input_too_large` go; the body cap becomes 256 KiB with `not_lyrics`. Re-point the uncommitted spec 002 cleanup tests to these ACs. The paste route still uses Claude at this point.
- [ ] T2 (AC-38 to AC-45, AC-47 to AC-49 at module level): Readings. Add `fugashi` and `unidic-lite`. `japanese_analyzer.py`, `hiragana.py`, and the romaji particle rule in `romaji.py`. `tests/fake_analyzer.py`.
- [ ] T3 (AC-50, AC-51, AC-55 to AC-59 at module level): The Gemini request and reply checks in `gemini.py`, against `tests/fake_gemini.py` on the fake transport. The key goes in a header, never in a URL.
- [ ] T4 (AC-53, AC-54 at module level): `translation.py`: the numbered message, chunks, order, stop at the first failure.
- [ ] T5 (AC-46, AC-52, AC-55 to AC-60, AC-61, AC-22 paste part): Switch the paste route to the new pipeline (`four_versions.py`), with `englishError` and `startSeconds: null`. Delete the Claude pipeline, its tests, and the `anthropic` dependency. `GEMINI_API_KEY` in config and `.env.example`.
- [ ] T6 (AC-10, AC-11, AC-65 record part, AC-1 headers): `lrclib.py`: fixed host, `https`, no redirects, no proxies, timeout, streaming caps, JSON and record-schema checks. Trim spec 002's unused DNS and SNI parts of `tests/fake_network.py` and delete `tests/pages.py`.
- [ ] T7 (AC-1 to AC-9, AC-12): The search route: `song_search.py` and `looks_japanese.py`.
- [ ] T8 (AC-20, AC-21): `timings.py`.
- [ ] T9 (AC-13 to AC-19, AC-22, AC-35): The pick route: `song_versions.py`.
- [ ] T10 (AC-37, AC-62 to AC-64): Error bodies, the log fields per route, the Host check and methods on the new routes.
- [ ] T11 (AC-66 to AC-76): The page: search form, results, getting a song, the song line, the English note, "Some readings may be wrong.", error messages, reply checks, the paste form.
- [ ] README: new flow, Gemini key setup, free-tier note, folder map.
- [ ] Manual check (with the user's key and go-ahead, nothing committed): one real search, one real pick, one real paste. Confirm the Gemini request shape and the reply parsing against the live API.
- [ ] Final review of the whole diff, then the explainer's walkthrough, then the PR.
