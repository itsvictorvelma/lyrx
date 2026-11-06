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

For a named song, LRCLIB (`backend/app/generation/lrclib.py`) is the source of the original Japanese lines. A Japanese lyric wins over an English translation. Among the lyrics that remain, an exact title and artist match wins, and then the longest plain lyric wins. Groq then supplies the readings and the English. The learner supplies the only audio file. The app does not ship a commercial recording.

## Routes

- `/songs/new` — new song. Chat, the four documents, and save.
- `/songs/:songId` — the saved song in [Learn Song](../learn-song/spec.md). Chat does not rewrite it.

Both routes are part of the local app. There is no login. `/import` and `POST /api/import` are not part of this product.

An unsaved draft lives in the page. Refresh or leaving the page drops it. The chat transcript is not stored. The new-song page sends the learner's message and does not send a saved song.

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

The browser never calls Groq and never sees the API key. The key is the local credential from `swytchcode auth connect Groq`. Application code does not read the key or set `Authorization`. Each Groq call is one Swytchcode execution of `groq.chat.completions.create`.

A message shaped like "title by artist" is the song name. A message of at least three words that is not shaped that way asks Groq to name the title and artist first. The server then searches LRCLIB at `https://lrclib.net/api/search`. Instrumental rows are skipped. A Japanese lyric wins over an English translation. An exact title match wins, then an exact artist match, then the longest plain lyric. A line that is only a square-bracket label is dropped. The original lines from that lyric stay as written. Groq fills them in groups of 12. Each group asks for the kanji readings and the English line. Kana in the original line is kept. Romaji is spelled from the hiragana. A group that comes back unusable is tried once more. If LRCLIB has no usable lyric, one Groq completion writes the whole draft.

The server builds each Groq request as one Swytchcode execution:

- `model` — `GROQ_MODEL`, default `openai/gpt-oss-120b`
- `messages` — one user message. No earlier transcript is included.
- `response_format` — strict JSON. A whole draft uses the schema named `lyric_draft`, with the draft fields above required and extra properties closed. A group from LRCLIB uses the schema named `lyric_slots`, with `readings` and `translationEnglish` required.
- `reasoning_effort` — `low`
- `include_reasoning` — `false`
- `temperature` — `0.6` for a lyric completion. Naming the song uses `0`.
- The completion is not streamed.
- `max_completion_tokens` — large enough to finish the JSON, and small enough that the estimated prompt tokens plus this cap stay within 8,000. Naming the song caps this at 200.

Groq's free plan for this model allows 8,000 tokens per minute and 200,000 tokens per day, counting prompt tokens and completion tokens together. Reasoning tokens are part of the completion count. `include_reasoning: false` omits the reasoning text from the message body and does not remove those tokens from `usage`. The measured call is [benchmarks/groq-token-usage.md](../../benchmarks/groq-token-usage.md).

If the prompt estimate leaves no room for a complete draft under 8,000 tokens, the server does not call Groq. It returns `generation_too_large`.

The new-song page disables Ask while that request is in progress. It does not start a second generation to repair the whole song. Swytchcode's policy for this method may retry HTTP 429, 503, and 504 up to three times inside a 90 second total timeout. Those retries belong to that one execution. HTTP 400 is not retried. The response ceiling for the method is 102,400 bytes.

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

`POST /api/songs` stores a valid draft as a published song and returns Song detail. `audioUrl` is null until an MP3 is stored. Saving a draft always creates a song. The server does not dedupe by title. There is no route that replaces a saved song's lyrics. A saved song is not rewritten from chat.

The save validates the draft before committing. A failed save does not add a song.

## Audio attach

The only upload is one MP3. The client filename is not required to be `audio.mp3`. The server checks the MPEG signature, enforces the configured size ceiling, measures duration, stores a checksum, and writes a generated storage name. The uploaded path is never used as the storage path.

`POST /api/songs/{songId}/audio` accepts multipart field `audio`. Replacing an existing file requires `replace=true`. The new file is staged until validation succeeds. A failure removes the staged file and leaves the previous audio in place.

The MP3 is attached on the saved song, after save. `/songs/new` does not upload audio. If the upload fails, the song remains saved without audio and the page shows a recoverable audio error.

Attaching audio does not call Groq.

## Screen behavior

`/songs/new` shows:

- A link back to Song Library
- A text field labeled Song and an Ask button
- A pending state while the request is working
- The confirmation line and the four documents after a valid draft
- Save, enabled only when a valid draft is on the page

A saved song does not show this composer. Refresh of a saved song shows the stored lines. The MP3 control is on that page.

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
- Prompt builder sends one user message and does not include an earlier transcript
- `max_completion_tokens` stays inside the 8,000-token minute when the prompt is large
- `generation_too_large` is returned without a Groq call when the prompt cannot fit
- Server confirmation line is built from title and line count
- MP3 signature acceptance and rejection, checksum, and generated storage name

### Integration

- A fixture draft saves one track and one lyric version and appears in the song list
- Saving the same title again creates another song
- A failed save does not add a song
- An invalid MP3 writes no file
- A failed replace leaves the previous audio in place
- Production and development both omit `POST /api/import`
- SQLite tests use real SQLite

Groq is not called from the default test run. The request body builder is tested locally. A manual or explicitly gated check may run one live `groq.chat.completions.create`.

### End-to-end

- Ask for a song, see four documents, save, and open it from Song Library.
- Leave without saving and confirm the library is unchanged.
- Open a saved song and confirm chat cannot replace its lines.
- Attach a valid MP3 and play it. Reject an invalid file with the song still readable.

## Sequencing

1. Freeze the draft, save, and audio contracts.
2. Validate drafts and build the Groq request without a live call in unit tests.
3. Add `POST /api/generations` and `POST /api/songs`.
4. Build `/songs/new`.
5. Add MP3 attach.
6. Remove the four-file import route and endpoint.

## Acceptance criteria

- A learner can request a song in chat and see Original, Hiragana, Romaji, and English.
- For a named song, the original lines come from LRCLIB and Groq supplies the readings and the English.
- A bad or oversized reply does not create a song and does not start another generation for the rest of the song.
- Save publishes a new song into the local library.
- A saved song is not rewritten from chat.
- The only upload is one validated MP3, and it can be missing.
- The Groq key stays on the server.
- `/import` and `POST /api/import` are gone.

## Risks

- Free-model wording can be wrong while the JSON shape is valid. The learner reads the documents before save.
- A prompt that cannot fit under 8,000 tokens is refused with `generation_too_large` and does not call Groq.
- Swytchcode retries a 429 inside one execution. The app must not stack its own retry on top.
- Lyric save and MP3 upload are two requests. A failed upload leaves a saved song with no audio.

## Non-goals and deferred work

- Accounts and a public multi-user host
- Stored chat transcripts
- Streaming tokens
- Automatic repair of a whole song
- A paid Groq plan
- Lyric text-file upload
- Line timing, audio scan, and a tempo control
