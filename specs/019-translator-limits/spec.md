# 019 — Translator request limits

Status: approved

## Goal

A call to Groq or Gemini never runs on without end and never reads an unbounded reply. Today the 45 s timeout restarts at every connect and read step, so a reply that trickles in can run for a long time, and Gemini's reply is read whole with no byte cap. Nothing changes for the learner when the translators behave.

## In scope

- One overall deadline per translator request (Groq and Gemini), on top of the existing per-step timeout.
- Gemini's reply is streamed and capped like Groq's, with `GEMINI_MAX_REPLY_BYTES` in `config.py`.
- Remove the two `ponytail:` comments these replace.

## Out of scope

- Changing the per-step timeouts, the models, the prompt, or the Groq-then-Gemini order.
- Retrying a request that hit the deadline (the existing fallback to Gemini still applies).
- Any page change.

## Rules

- `config.TRANSLATOR_DEADLINE_SECONDS = 45`: a request that has not finished reading its reply 45 s after it started is abandoned.
- The deadline is checked between reply chunks. One read step is still capped by the per-step timeout, so the worst case is under about 90 s instead of unbounded. A `ponytail:` comment records this.
- A request past the deadline raises `ApiError("translation_unavailable", reason="deadline")`, the same code a timeout gives today, so the existing Groq → Gemini fallback handles it unchanged.
- `config.GEMINI_MAX_REPLY_BYTES = 512 * 1024`, the same as Groq. A Gemini reply over it raises `ApiError("translation_invalid", reason="too_large")`, matching Groq's behavior.
- The deadline and cap checks are shared by both translators only if the shared code stays short and clear; two small functions in their own files are fine.

## Security

- Untrusted input: the translator replies. The byte cap is enforced while reading, before anything parses the reply.
- What is sent to an outside service: unchanged.
- What is logged: only the reason word (`deadline`, `too_large`). Never reply text or the key.

## Acceptance checks

- AC-1: A fake Groq transport that sends a reply in slow chunks past the deadline gives `translation_unavailable` with reason `deadline`.
- AC-2: The same for Gemini.
- AC-3: A fake Gemini reply one byte over `GEMINI_MAX_REPLY_BYTES` gives `translation_invalid` with reason `too_large`; one at the cap is parsed normally.
- AC-4: A normal Groq and Gemini reply within the deadline and cap still works (existing tests keep passing).
- AC-5: When Groq hits the deadline, the request falls back to Gemini as it does for a timeout.

Tests use a fake clock or a fake transport; no test sleeps for real or calls the network.

## Plan

- New `translation/reply_limits.py`: `deadline_from_now()` and `read_within_limits(response, max_bytes, deadline)`, which reads the streamed reply chunk by chunk and stops on the byte cap or the deadline. It replaces `groq.read_capped`.
- `groq.py`: `send_request` takes a deadline when it starts and reads through `read_within_limits`.
- `gemini.py`: `send_request` streams like Groq (`client.stream`) and returns the body bytes; `parse_envelope` takes bytes.
- `chain.py`: `deadline` joins `BUSY_REASONS`, so the next translator is tried (AC-5).
- `config.py`: `TRANSLATOR_DEADLINE_SECONDS`, `GEMINI_MAX_REPLY_BYTES`.
- Tests: `tests/fake_clock.py` (a scripted `monotonic`), `tests/translation/test_reply_limits.py` (AC-1, AC-2), `test_gemini.py` (AC-3), `test_chain.py` (AC-5). README folder map gets the new module.
