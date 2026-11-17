# 003 — Plan

How spec 003 is built. The spec says what; this file says which files change and how.

## Approach in one paragraph

Two new routes sit next to the paste route: `POST /api/song-search` asks LRCLIB for a name and returns a ranked short list, and `POST /api/song-versions` fetches one record and runs it through the same pipeline as a paste. That shared pipeline is: clean the lines → hiragana from the local analyzer → romaji from the hiragana → English from Gemini (in chunks only when the song is very large) → the reply, with `englishError` when Gemini fails. The Claude call and its checks are deleted. Every outside call (LRCLIB, Gemini) goes through `httpx2` with a transport the tests replace, so no test touches the network.

## Settled open questions

Checked on 2026-11-17 against the live documentation and a scratch install (nothing committed).

1. **Gemini model and client.** Model `gemini-3.6-flash`: stable, on the free tier, recommended by Google for everyday text tasks. Plain HTTPS with `httpx2` to `POST https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent`, key in the `x-goog-api-key` header. **No `google-genai` SDK, so no new dependency.**
   - Request: `systemInstruction`, one user `contents` item, `generationConfig` with `responseMimeType: "application/json"`, `responseJsonSchema` (the reply schema, `additionalProperties: false`), `maxOutputTokens`, and `thinkingConfig.thinkingLevel: "LOW"`. `store: false`.
   - Reply: text in `candidates[0].content.parts[].text`. `promptFeedback.blockReason` set → `translation_blocked`. `finishReason` `SAFETY`, `RECITATION`, `PROHIBITED_CONTENT`, `BLOCKLIST`, `SPII` → `translation_blocked`; `MAX_TOKENS` → `translation_invalid`; anything else but `STOP` → `translation_invalid`. Token counts from `usageMetadata`.
   - Google now calls `generateContent` "legacy, still supported" and recommends its newer Interactions API, whose documentation does not yet say how blocks are reported. `ponytail:` comment in `gemini.py`: move to the Interactions API once its block reporting is documented.
   - Google no longer publishes free-tier request limits; they show in Google AI Studio. The spec already handles a `429` (`translation_rate_limited`, no retry).
2. **LRCLIB.** Confirmed from `https://lrclib.net/docs.md`: `GET /api/search` with `track_name` and `artist_name` (searching `track_name=akuma no ko` returns the original song); `GET /api/get/{id}`; unknown id → `404` (`TrackNotFound`); a search returns at most 20 items (reading the first 50 stays a harmless upper bound); the record fields match the spec's schema. LRCLIB asks clients to name themselves in `User-Agent`; `Lyrx/0.1` does that without a link or e-mail, as the spec requires. A `429` from LRCLIB is a non-2xx reply → `lyrics_source_unavailable`, per the spec.
3. **"Looks Japanese" threshold:** a quarter, as specified. Kept as a setting.
4. **Duplicate window:** 2 seconds, as specified. Kept as a setting.
5. **Word breaks.** Conjunctive particles (UniDic `pos2` `接続助詞`, such as `て` and `で` after a verb) join the word before: `聞いて` → `きいて`, `とんでゆく` → `とんで ゆく`. This narrows the spec's "a particle always stands alone" rule, which the spec left to the plan. It does not touch `は` or `へ`, so the romaji particle rule is unchanged. Every other particle stands alone.
6. **Settings** (all in `config.py`): LRCLIB timeout 10 s; caps 2 MiB (search) and 512 KiB (record); names 300 characters; 50 items read, 10 shown; Gemini timeout 120 s; `maxOutputTokens` 32,768; chunk size 200 non-blank lines or 8,000 characters. 200 lines of English in the reply JSON is about 6,000 tokens, well inside one reply.
7. **UniDic fields.** `fugashi` 1.5.2 with `unidic-lite` 1.0.8 gives `UnidicFeatures26`, which has `kana` (the reading as written: `遠く` → `トオク`) and `pron` (the pronunciation: `トーク`). Only `kana` is read. Latin and digit tokens have no `kana` (`None`).

### Two analyzer details the code must handle

Found in the scratch install. Both keep the spec's expected results; neither changes the spec.

- **Analyze each space-separated run on its own.** Run on the whole line `Oh 君と`, the analyzer tags `君` as the suffix "kun" after `Oh`. Run on `君と` alone, it is the pronoun `きみ`. A run with no Japanese character is one piece, kept as written.
- **Full-width digits.** `２人` is one dictionary word read `フタリ`, which would drop the digit the spec keeps (AC-42). The analyzer gets a copy of the run with `０`–`９` mapped to `0`–`9` (same length, one to one); each word's written form is then taken from the original run by position.
- The `fugashi` tagger is created once and shared behind a lock, because the paste and song routes run in FastAPI's threadpool and a MeCab tagger is not safe to share across threads.

## Files

### Backend: new modules (`backend/src/lyrx/`)

| File | Job |
|---|---|
| `lyric_cleanup.py` | The shared removal and the cleanup steps 3–5 (`remove_unwanted_characters`, `clean_lines`). Used by pastes, LRCLIB records, and the timed lines. |
| `japanese_analyzer.py` | Wraps `fugashi`: one locked tagger; turns a run of text into `Word(surface, part_of_speech, conjunctive, reading)`; the full-width digit mapping. The only module that imports `fugashi`. |
| `hiragana.py` | One line → its hiragana and `readingVerified`: one piece per word, the kana check, the joining rules, and which words are particles `は`/`へ`. |
| `gemini.py` | The one Gemini HTTPS request and the checks on its reply. Returns the English by index or raises a `TranslationFailed(code)`. |
| `translation.py` | Builds the numbered message, cuts chunks, calls `gemini.py` per chunk in order, joins the English, stops at the first failure. |
| `lrclib.py` | The two LRCLIB requests: fixed host, `https`, no redirects, no proxies, timeout, the streaming size caps, JSON and record-schema checks, and the error codes. |
| `song_search.py` | Search rules: drop, `looksJapanese`, rank, remove duplicates, keep 10. |
| `timings.py` | Reads synced lyrics (the anchored LRC pattern), cleans the timed lines, and matches them to the plain lines. |
| `song_versions.py` | The pick route's pipeline: fetch the record → check → clean → looks Japanese → four versions → timings. |
| `looks_japanese.py` | The quarter-of-lines kana rule, shared by search and pick. |

### Backend: changed

| File | Change |
|---|---|
| `four_versions.py` | Becomes the shared pipeline for cleaned lines: hiragana and romaji per line, then `translation.py`, then the reply lines with `englishError`. No Claude. |
| `lines.py` | Keeps splitting and `has_japanese`; `read_paste` returns the cleaned lines. `check_limits`, `count_characters`'s limit use, and `find_first_long_line` go. |
| `romaji.py` | `to_romaji` gains the particle information from `hiragana.py`: a word marked as particle `は`/`へ` is `wa`/`e`; every other `は`/`へ` is `ha`/`he`. Retires the tooth `ponytail:`; adds the `こんにちは` one. |
| `app.py` | The two new routes; `create_app` takes an LRCLIB transport and a Gemini transport (tests pass fakes). |
| `config.py` | Gemini and LRCLIB settings above; `GEMINI_API_KEY`; the 256 KiB body cap; the cleanup split length. Removes the Claude settings and the size limits. |
| `errors.py` | Adds `empty_search`, `song_not_found`, `lyrics_source_unavailable`, `lyrics_source_timeout`, `song_not_japanese`, `not_lyrics`; changes `server_not_configured`; removes `input_too_large`, the `model_…` codes, and the limit-details helpers. |
| `schemas.py` | Request and reply shapes for both routes, `startSeconds`, `englishError`, the LRCLIB record schema, the Gemini reply schema. Removes the Claude shapes. |
| `body_limit.py` | Cap from config (256 KiB), code `not_lyrics`. |
| `request_log.py` | Generic fields per route (results, id, lines, characters, timings matched, Gemini requests, `englishError`, tokens). Never a search text or URL. |

### Backend: deleted

`claude.py`, `prompt.py`, `readings.py` (the Claude reading checks), `tests/fake_claude.py`, `tests/test_claude.py`, `tests/test_prompt.py`, `tests/test_readings.py`, `tests/test_fake_claude.py`. From spec 002's leftovers, `tests/pages.py` and the DNS and SNI parts of `tests/fake_network.py` (`answer`, `resolve`, `dialed`, `sni_hostname`), which no spec 003 test uses.

### Backend: tests

One `test_<module>.py` per new module. `test_four_versions.py`, `test_lines.py`, `test_romaji.py`, `test_app.py`, `test_body_limit.py`, `test_request_log.py`, `test_config.py` are updated. The uncommitted spec 002 T1b tests (`test_lyric_cleanup.py`, and the edits to `test_lines.py` and `test_four_versions.py`) are kept and re-pointed at AC-23 to AC-37. Their tests of the removed size limits are rewritten per AC-32 and AC-33. New test helpers: `tests/fake_gemini.py` (builds scripted Gemini HTTP replies on the fake transport and records each request body) and `tests/fake_analyzer.py` (set words with set tags and readings). `tests/fake_network.py` serves LRCLIB and Gemini replies. The network guard stays on.

### Backend: dependencies

`pyproject.toml`: add `fugashi` and `unidic-lite` (approved in the spec); remove `anthropic`. `uv.lock` updates with them.

### Frontend (`frontend/src/`)

| File | Change |
|---|---|
| `lyrics/SearchForm.tsx` (new) | Song name, artist, Search button. |
| `lyrics/SearchResults.tsx` (new) | The ranked list with the "Use this song: …" buttons. |
| `lyrics/EnglishNote.tsx` (new) | "No English yet. Try again later." plus the sentence for the code. |
| `lyrics/api.ts` | `searchSongs`, `getSongVersions`, and the reply checks for both; paste reply gains `englishError` and `startSeconds`. |
| `lyrics/types.ts` | The new shapes. |
| `lyrics/errorMessages.ts` | New codes and messages; removes `input_too_large`, the `model_…` codes, and the limit sentence builder. |
| `lyrics/FourVersions.tsx` | "Some readings may be wrong."; leaves out an empty English row. |
| `lyrics/PasteForm.tsx` | Heading "Or paste the lyrics"; disabled while any request runs. |
| `App.tsx` | Page state for searching, results, getting a song, the song line, and the note. |

Each gets its `*.test.ts(x)` next to it.

### Docs and settings

- `.env.example`: `GEMINI_API_KEY=` replaces `ANTHROPIC_API_KEY=`.
- `README.md`: the new flow, the Gemini key setup (Google AI Studio), the free-tier note, and the folder map.
- `specs/README.md`: 003 to `done` after the merge.

## Side effects and risks

- **Size.** This is far above the 800-line mark: about 1,200 lines of new source across backend and frontend, about 2,500 lines of tests, and about 900 lines deleted. It is one spec because the routes share one pipeline; it is built as 11 small tasks, each reviewed on its own.
- **Dictionary size.** `unidic-lite` adds about 50 MB to `backend/.venv`. Nothing is added to the repo.
- **Free-tier limits** are not published and can change. A rate-limited song still gets its readings.
- **Analyzer readings are not perfect** (names, sung readings, counters). The spec accepts this; `readingVerified` flags the cases the code can detect.
- **The first real run** needs the user's Gemini key. A manual task checks one real search, one real pick, and one real paste once, by hand, with the user's go-ahead; nothing from it is committed.
