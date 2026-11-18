# 008 — Find a song: type a name, read it in four columns

Status: approved (by the user in chat, 2026-11-17, with "Option 1": Gemini makes every version)

## Goal

The learner types a song name in one box and, a few seconds later, reads every line in four columns: Original, Hiragana, Romaji, English. This is the first version of Lyrx that is useful end to end. It replaces spec 003, reuses its cleanup, Gemini call, and chunks, and cuts the code down: Gemini makes all three versions in one call, so the local reading code goes.

## In scope

- **One search box.** The learner types a title, an artist, or both, in any order.
- **Best match automatically.** The server asks LRCLIB and ranks the matches; the page opens the best one right away. A "Not this song?" list shows the other matches; clicking one opens it instead.
- **The four versions from Gemini.** The song is cut into small chunks (15 lines) sent at the same time, up to 4 at once; each request carries the whole song as context and asks for its own lines. Amended 2026-11-18 (user): the old single call was slow and failed often.
- **Columns layout.** One table row per lyric line, four columns. A blank line in the song shows as a gap between verses, not an empty row.
- **Paste fallback.** When no match is found, a "Paste the lyrics instead" link opens the existing paste form, which goes through the same pipeline.
- **Deleting code.** Removed with their tests: the Claude pipeline (`claude.py`, `prompt.py`, `anthropic`, `ANTHROPIC_API_KEY`, the `model_…` codes) and the local readings (`fugashi`, `unidic-lite`, `japanese_analyzer.py`, `hiragana.py`, `readings.py`, `romaji.py`, and whatever of `kana.py` nothing else uses). `GEMINI_API_KEY` goes in `config.py` and `.env.example`.
- **Lighter tests.** One test per acceptance check below, plus tests already kept for the reused modules. Tests for deleted code are deleted.

## Out of scope

- Languages other than Japanese. A song that does not look Japanese gives "Lyrx only supports Japanese songs for now."
- Showing the original lyrics when Gemini fails. A Gemini failure is an error with a clear message; the learner tries again.
- Saving songs (next spec), playback and timings, accounts, hosting.
- Lyrics from anywhere but LRCLIB and pastes. AI to understand the search text.
- Showing lines while the rest are still coming (streaming).

## Inputs and outputs

**Search.** `POST /api/song-search` with `{ "query": "星の歌 ミナト" }` → `200 { "results": [ { "id", "track", "artist", "album", "durationSeconds", "looksJapanese" } ] }`, best first, at most 10. No lyrics at this step.

**Open a song.** `POST /api/song-versions` with `{ "id": 101 }` → `200 { "song": { "id", "track", "artist", "album", "durationSeconds" }, "lines": [ { "index", "original", "hiragana", "romaji", "english" } ] }`.

**Paste.** `POST /api/versions` with `{ "lyrics": "…" }` → `200 { "lines": [...] }`.

Errors use the existing `{ "code", "message" }` shape.

## Rules

### Search
1. `query` is a string, trimmed, 1 to 300 characters; otherwise `400 empty_search` (empty) or `400 invalid_request`.
2. One `GET https://lrclib.net/api/search?q=<query>`. The reply must be a JSON array; only its first 50 items are read. Anything else is `502 lyrics_source_unavailable`.
3. Drop items that fail the record schema, are instrumental, or have no plain lyrics.
4. Rank items that look Japanese first, then LRCLIB's order. Remove duplicates (same normalized track and artist, durations within 2 s). Keep 10.
5. None left → `404 song_not_found`.

**Looks Japanese:** at least a quarter of the non-blank cleaned lines contain a kana.

### Open a song
1. `id` is an integer ≥ 1 (not a boolean, float, or string); otherwise `400 invalid_request`.
2. `GEMINI_API_KEY` unset or empty → `503 server_not_configured`, before LRCLIB is called. Read at request time.
3. One `GET https://lrclib.net/api/get/{id}`. `404` → `404 song_not_found`; any other failure, a schema failure, or an id mismatch → `502 lyrics_source_unavailable`.
4. Clean the plain lyrics (existing `lyric_cleanup.py`). Not Japanese → `422 song_not_japanese`; Gemini is not called.
5. The four versions (shared with paste, below).

### The four versions (shared pipeline)
1. Gemini gets the numbered non-blank lines as data, never instructions, and replies with JSON: one `{ "index", "hiragana", "romaji", "english" }` per sent line. The system instruction asks for: hiragana for the whole line with spaces between words, kana already in the line kept as written; romaji in modified Hepburn spelled from that hiragana, particles は/へ/を as wa/e/o; natural English using the lines around it as context.
2. The reply must be a JSON object with a `lines` array; otherwise the request is unusable. Each line is checked on its own: for a Japanese line a non-blank `hiragana`, `romaji`, and `english`, `hiragana` with no kanji, and `romaji` with no kana or kanji. Lines that fail, or are missing, are asked again once in their own request. A line that still fails is shown with empty versions, and the page says "Not available".
3. A line with no Japanese keeps its original text in all four columns; a blank line stays blank. Line count and order match the input.
4. **Retries** (amended 2026-11-18): an overloaded or failed request (`5xx`, connection error, timeout after 45 s, or an unusable reply) is retried up to 2 times, after 1 s and 3 s. A `429` and a block are never retried.
5. Gemini failures after the retries fail the song: `429` → `429 translation_rate_limited`; blocked → `502 translation_blocked`; outage → `503 translation_unavailable`; unusable reply → `502 translation_invalid`. Thinking is set to minimal.

### Talking to LRCLIB
Fixed host, `https` only, no redirects, no proxy from the environment, 10 s timeout, size caps enforced while streaming (2 MiB search, 512 KiB record), a fixed User-Agent with only the app name and version. The Gemini client also ignores proxies from the environment.

### The page
- One labeled input "Song name or artist" and a "Find" button, disabled while empty or while a request runs. A status line says "Finding the song…", then "Getting the lyrics and translating…", each followed by the seconds elapsed (hidden from screen readers).
- On success: a line "TRACK — ARTIST (lyrics from LRCLIB)", then the table with column headers Original, Hiragana, Romaji, English.
- "Not this song?" lists the other results as buttons ("TRACK — ARTIST, m:ss"), with "Not Japanese" as text where it applies.
- `song_not_found` → "No song found for that name." and the "Paste the lyrics instead" link. Other errors show their message.
- On a narrow screen the table scrolls sideways inside its own box; the page itself never scrolls sideways.
- Every server field is rendered as React text. No `dangerouslySetInnerHTML`. Labeled controls, visible focus, no new colors, the existing Japanese font stack.

## Security

- **Untrusted input:** the query, the id, pasted lyrics, LRCLIB replies, and Gemini replies. Body cap 256 KiB before parsing. The query only becomes a URL-encoded query value; the id is a checked integer before it enters the path.
- **Prompt injection:** lyrics are delimited data; a hostile song can at worst spoil its own versions, which must still pass the reply checks and are rendered as text.
- **Outside calls:** LRCLIB (search text or id only, no cookies or personal data) and Gemini (the numbered non-blank lines only, the key in a header). Nothing else is fetched.
- **Logged:** route, status, error code, a short fixed reason (such as `http_503`, `timeout`, `finish_RECITATION`), result count, LRCLIB id, line and character counts, Gemini calls, retries, time, missing lines, and token counts. Never the search text, lyrics, reply text, URLs with queries, headers, or the key.
- **Disk:** nothing is written. The server reads `.env`, which stays gitignored.
- The Host check, crash guard, and `127.0.0.1` bind cover the new routes.

## Acceptance checks

Backend (pytest, fake LRCLIB and fake Gemini; no network):

- AC-1: A search sends exactly one request to `https://lrclib.net/api/search` with `q` set to the trimmed query and the fixed User-Agent.
- AC-2: Empty query → `400 empty_search`; 301 characters or a non-string → `400 invalid_request`; LRCLIB not called.
- AC-3: Results drop bad, instrumental, and lyric-less items, put Japanese-looking items first, remove duplicates, and return at most 10, without lyrics.
- AC-4: No usable item → `404 song_not_found`. A non-array reply, a timeout, or a reply over the cap → `502 lyrics_source_unavailable`.
- AC-5: Opening a Japanese song returns its lines in order, indexed from 0, with the fake Gemini's hiragana, romaji, and English (exactly one call); non-Japanese and blank lines are kept as described.
- AC-6: Bad ids (0, `true`, `1.5`, `"1"`) → `400 invalid_request`; LRCLIB not called.
- AC-7: No key → `503 server_not_configured`, LRCLIB and Gemini not called; setting the key after start makes the next request work.
- AC-8: LRCLIB `404` → `404 song_not_found`; a `500` or an id mismatch → `502 lyrics_source_unavailable`.
- AC-9: A record that does not look Japanese → `422 song_not_japanese`, Gemini not called.
- AC-10: Gemini `429` and a block give their code after one call; a `503` is retried twice, then gives its code; the log names the reason. Bad lines are asked again once, then shown as "Not available".
- AC-11: The paste route returns the same line shape through the same pipeline.
- AC-12: `anthropic`, `fugashi`, `unidic-lite`, and the deleted modules are gone and nothing imports them.
- AC-13: Log lines hold the listed fields and never the query text or any lyric.

Page (Vitest):

- AC-14: Typing a name and pressing Find calls search, opens the first result, and shows the song line and a four-column table with one row per lyric line.
- AC-15: Clicking a "Not this song?" item opens that song instead.
- AC-16: `song_not_found` shows the message and the paste link; the paste form produces the same table.
- AC-17: An error reply shows its message; a malformed `200` reply shows "Something went wrong. Try again."; server text containing `<b>` renders as literal text.

## Plan

- **Branch** `claude/008-find-a-song`, cut from `claude/003-song-search` (it holds the reused code).
- **Delete first:** the Claude pipeline and the local readings with their tests and dependencies (`uv remove anthropic fugashi unidic-lite`).
- **Backend:** `gemini.py` asks for and checks hiragana, romaji, and English; `four_versions.py` becomes the shared pipeline; new `lrclib.py` (the two LRCLIB requests), `song_search.py`, `song_versions.py`, `looks_japanese.py`; routes in `app.py`; codes in `errors.py`; settings in `config.py`; shapes in `schemas.py`; `tests/fake_lrclib.py`.
- **Frontend:** search form, results list, versions table, paste fallback; types in `types.ts`; reply checks.
- **README:** Gemini key setup and the folder map.
- **Paste link:** shown at all times, not only after `song_not_found`, so a learner can paste any song (decided in the build; the AC-16 flow still holds).
