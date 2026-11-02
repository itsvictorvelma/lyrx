# Groq token usage

Measured on 29 October 2026 against the free plan for `openai/gpt-oss-120b`, through Swytchcode method `groq.chat.completions.create`.

The product rule that uses these numbers is in [Song creation](../specs/song-creation/spec.md).

## Who meters the tokens

Groq meters the API key. Swytchcode does not keep a token balance. It POSTs the chat completion to `https://api.groq.com/openai/v1/chat/completions` and injects the key stored by `swytchcode auth connect Groq`.

The response `usage` object is the count for that call:

- `prompt_tokens` — the request, including the JSON schema
- `completion_tokens` — everything the model generated
- `completion_tokens_details.reasoning_tokens` — the part of `completion_tokens` spent thinking before the JSON
- `total_tokens` — `prompt_tokens` + `completion_tokens`

`include_reasoning: false` drops the thinking text from `message.content`. It does not remove `reasoning_tokens` from `usage`. Those tokens still count toward the minute and the day.

## Free-plan ceilings

Published for `openai/gpt-oss-120b` on Groq's free plan. Confirmed against the Groq rate-limit docs on 29 October 2026. The account limits page is the source of truth if Groq changes them.

| Ceiling | Value | What it counts |
| --- | --- | --- |
| Tokens per minute | 8,000 | `prompt_tokens` + `completion_tokens` |
| Tokens per day | 200,000 | the same sum, across the day |
| Requests per minute | 30 | HTTP calls |
| Requests per day | 1,000 | HTTP calls |

A call that would pass the minute token budget is rejected with 429 or 413. The response includes `retry-after` and `x-ratelimit-remaining-tokens`. Request-count ceilings are not the limit a lyric generation hits. One song spends thousands of tokens, so 8,000 tokens per minute is the ceiling that matters.

Swytchcode's execution policy for this method retries 429, 503, and 504 up to 3 times, with backoff from 500 ms to 30 s, inside a 90 s total timeout. Idempotency mode is `none`, so a retry is another HTTP call. HTTP 400 is not retried. `max_response_bytes` is 102,400. `max_concurrent` is 5. The app still allows one lyric generation in flight, because two calls share the same 8,000-token minute.

## Measured call

Prompt: two original Japanese practice lines about morning rain. No existing song. One user message. Strict JSON schema with `title`, `artist`, and `lines[]` of `originalText`, `readingHiragana`, `pronunciationRomaji`, and `translationEnglish`.

Request settings:

| Field | Value |
| --- | --- |
| model | `openai/gpt-oss-120b` |
| temperature | 0.6 |
| reasoning_effort | `low` |
| include_reasoning | `false` |
| max_completion_tokens | 2,000 |
| stream | false |

Result: HTTP 200. Two lines. `finish_reason` `stop`.

| Usage field | Tokens |
| --- | --- |
| prompt_tokens | 220 |
| completion_tokens | 303 |
| reasoning_tokens | 37 |
| total_tokens | 523 |

Completion time was about 0.64 s. Queue time was about 0.07 s. The minute budget after this call was 8,000 − 523 = 7,477 tokens.

The Romaji for したたる came back as `shitatru`. The JSON shape was valid. Token count does not measure lyric accuracy.

## Measured failure

The same schema with `max_completion_tokens` 400 returned HTTP 400 `json_validate_failed` and an empty `failed_generation`. That status is on Swytchcode's non-retryable list, so the client did not send it again.

`max_completion_tokens` includes reasoning tokens. A cap of 400 was spent before a complete JSON object was written. The working call raised the cap to 2,000 and set `reasoning_effort` to `low`. Reasoning then cost 37 tokens, and the JSON fit in the remaining completion budget.

## What a full song costs

Not measured yet. Do not treat the following as a budget you can bill against.

The measured call wrote two lines for 303 completion tokens, 37 of them reasoning. If completion tokens grew only with line count, 40 lines would be several thousand completion tokens, and a revision would also send those lines back as prompt tokens. Input and output both come out of the same 8,000. One full song can fit in a minute. A second full song in that same minute can be rejected. The 200,000 daily ceiling is on the order of a few dozen full generations, once a real song has been measured.

`max_completion_tokens` for a real song has to be high enough to finish the JSON and low enough that estimated prompt tokens plus that cap stay within 8,000. When the prompt leaves no room, the server returns `generation_too_large` and does not call Groq.

Record the next full-song run in the section below. Replace the estimate with that measurement.

## Next measurement

| Field | Value |
| --- | --- |
| Date | |
| Song | |
| Lines | |
| Revision or first send | |
| prompt_tokens | |
| completion_tokens | |
| reasoning_tokens | |
| total_tokens | |
| HTTP status | |
| finish_reason | |

## How to reproduce the two-line call

From the repository root, with Groq connected:

```bash
swytchcode exec groq.chat.completions.create --body /tmp/lyrx-groq-smoke.json --json
```

The body is one user message, model `openai/gpt-oss-120b`, `reasoning_effort` `low`, `include_reasoning` false, `temperature` 0.6, `max_completion_tokens` 2000, and the strict `lyric_lines` schema. Read `usage` from the JSON response. Do not run this in the default test suite.
