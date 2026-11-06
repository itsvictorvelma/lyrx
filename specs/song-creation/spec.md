# Song creation specification

Prototype 2.

Dependencies and consumers:

- [Application foundation](../app-foundation/spec.md)
- [Song Library](../song-library/spec.md)
- [Learn Song](../learn-song/spec.md)
- [Audio player](../audio-player/spec.md)

## Goal

Let one learner type a song name, see Original, Hiragana, Romaji, and English, save that song, and attach one MP3.

One search. LRCLIB supplies the original Japanese lines. A Japanese lyric wins over an English translation. One Groq completion supplies the hiragana readings and the direct English. Romaji is spelled from the hiragana. One user send is one completion. A bad draft is not saved and does not start a repair completion.

The learner supplies the only audio file. The app does not ship a recording.

## Routes

- `/`, `/search`, and `/songs/new` are the same search. The song-name field, the result, and save live here.
- `/songs/:songId` is the saved song in [Learn Song](../learn-song/spec.md). A later search does not rewrite it.

Both are part of the local app. There is no login. `/import` and `POST /api/import` are not part of this product.

The search result fills this screen. Saved songs stay in the menu or the library section from [Song Library](../song-library/spec.md). They are not a column beside the documents.

An unsaved draft lives in the page. Refresh or leaving the page drops it. The text the learner sent is not stored. The search does not send a saved song.

## Lyric draft

LRCLIB supplies each `originalText`. The completion supplies the hiragana reading and the direct English. The server spells romaji from the hiragana. The server checks the draft before the page renders documents. The visible status line is a short confirmation the server builds from that draft, such as the title and the line count. The model is not asked for a prose reply.

Draft fields:

- `title`
- `artist`
- `sourceLanguage` — server sets `ja`
- `targetLanguage` — server sets `en`
- `lines`

Each line:

- `originalText` — the Japanese line from LRCLIB, unchanged
- `readingHiragana` — full hiragana reading
- `pronunciationRomaji` — Hepburn pronunciation spelled from the hiragana
- `translationEnglish` — direct English meaning

The server assigns a zero-based `index` after a valid parse. Stable line ids are assigned when the song is saved. The draft rejects an empty title, an empty artist, an empty line list, a missing layer, or a blank layer on a line that has any text. Timing fields are rejected.

Hiragana is required on every line of a new draft. The learner can hide that document on the reading screen. Kana already in the original line is kept.

## One search

The learner sends one song name to `POST /api/generations`.

- Text shaped like "title by artist" is the title and the artist.
- Any other text is the title. The server does not call Groq to invent an artist.

The server searches LRCLIB at `https://lrclib.net/api/search`. Instrumental rows are skipped. A line that is only a square-bracket label is dropped. A Japanese lyric wins over an English translation. An English translation is not used. Among Japanese lyrics, an exact title match wins, then an exact artist match when the learner included an artist, then the longest plain lyric.

The draft's title and artist are the title and artist of that recording. The original lines stay as written. If LRCLIB has no usable Japanese lyric, or the lyric fetch fails, the server returns the shared error envelope, does not call Groq, and does not save.

## One completion

A usable Japanese lyric is filled by one Groq completion. That completion supplies the hiragana readings and the direct English for those lines. Romaji is spelled from the hiragana after the completion returns. The model is not the source of the romaji.

The browser never calls Groq and never sees the API key. The key is the local credential from `swytchcode auth connect Groq`. Application code does not read the key or set `Authorization`. The call is one Swytchcode execution of `groq.chat.completions.create`.

The server builds that request as:

- `model` — `GROQ_MODEL`, default `openai/gpt-oss-120b`
- `messages` — one user message. No earlier text is included. The original lines in that message are the LRCLIB lines.
- `response_format` — strict JSON, schema named `lyric_slots`, with `readings` and `translationEnglish` required and extra properties closed. The result lines up with the LRCLIB lines in order.
- `reasoning_effort` — `low`
- `include_reasoning` — `false`
- `temperature` — `0.6`
- The completion is not streamed.
- `max_completion_tokens` — large enough to finish the JSON, and small enough that the estimated prompt tokens plus this cap stay within 8,000.

There is no second completion in that send. There is no completion that only names the song, no completion per group of lines, and no completion that writes the original lines.

Groq's free plan for this model allows 8,000 tokens per minute and 200,000 tokens per day, counting prompt tokens and completion tokens together. Reasoning tokens are part of the completion count. `include_reasoning: false` omits the reasoning text from the message body and does not remove those tokens from `usage`. The measured call is [benchmarks/groq-token-usage.md](../../benchmarks/groq-token-usage.md).

If the prompt estimate leaves no room for a complete result under 8,000 tokens, the server does not call Groq. It returns `generation_too_large`. Nothing is saved.

The search screen disables Send while that request is in progress. A bad draft is not saved and does not start a repair completion. Swytchcode's policy for this method may retry HTTP 429, 503, and 504 up to three times inside a 90 second total timeout. Those retries belong to that one execution. They are not a second lyric completion. HTTP 400 is not retried. The response ceiling for the method is 102,400 bytes.

The server reads `choices[0].message.content`, parses the JSON, keeps the LRCLIB lines, spells the romaji, and runs the line checks. The Groq `usage` object is the token count for that call. Logs may record token totals and the song id. Logs do not record the API key or the full lyric text by default.

The learner may send again. That is a new send, and it is one new completion. The server does not start it on its own.

### Generation errors

Use the shared error envelope.

| Code | When |
| --- | --- |
| `generation_invalid` | The reply is empty, cut off, or fails the line checks. Nothing is saved. No repair completion starts. The learner can send again. |
| `generation_too_large` | The song cannot fit in one 8,000-token completion. Groq is not called. |
| `groq_rate_limited` | Groq returns 429 or 413, including after Swytchcode's retries. |
| `groq_unavailable` | Timeout, or Groq returns 503 or 504 after retries. |
| `groq_unauthorized` | The local Groq credential is missing or rejected. |

A search with no usable Japanese lyric uses the same envelope, does not call Groq, and does not save.

Messages are safe. They do not include the key, request ids from Groq, or response bodies.

Read endpoints still start when Groq is not connected. Only generation fails.

## Save

`POST /api/songs` stores a valid draft as a published song and returns Song detail. `audioUrl` is null until an MP3 is stored. Saving a draft always creates a song. The server does not dedupe by title. There is no route that replaces a saved song's lyrics. A saved song is not rewritten by a later search.

The save validates the draft before committing. A failed save does not add a song. A draft that failed the line checks cannot be saved.

## Audio attach

The only upload is one MP3. The client filename is not required to be `audio.mp3`. The server checks the MPEG signature, enforces the configured size ceiling, measures duration, stores a checksum, and writes a generated storage name. The uploaded path is never used as the storage path.

`POST /api/songs/{songId}/audio` accepts multipart field `audio`. Replacing an existing file requires `replace=true`. The new file is staged until validation succeeds. A failure removes the staged file and leaves the previous audio in place.

The MP3 is attached on the saved song, after save. The search screen does not upload audio. If the upload fails, the song remains saved without audio and the page shows a recoverable audio error.

Attaching audio does not call Groq.

## Screen behavior

The search screen shows:

- A way to saved songs, the menu or the library section from [Application foundation](../app-foundation/spec.md)
- A text field labeled Song and a Send button
- A pending state while the request is working
- The confirmation line and the four documents after a valid draft
- Save, enabled only when a valid draft is on the page

After a valid draft, the four documents fill the screen. The song field stays the way to send again. It is not a second column. Document order, hide and show, and the line mark are specified in [Learn Song](../learn-song/spec.md). The player is on the saved song, specified in [Audio player](../audio-player/spec.md).

A saved song does not show this field. Refresh of a saved song shows the stored lines. The MP3 control is on that page.

## Accessibility

- The song field has a persistent label and a visible Send control.
- Pending, success, rate-limit, and validation messages use a live region and do not move focus by surprise.
- Save and the file input are keyboard operable.
- The file input is not drag-and-drop only.
- Documents rendered from a draft use the same names and language annotations as Learn Song.

## Tests

### Unit

- Draft schema accepts four filled layers and rejects a missing or blank layer
- Original lines in a named-song draft are the LRCLIB lines
- A Japanese lyric is chosen over an English translation
- Timing fields are rejected
- The request builder sends one user message and does not include an earlier send
- One send builds one `groq.chat.completions.create` body
- A bad draft does not build a second completion
- No Groq body is built when LRCLIB has no usable Japanese lyric
- Romaji stored on the draft is the spelling of the hiragana
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

- Type a song name, see four documents, save, and open it from the library section. The documents fill the screen.
- Leave without saving and confirm the library is unchanged.
- Open a saved song and confirm a later search does not replace its lines.
- Attach a valid MP3 and play it. Reject an invalid file with the song still readable.

## Acceptance criteria

- A learner can type a song name and see Original, Hiragana, Romaji, and English.
- The original lines come from LRCLIB. A Japanese lyric wins over an English translation.
- Groq supplies the hiragana readings and the direct English. Romaji is spelled from the hiragana.
- One user send is one completion.
- A bad or oversized reply does not create a song and does not start a repair completion.
- A miss on LRCLIB does not call Groq and does not save.
- Save publishes a new song into the library section.
- A saved song is not rewritten by a later search.
- The only upload is one validated MP3, and it can be missing.
- The Groq key stays on the server.
- `/import` and `POST /api/import` are gone.
- The search result is not shown beside a song sidebar.

## Risks

- Free-model wording can be wrong while the JSON shape is valid. The learner reads the documents before save.
- A prompt that cannot fit under 8,000 tokens is refused with `generation_too_large` and does not call Groq.
- Swytchcode retries a 429 inside one execution. The app must not start a repair completion on top of that.
- Lyric save and MP3 upload are two requests. A failed upload leaves a saved song with no audio.

## Out of scope

- A second model
- LangChain and LangGraph
- A repair completion, a completion per group of lines, or a completion that writes the original lines
- Groq choosing the song name
- Accounts and a public multi-user host
- A stored transcript of searches
- Streaming tokens
- A paid Groq plan
- Lyric text-file upload
- Line timing, audio scan, and a tempo control
- Spotify playback. That is specified in [Audio player](../audio-player/spec.md).
