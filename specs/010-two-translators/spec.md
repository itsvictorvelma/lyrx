# 010 — Two translators: Groq first, Gemini as backup

Status: approved (by the user, 2026-11-18)

## Goal

Songs open fast and almost never fail. Today about every other new song fails with Google's "high demand" 503, and a 40-line chunk takes about 12 s. Groq is a second free service, run by a different company, so it is rarely busy at the same moment as Google.

## Why Groq first (test on 2026-11-18, 8 invented lines with tricky readings)

| Model | Time | Passed the checks | Mistakes seen |
|---|---|---|---|
| Groq `openai/gpt-oss-120b` | 3.6 s | 8/8 | none |
| Groq `openai/gpt-oss-20b` | 1.9 s | 8/8 | one split word |
| Groq `qwen/qwen3.8-27b` | 1.8 s | 8/8 | one wrong reading, English turned into kana |
| Gemini `gemini-3.5-flash-lite` | 7.7 s | 8/8 | long vowels dropped (kyo, mo), split words |

Free limits per Groq model: 1,000 requests a day, 8,000 tokens a minute (about 2 songs a minute). Gemini stays as the backup for when Groq is out of quota or down.

## In scope

- **A translator chain** in `config.py`, tried in order for each request: Groq `openai/gpt-oss-120b`, then Gemini `gemini-3.5-flash-lite`, then Gemini `gemini-3.1-flash-lite`. Changing the order is one line.
- **Move to the next translator** when one is busy or unreachable: `429`, `503`, a timeout, or a connection error. Groq's `413` (one request larger than its per-minute token limit) counts as `429`. Any other failure (a refused request, a blocked or unusable reply) is handled as today: retried or reported, no move.
- **Same prompt, same JSON shape, same checks** for every translator. Lines that fail the checks are asked again once, then shown as "Not available", as today.
- **Keys:** `GROQ_API_KEY` joins `GEMINI_API_KEY` in `.env`. Either key alone is enough; a translator without its key is skipped. With neither key: `503 server_not_configured`, as today.
- **The log** names the translator that answered (`translator=groq-gpt-oss-120b`), from a fixed list in `config.py`, never from a reply.
- **Docs:** README setup gets the Groq key; AGENTS.md "No paid AI" names Groq next to Gemini.

## Out of scope

- Choosing a translator on the page, or showing which one answered (log only, for now).
- Smaller chunks or showing lines as they arrive (ideas list).
- Groq's other models (the 20b and qwen are listed above for reference only).

## Inputs and outputs

No change to any route. The page sees the same replies and the same error codes.

## Rules

1. Groq is called at `https://api.groq.com/openai/v1/chat/completions` with the system instruction, the numbered lyrics, and the reply schema as a strict JSON schema; `temperature` 0; a cap on reply tokens.
2. A Groq reply whose finish reason is not `stop` is unusable (`length` → `translation_invalid`; `content_filter` → `translation_blocked`).
3. When every translator in the chain is busy, the last one's error is returned (`429 translation_rate_limited` or `503 translation_unavailable`).
4. Retries stay as today: each retry walks the chain again from the start.

## Security

- **Outside service:** a fixed https host, the same client rules as Gemini and LRCLIB (timeout, no redirects, no proxy from the environment, byte cap on the reply). The key goes in the `Authorization` header and is never logged, printed, or sent to the browser.
- **What is sent:** the lyric lines only, as with Gemini. Lyrics stay data, never instructions.
- **Untrusted output:** Groq's reply goes through the same parsing and per-line checks as Gemini's.
- **Logged:** the translator name and the existing counts. Never lyrics, titles, keys, or reply text.

## Acceptance checks

Backend (pytest, fakes for both services; no network):

- AC-1: With both keys, a request goes to Groq first, with the key in the `Authorization` header and a strict JSON schema.
- AC-2: Groq `429`, `503`, timeout, or connection error → the same request goes to Gemini, and the song opens.
- AC-3: A refused request (`400`) or a blocked reply from Groq does not move on.
- AC-4: Groq's reply passes the same checks: a line with kanji in the hiragana is asked again, then "Not available".
- AC-5: A Groq reply cut off (`length`) is `translation_invalid`; `content_filter` is `translation_blocked`.
- AC-6: Only `GROQ_API_KEY` set → Groq only; only `GEMINI_API_KEY` → Gemini only; neither → `503 server_not_configured`.
- AC-7: Every translator busy → the last error's code and status.
- AC-8: The log line names the translator that answered; no key or reply text appears in the log.
- AC-9: Groq's address is a fixed https host in `config.py`.

## Plan

- **Settings** (`config.py`): `TRANSLATORS` (name, service, model), the Groq URL, key name, timeout, token and byte caps; chunk, retry, and parallel settings lose their `GEMINI_` prefix.
- **Split `gemini.py`** into `translation_prompt.py` (instruction, reply schema, user message) and `reply_checks.py` (JSON and per-line checks), unchanged; `gemini.py` keeps one Gemini request.
- **New `groq.py`**: one chat-completions request, streamed with a byte cap, uncompressed; finish reasons and `json_validate_failed` mapped to the existing codes.
- **New `translators.py`**: `ReadyTranslator` (key and client hidden from `repr`), `ready_translators` (keys read per request), `request_versions` (walks the chain, then the shared checks).
- **Wiring:** `chunks.py`, `four_versions.py`, `song_versions.py`, and `app.py` pass the ready translators instead of one key and client; the app builds and closes a Groq client; the log gains `translator=`.
- **Renames** for code that is no longer Gemini-only: `ReplyLine`, `SongTranslation`, `translator_*` log fields; error messages name "the translator".
- **Tests:** `fake_groq.py`, `test_groq.py`, `test_translators.py`; autouse fixtures clear both keys and keep one translator per service.
