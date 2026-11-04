---
cursor:
  subagentId: "bc-43f25a2f-93d8-5ec7-9282-d2774358e7bf"
---

# Song creation specification

Parent plan: [Prototype 1 build plan](../../AGENTS.md)

Dependencies and consumers:

- [Application foundation](../app-foundation/spec.md)
- [Song Library](../song-library/spec.md)
- [Learn Song](../learn-song/spec.md)
- [Audio player](../audio-player/spec.md)

## Goal

Let one learner ask for a song in chat, see four aligned lyric documents, save that song into the local library, and attach one MP3.

The model writes the lyrics. The learner supplies the only audio file. The app does not scrape a lyrics site and does not ship a commercial recording.

## Routes

- `/songs/new` — new song. Chat, live documents, save, and an optional MP3 choice.
- `/songs/:songId` — saved song. The same chat can replace the lyrics. See [Learn Song](../learn-song/spec.md).

Both routes are part of the local app. There is no login. `/import` and `POST /api/import` are not part of this product.

An unsaved draft lives in the page. Refresh or leaving the page drops it. The chat transcript is not stored. A revision sends the current lines with the new sentence.

## Lyric draft

The model returns structured data. The server checks it before the page renders documents. The visible chat line is a short confirmation the server builds from that draft, such as the title and the line count. The model is not asked for a second prose reply.

Draft fields:

- `title`
- `artist`
- `sourceLanguage` — server sets `ja`
- `targetLanguage` — server sets `en`
- `lines`

Each line:

- `originalText` — Japanese as written
- `readingHiragana` — full hiragana reading
- `pronunciationRomaji` — Hepburn pronunciation
- `translationEnglish` — direct English meaning

The server assigns a zero-based `index` after a valid parse. Stable line ids are assigned when the song is saved. The draft rejects an empty title, an empty artist, an empty line list, a missing layer, or a blank layer on a line that has any text. Timing fields are rejected.

Hiragana is required on every line. The learner can hide that document on the reading screen.

## Generation call

One user send is one Swytchcode execution of `groq.chat.completions.create`. The browser never calls Groq and never sees the API key. The key is the local credential from `swytchcode auth connect Groq`. Application code does not read the key or set `Authorization`.

The server builds this request:

- `model` — `GROQ_MODEL`, default `openai/gpt-oss-120b`
- `messages` — one user message. The first send contains the learner's sentence. A revision contains that sentence plus the current title, artist, and lines. No earlier transcript is included.
- `response_format` — strict JSON schema named `lyric_draft`, with the draft fields above required and extra properties closed
- `reasoning_effort` — `low`
- `include_reasoning` — `false`
- `temperature` — `0.6`
- `stream` — false
- `max_completion_tokens` — large enough to finish the JSON, and small enough that the estimated prompt tokens plus this cap stay within 8,000

Groq's free plan for this model allows 8,000 tokens per minute and 200,000 tokens per day, counting prompt tokens and completion tokens together. Reasoning tokens are part of the completion count. `include_reasoning: false` omits the reasoning text from the message body and does not remove those tokens from `usage`. The measured call is [benchmarks/groq-token-usage.md](../../benchmarks/groq-token-usage.md).

If the prompt estimate leaves no room for a complete draft under 8,000 tokens, the server does not call Groq. It returns `generation_too_large`.

The handler keeps a single generation in flight. It does not start a second completion to repair a bad draft. Swytchcode's policy for this method may retry HTTP 429, 503, and 504 up to three times inside a 90 second total timeout. Those retries belong to that one execution. HTTP 400 is not retried. The response ceiling for the method is 102,400 bytes.

The server reads `choices[0].message.content`, parses the JSON, and runs the line checks. The Groq `usage` object is the token count for that call. Logs may record token totals and the song id. Logs do not record the API key or the full lyric text by default.

### Generation errors

Use the shared error envelope.

| Code | When |
| --- | --- |
| `generation_invalid` | The reply is empty, cut off, or fails the line checks. The learner can send again. |
| `generation_too_large` | The song cannot fit in one 8,000-token call. |
| `groq_rate_limited` | Groq returns 429 or 413, including after Swytchcode's retries. |
| `groq_unavailable` | Timeout, or Groq returns 503 or 504 after retries. |
| `groq_unauthorized` | The local Groq credential is missing or rejected. |

Messages are safe. They do not include the key, request ids from Groq, or response bodies.

Read endpoints still start when Groq is not connected. Only generation fails.

## Save

`POST /api/songs` stores a valid draft as a published song and returns Song detail. `audioUrl` is null until an MP3 is stored. Saving a new draft always creates a song. The server does not dedupe by title.

`PUT /api/songs/{songId}/lyrics` replaces the lyric version of that song when the learner saves from the saved-song chat. The attached audio stays. A missing song returns `song_not_found`.

Both writes validate the draft before committing. A failed write leaves the previous saved song in place.

## Audio attach

The only upload is one MP3. The client filename is not required to be `audio.mp3`. The server checks the MPEG signature, enforces the configured size ceiling, measures duration, stores a checksum, and writes a generated storage name. The uploaded path is never used as the storage path.

`POST /api/songs/{songId}/audio` accepts multipart field `audio`. Replacing an existing file requires `replace=true`. The new file is staged until validation succeeds. A failure removes the staged file and leaves the previous audio in place.

On `/songs/new`, the learner may choose a file before save. Save writes the lyrics first, then uploads the file to the new id. If the upload fails, the song remains saved without audio and the page shows a recoverable audio error.

Attaching audio does not call Groq.

## Screen behavior

`/songs/new` shows:

- A way back to Song Library
- A text field and a send button
- A pending state while Groq is working
- The confirmation line and the four documents after a valid draft
- Save, enabled only when a valid draft is on the page
- One file input for the MP3

A saved song uses the same composer. Send replaces the documents on the page. Save writes that replacement. Until save, refresh shows the last stored version.

The reading layout, hide and show, and the player are specified in [Learn Song](../learn-song/spec.md) and [Audio player](../audio-player/spec.md).

## Accessibility

- The composer has a persistent label and a visible send control.
- Pending, success, rate-limit, and validation messages use a live region and do not move focus by surprise.
- Save and the file input are keyboard operable.
- The file input is not drag-and-drop only.
- Documents rendered from a draft use the same names and language annotations as Learn Song.

## Tests

### Unit

- Draft schema accepts four filled layers and rejects a missing or blank layer
- Timing fields are rejected
- Prompt builder sends one user message and, on revision, the current lines only
- `max_completion_tokens` stays inside the 8,000-token minute when the prompt is large
- `generation_too_large` is returned without a Groq call when the prompt cannot fit
- Server confirmation line is built from title and line count
- MP3 signature acceptance and rejection, checksum, and generated storage name

### Integration

- A fixture draft saves one track and one lyric version and appears in the song list
- Lyric replacement keeps the existing audio
- A failed lyric write does not change the stored version
- An invalid MP3 writes no file
- A failed replace leaves the previous audio in place
- Production and development both omit `POST /api/import`
- SQLite tests use real SQLite

Groq is not called from the default test run. The request body builder is tested locally. A manual or explicitly gated check may run one live `groq.chat.completions.create`.

### End-to-end

- Ask for a song, see four documents, save, and open it from Song Library.
- Revise a saved song, save, and see the replacement after reload.
- Leave without saving and confirm the library is unchanged.
- Attach a valid MP3 and play it. Reject an invalid file with the song still readable.

## Sequencing

1. Freeze the draft, save, and audio contracts.
2. Validate drafts and build the Groq request without a live call in unit tests.
3. Add `POST /api/generations`, `POST /api/songs`, and `PUT /api/songs/{songId}/lyrics`.
4. Build `/songs/new` and the saved-song composer.
5. Add MP3 attach.
6. Remove the four-file import route and endpoint.

## Acceptance criteria

- A learner can request a song in chat and see Original, Hiragana, Romaji, and English from one Groq completion.
- A bad or oversized reply does not create a song and does not trigger a second app-level completion.
- Save publishes the song into the local library.
- A later message can replace the lyrics of that song after an explicit save.
- The only upload is one validated MP3, and it can be missing.
- The Groq key stays on the server.
- `/import` and `POST /api/import` are gone.

## Risks

- Free-model wording can be wrong while the JSON shape is valid. The learner reads the documents before save.
- A long revision can exceed 8,000 tokens because the current lines are both input and output. The server refuses that call instead of spending the minute on a truncated reply.
- Swytchcode retries a 429 inside one execution. The app must not stack its own retry on top.
- Lyric save and MP3 upload are two requests. A failed upload leaves a saved song with no audio.

## Non-goals and deferred work

- Accounts and a public multi-user host
- Stored chat transcripts
- Streaming tokens
- A lyrics website or catalog API
- Automatic repair completions
- A paid Groq plan
- Lyric text-file upload
- Line timing, audio scan, and a tempo control
