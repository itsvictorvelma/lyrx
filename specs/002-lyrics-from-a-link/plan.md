# 002 — Plan

## Files

### Backend — `backend/`

| File | New or changed | Why |
|---|---|---|
| `src/lyrx/config.py` | changed | The link, fetch, page, candidate, and selection settings (see **Settings**) |
| `src/lyrx/errors.py` | changed | The 9 new codes in `ErrorCode` and `ERROR_TABLE`, with the spec's exact messages |
| `src/lyrx/schemas.py` | changed | `VersionsFromLinkRequest` (strict `url: str`), `VersionsFromLinkResponse` (`lyrics`, and `lines` or `limit`), `LyricPick` (Claude's strict selection reply). Internal frozen dataclasses: `CheckedLink`, `FetchedPage`, `PickedLines` |
| `src/lyrx/link_check.py` | new | `check_link(text) -> CheckedLink`: the 9 link rules, no network (AC-9–15) |
| `src/lyrx/address_check.py` | new | `is_public(address)` and `public_address(link, resolve, timeout)`: one lookup, every address must be public, returns the one to connect to (AC-16–18) |
| `src/lyrx/pinned_transport.py` | new | `PinnedTransport`, the small custom transport of Decision 6: sends a request to the checked address while keeping `Host`, SNI, and the certificate check on the host name (AC-19, 20) |
| `src/lyrx/page_fetch.py` | new | `fetch_page(link, network) -> FetchedPage`: the hop loop with manual redirects, the request headers, the 15 s deadline, the content-type and size caps, and the error mapping. Also `LinkNetwork` (the lookup and the transport, replaced in tests) (AC-19–32) |
| `src/lyrx/page_charset.py` | new | `decode_page(page) -> str`: picks the character set (header, then `<meta>`, then UTF-8) and decodes with `U+FFFD` for bad bytes (AC-33) |
| `src/lyrx/page_text.py` | new | `page_lines(text, media_type) -> list[str]`: HTML to text lines with `html.parser` (skipped elements, block breaks, `<br>`), or plain text split on line endings (AC-34, 36, 37) |
| `src/lyrx/candidate_lines.py` | new | `to_candidates(lines)` (the 6 code steps) and `check_candidate_size(candidates)` (the cost cap) (AC-38–42, 52) |
| `src/lyrx/lyric_pick_prompt.py` | new | The selection system prompt and `build_page_lines_message(candidates)` with `<page_lines>` and `[n]` labels (AC-47) |
| `src/lyrx/lyric_pick.py` | new | `request_lyric_lines(client, candidates) -> PickedLines`: the one selection call and its checks, then sort and de-duplicate (AC-46, 47, 49, 49b, 50, 51) |
| `src/lyrx/claude.py` | changed | `send_request` becomes `send_completion(client, *, system, user_message, schema, effort, max_tokens)`, shared by both calls, keeping the one SDK error mapping. `request_readings` calls it with today's values; behavior unchanged |
| `src/lyrx/versions_from_link.py` | new | The pipeline for one link, readable top to bottom: link → key → fetch → text → candidates → selection → spec 001's pipeline, or the over-limit reply (AC-43–45, 48, 53) |
| `src/lyrx/request_log.py` | changed | `logged_request(**fields)` and `RequestLog.add(...)` so the link route can fill its own fields as it goes; `add_tokens(usage, prefix="")`. Spec 001's call and log line are unchanged (AC-55) |
| `src/lyrx/app.py` | changed | `create_app(claude_client=None, link_network=None)`; route `POST /api/versions-from-link` (sync `def`, `response_model_exclude_none=True`) inside its log line (AC-54, 56) |
| `tests/network_guard.py` | new | The test-wide guard: patches `socket.getaddrinfo`, `socket.create_connection`, and `socket.socket.connect`/`connect_ex` to record and raise (AC-57) |
| `tests/fake_network.py` | new | The fake fetcher: a scripted `resolve` and an `httpx2.MockTransport`. Records each lookup, each connection target (the URL host the transport receives), each request, and each body chunk read |
| `tests/pages.py` | new | Invented page bodies and candidate sets the tests share (like `pastes.py`). No real lyrics |
| `tests/fake_claude.py` | changed | `messages.replies`: a queue of replies, one per call (selection first, then readings). `final_message` still works for spec 001 tests |
| `tests/conftest.py` | changed | Autouse network guard with a teardown check; `fake_network` fixture; the `app` fixture also passes the fake network |
| `tests/test_network_guard.py`, `tests/test_fake_network.py`, `tests/test_fake_claude.py` | new | Tests of the test setup (T1): the guard trips on a real lookup or connection; the fake network rebuilds links, records the dialed address and chunks as read; the fake Claude queue returns one reply per call. They test the fakes, so they cite no AC except AC-57 for the guard |
| `tests/test_<module>.py` | new | One per new module: `test_link_check`, `test_address_check`, `test_pinned_transport`, `test_page_fetch`, `test_page_charset`, `test_page_text`, `test_candidate_lines`, `test_lyric_pick_prompt`, `test_lyric_pick`, `test_versions_from_link`; plus `test_network_guard` |
| `tests/test_claude.py`, `tests/test_request_log.py` | changed | Cover the shared `send_completion` and the generic log fields; existing tests keep passing |

### Frontend — `frontend/`

| File | New or changed | Why |
|---|---|---|
| `src/lyrics/types.ts` | changed | The new `PageErrorCode`s; `LinkResult` (lines with lyrics, over-limit with lyrics and limit, error, unreadable, unreachable) |
| `src/lyrics/api.ts` | changed | `getFourVersionsFromLink(url)`. The fetch-and-parse part of `getFourVersions` becomes one shared `postJson`, so both calls check replies the same way (AC-2, 6) |
| `src/lyrics/errorMessages.ts` | changed | The 9 new messages; `overLimitNotice(limit)` builds "Note: … over the limit. <AC-48 sentence or AC-45 fallback> Remove some lines, then press Get four versions." (AC-6, 7) |
| `src/lyrics/LinkForm.tsx` | new | Its own `<form>`: labeled text input "Link to a lyrics page", button "Get four versions from link", disabled when blank or waiting (AC-1–3) |
| `src/lyrics/PasteForm.tsx` | changed | Controlled: `lyrics` and `onLyricsChange` come from `App`, so a link load can fill the box. The polite region shows a `statusText` prop instead of its own constant |
| `src/lyrics/pageState.ts` | new | The page's state type, the conversions from each request result, and `statusTextFor(state)`. Keeps `App.tsx` short |
| `src/App.tsx` | changed | Holds the paste text and the state; renders `LinkForm` above `PasteForm`; moves focus per state (AC-3–8) |
| `src/styles.css` | changed | The link form reuses the paste form's layout rules. No new color |
| `src/lyrics/LinkForm.test.tsx`, `src/lyrics/pageState.test.ts` | new | Tests next to what they test |
| `src/App.test.tsx`, `src/lyrics/{api,errorMessages,PasteForm}.test.ts(x)` | changed | New cases; PasteForm tests pass the new props |

### Root

| File | New or changed | Why |
|---|---|---|
| `README.md` | changed | The link flow in one paragraph; the folder map gains the new modules and test helpers; each link makes up to two Claude calls |
| `specs/README.md` | changed | At the end: status `done` |

## Approach

### The request, top to bottom (`versions_from_link.py`)

The route reads the body (`VersionsFromLinkRequest`, strict, so a missing or numeric `url` is `invalid_request`), then runs the pipeline inside `logged_request()`:

1. `check_link(body.url)` → `CheckedLink(url, host, port)`. `log.add(host=link.host)`.
2. `config.read_api_key()`, else `server_not_configured`. The Claude client is built here (or the fake from `app.state`), before any lookup.
3. `fetch_page(link, network)` → `FetchedPage(body, media_type, charset, redirects)`. `log.add(bytes=…, redirects=…)`.
4. `page_lines(decode_page(page), page.media_type)` → `to_candidates(...)`. `log.add(candidates=…, candidate_characters=…)`. `check_candidate_size(candidates)`.
5. `request_lyric_lines(client, candidates)` → `PickedLines(line_numbers, usage)`. `log.add_tokens(usage, prefix="select_")`, `log.add(selected=…)`.
6. `lyrics = "\n".join(candidates[n] for n in line_numbers)`; `paste = read_paste(lyrics)` (spec 001); `log.add(lines=…)`.
7. `check_limits(paste.text, paste.lines)` from `lines.py`. If it raises `input_too_large`, return `{lyrics, limit: error.details}`. No readings call.
8. Otherwise `make_four_versions(paste, client)` from `four_versions.py`, unchanged. Return `{lyrics, lines}`; `log.add_tokens(usage)`.

Steps 5 and 8 run inside a small helper that adds `step=select` or `step=readings` to the log when the error is one of the four model codes, then re-raises. Spec 001's `check_limits`, `read_paste`, and `make_four_versions` are reused as they are. `make_four_versions` runs its own limit check again, which is cheap and can no longer fail.

### Checking the link (`link_check.py`)

One parser only: `httpx2.URL`, the same one the request uses, so the check and the request can never disagree about the host (a second parser would open a parser-differential SSRF gap). In spec order:
- strip; length ≤ `MAX_LINK_CHARACTERS`; no `str.isspace()` or category `Cc` character inside;
- parse (`httpx2.InvalidURL` → `invalid_link`); scheme in `{"http", "https"}` (httpx2 lowercases it); non-empty host; empty `userinfo`; port `None`, 80, or 443;
- numeric host forms on the ASCII host (`url.raw_host`, so an IDN host is Punycode): if the last label is all digits or starts with `0x`, `ipaddress.IPv4Address(host)` must accept it (it refuses `0177.0.0.1`, `127.1`, `2130706433`). A host with `:` is IPv6 (only reachable through brackets); a `%` zone is refused;
- `url.copy_with(fragment=None)`.

It returns `CheckedLink` with the URL, the ASCII host, and the port (default 80/443 by scheme). It does no lookup, so "no lookup" holds by construction; the end-to-end tests assert it through the fake.

### Refusing private addresses (`address_check.py`)

- `is_public(address)`: use `address.ipv4_mapped` when present; public means `is_global and not is_multicast`. The explicit multicast check matters: Python marks `224.0.0.1` and `ff02::1` as global.
- `public_address(link, resolve, timeout)`: an IP host is checked with no lookup. Otherwise `resolve(host, port)` runs once (default: `socket.getaddrinfo(host, port, type=SOCK_STREAM)`, de-duplicated). It runs in a one-worker `concurrent.futures.ThreadPoolExecutor` with `result(timeout=remaining)`, because `getaddrinfo` has no timeout of its own and the spec's 15 s covers the whole fetch. Running out is `link_timeout`. `socket.gaierror`/`OSError` or an empty answer is `link_unreachable`. If any address is not public: `link_not_allowed`. It returns the first address.
- `ponytail:` only the first checked address is tried; no fallback to the others if it does not answer. Upgrade path: loop over the checked list.
- `ponytail:` a lookup that times out leaves its worker thread running until the OS resolver gives up. Upgrade path: an async resolver with cancellation.

### Pinning the connection (`pinned_transport.py`)

Checked against the installed `httpx2` 2.16.2 and `httpcore2`:
- `httpx2.Request("GET", link.url, headers=…)` fills `Host` from the real URL (`Request._prepare` adds `Host` from `url.netloc` only when it is absent).
- `PinnedTransport(inner, host, address).handle_request(request)` refuses (fails closed) any request whose host is not `host`. It builds a new `httpx2.Request` with `url=request.url.copy_with(host=str(address))` (httpx2 brackets an IPv6 address), the same headers (so `Host: lyrics.example` stays), `stream=request.stream`, and `extensions={**request.extensions, "sni_hostname": host}`. It passes it to `inner.handle_request`.
- `HTTPTransport.handle_request` passes `extensions` to `httpcore2`. `httpcore2`'s connection opens TCP to the URL host (the checked IP) and calls `start_tls(ssl_context, server_hostname=sni_hostname)` (`httpcore2/_sync/connection.py`, lines 101–142). The default context from `httpx2.create_ssl_context()` has `check_hostname=True` and `CERT_REQUIRED`, so the certificate is verified against the host name. A certificate error is an `ssl.SSLError` (an `OSError`), which `httpcore2` maps to `ConnectError` → `link_unreachable`.
- The real inner transport is `httpx2.HTTPTransport(verify=True, trust_env=False, retries=0, limits=httpx2.Limits(max_keepalive_connections=0))`, made fresh for each fetch and closed after it. No keep-alive, so a TLS connection opened for one host name is never reused for another that shares its IP.
- No `httpx2.Client` is used. The transport level has no cookie jar, no automatic redirects, no auth, and never reads `HTTP_PROXY`, `HTTPS_PROXY`, or `ALL_PROXY` (proxies come from `Client(trust_env=True)` only). So AC-20 and AC-24 hold by construction, and tests prove them.

`LinkNetwork` (in `page_fetch.py`) is a frozen dataclass with `resolve` and `make_transport: Callable[[], httpx2.BaseTransport]`. `LinkNetwork.real()` gives the defaults above. Tests pass the fake's `resolve` and a `make_transport` returning its `MockTransport`. The fake sits under `PinnedTransport`, so the pinning itself is tested: the fake sees the IP in the URL, `Host` in the headers, and `sni_hostname` in the extensions.

### The fetch (`page_fetch.py`)

- `deadline = time.monotonic() + config.FETCH_TOTAL_SECONDS`, read from `config` at call time so a test can lower it (AC-25).
- Each hop: `public_address(link, …)`, then a `GET` with headers `User-Agent: config.FETCH_USER_AGENT`, `Accept: config.FETCH_ACCEPT`, and `Accept-Encoding: config.FETCH_ACCEPT_ENCODING` (`gzip, deflate`: see risks about `br`). No body, no cookie, no `Authorization`, no `Referer`. The timeout extension is `{"connect": min(FETCH_CONNECT_SECONDS, remaining), "read": remaining, "write": remaining, "pool": remaining}`.
- **Redirects.** Status in `{301, 302, 303, 307, 308}`: close the response unread. A missing `Location` is `link_unreachable`. Count it; the 6th is `link_unreachable` before anything is requested. `current.url.join(location)` resolves a relative target. The joined URL goes through `check_link(str(...))` and `public_address` again, so a bad target fails with that check's code and is never requested.
- **The final response**, checked in this order before any body byte is read:
  1. not 2xx → `link_unreachable`;
  2. media type (`Content-Type` before `;`, stripped, lowercased) not in `PAGE_MEDIA_TYPES` → `link_not_a_page`;
  3. `Content-Length` decimal and over `MAX_PAGE_BYTES` → `link_too_large`.
- **Streaming cap.** `for chunk in response.iter_bytes()` counts decoded bytes. httpx2's decoders inflate gzip, deflate, and zstd in pieces of at most 1 MiB (`MAX_DECODE_CHUNK_SIZE`), so a gzip bomb never grows past the cap plus 1 MiB in memory. Over the cap: stop, close, `link_too_large`. After each chunk, a passed deadline is `link_timeout`. The bytes are only joined once the whole body is in and under the cap.
- **Errors.** `httpx2.TimeoutException` → `link_timeout`. Any other `httpx2.RequestError` (`ConnectError`, `ReadError`, `RemoteProtocolError`, `DecodingError` for a corrupt compressed body) → `link_unreachable`. All are raised `from None`, so no exception text reaches the reply or a traceback. The response is always closed in `finally`.
- It returns `FetchedPage(body, media_type, charset=response.charset_encoding, redirects)`.

### From bytes to text (`page_charset.py`, `page_text.py`)

- Charset: `page.charset` from the header; else for HTML, a regex for `<meta … charset=…>` or `content="…charset=…"` on the first `CHARSET_SNIFF_BYTES` bytes decoded as ASCII with `errors="replace"`; else `utf-8`. Decoding is `body.decode(name, errors="replace")`. A `LookupError` (an unknown name, or a non-text codec like `base64`) falls back to UTF-8 the same way.
- `text/plain`: `lines.normalize_line_endings(text).split("\n")` (spec 001's helper, not `str.splitlines`, which also breaks on `\x1c`, ` `, and others).
- HTML: an `html.parser.HTMLParser` subclass with `convert_charrefs=True`, so character references are decoded. Only `handle_starttag`, `handle_endtag`, and `handle_data` are overridden, so comments and attributes are never text. A per-tag depth counter for `SKIPPED_ELEMENTS`: data is dropped while any count is above 0. `<svg/>` goes through the default `handle_startendtag` (start, then end), so it nets to 0. A `<body>` start tag resets an unclosed `head`, as browsers do, so a page that omits `</head>` still has a body. `<br>` and the start and end of `BLOCK_ELEMENTS` add `"\n"`. The joined text is split on line endings. The element sets are named constants in `page_text.py`, like the ranges in `kana.py`: they are rules, not settings.

### The candidate lines (`candidate_lines.py`)

For each line, in spec order:
1. NFC.
2. Drop `U+200B`–`U+200D`, `U+2060`, `U+FEFF`, and every category `Cc` character except tab.
3. Drop Hangul: `1100–11FF`, `3130–318F`, `A960–A97F`, `AC00–D7AF`, `D7B0–D7FF`, `FFA0–FFDC` (named ranges).
4. Remove each bracket pair (`()`, `（）`, `[]`, `［］`, `「」`, `【】`) whose inside is only whitespace or category `P*` characters.
5. Tabs and runs of ASCII spaces become one space. Then trim the ends (see risks: the plan trims with `str.strip()`, so a `U+3000` inside the line is kept and one at the ends is not).
6. Re-apply NFC (removing a Hangul letter can leave a combining mark next to a kana), then keep the line only if `lines.has_japanese(line)`.

`check_candidate_size`: none → `link_no_japanese`; over `MAX_CANDIDATE_LINES` or `MAX_CANDIDATE_CHARACTERS` (on `"\n".join`) → `link_too_much_text`. Both run before any Claude call.

### The selection call (`lyric_pick.py`, `lyric_pick_prompt.py`)

- `claude.send_completion(client, system=PICK_SYSTEM_PROMPT, user_message=build_page_lines_message(candidates), schema=PICK_SCHEMA, effort=config.PICK_EFFORT, max_tokens=config.PICK_MAX_TOKENS)`. Same `messages.stream(...)` and `get_final_message()`, same model, same client and timeout, one completion. SDK, connection, and httpx2 errors → `model_unavailable` (spec 001's mapping, now in one place).
- `PICK_SCHEMA = {"type": "object", "properties": {"lyricLines": {"type": "array", "items": {"type": "integer"}}}, "required": ["lyricLines"], "additionalProperties": False}`.
- The system prompt holds the spec's eight points, written as plain sentences. The user message is `<page_lines>`, then `[n] text` per candidate, then `</page_lines>`. `ponytail:` a candidate holding the delimiter text is not escaped (as in `prompt.py`). The reply is numbers checked against the candidate range, so the worst case is a poor pick.
- Checks, in order: `claude.check_stop_reason` (refusal → `model_refused`, max_tokens → `model_output_truncated`, any other non-`end_turn` → `model_output_invalid`); `claude.join_text_blocks`; `json.loads` + `LyricPick.model_validate` (Pydantic `strict=True, extra="forbid"`, field `lyric_lines: list[int]` with alias `lyricLines`; strict mode refuses `true`, `1.5`, and `"2"`), with `JSONDecodeError`, `RecursionError`, `ValidationError` → `model_output_invalid`; every number in `0 … len(candidates) − 1`, else `model_output_invalid`; then `sorted(set(numbers))`; empty → `link_no_lyrics`.
- `PICK_MAX_TOKENS = 16000`. 400 numbers as JSON take about 1,600 output tokens. The rest is room for thinking at `low` effort, so truncation (a paid, failed request) stays unlikely. Tokens are billed as used, not as allowed.

### Reply shapes

`VersionsFromLinkResponse(lyrics: str, lines: list[VersionLine] | None = None, limit: dict[str, Any] | None = None)`. The route is registered with `response_model_exclude_none=True`, so a reply has `lyrics` plus exactly the one field that was set. `VersionLine` has no optional fields, so nothing inside `lines` is dropped. `limit` is spec 001's AC-48 `details` from the caught `ApiError`.

### Logging

The route wraps everything after the body check in `logged_request()`. Fields, filled as they become known: `status`, `code` (errors), `host` (the link's ASCII host only, never a redirect target's; the link check has already refused whitespace and control characters, so it cannot break the line), `bytes`, `redirects`, `candidates`, `candidate_characters`, `selected`, `lines`, `step` (model errors only), `select_input_tokens`, `select_output_tokens`, `input_tokens`, `output_tokens`, `duration_ms`, and `exception` on `internal_error` (class name only, as in spec 001). An `invalid_link` line has no `host`. Nothing from the path, query, fragment, IPs, headers, page, candidates, selection, lyrics, or replies is ever logged. The default `httpcore` and `httpx2` loggers stay at Python's default (warning) level, and their debug traces (which name the IP) are never enabled.

### The network guard (`tests/network_guard.py`, `conftest.py`)

An autouse fixture patches `socket.getaddrinfo`, `socket.create_connection`, `socket.socket.connect`, and `socket.socket.connect_ex`. Each records the attempt and raises `RealNetworkUsed` (an `AssertionError`). Raising alone is not enough: the route turns an unexpected exception into a 500, so a test could still pass. The fixture's teardown therefore calls `pytest.fail` if anything was recorded. `asyncio`'s self-pipe uses `socket.socketpair`, which is not patched, so `TestClient` keeps working. `test_network_guard.py` calls `socket.getaddrinfo("lyrics.example", 443)`, asserts the raise, and clears the record (AC-57). It lands in T1, before any fetch code exists.

### The page

- `App` owns `lyrics` (the paste box text) and `PageState` from `pageState.ts`:
  `idle` | `waiting {source: "paste" | "link"}` | `result {lines, fromLink}` | `overLimit {notice}` | `error {message, source}`.
- `statusTextFor(state)` fills `PasteForm`'s polite region:
  - waiting on a paste: "Working on your lyrics…";
  - waiting on a link: "Reading the page and working on your lyrics…";
  - a result from a link: "The lyrics from the page are also in the paste box. You can fix them there and press Get four versions.";
  - over the limit: the notice;
  - otherwise empty.
- Both buttons get `waiting = state.kind === "waiting"`, so neither can start a second request. Starting either request sets `waiting`, which clears the old result, error, and notice.
- `getFourVersionsFromLink(url)` validates a 200 reply before anything changes. It needs a string `lyrics` and exactly one own `lines` or `limit`. `limit` must be a non-array object. `lines` must pass the existing `isLinesReply`. Anything else is `unreadable`, and then neither `lyrics` nor the result changes.
- Focus, by effect on `state`:
  - `result` → the result heading (existing `ResultHeading`);
  - `overLimit` → the paste box;
  - `error` from a link → the link input;
  - `error` from a paste → the paste box (spec 001, unchanged).
- `lyrics` is set only on `result` from a link and on `overLimit`. It is a controlled `<textarea>` value, never HTML.
- The link input is `type="text"` with `inputMode="url"`. `type="url"` would let the browser block a bad link with its own tooltip instead of the server's `invalid_link` message.

## Settings (`config.py`)

| Name | Value |
|---|---|
| `MAX_LINK_CHARACTERS` | `2048` |
| `ALLOWED_LINK_SCHEMES` | `frozenset({"http", "https"})` |
| `ALLOWED_LINK_PORTS` | `frozenset({80, 443})` |
| `MAX_REDIRECTS` | `5` |
| `REDIRECT_STATUSES` | `frozenset({301, 302, 303, 307, 308})` |
| `FETCH_USER_AGENT` | `"Lyrx/0.1 (local lyrics reader)"` |
| `FETCH_ACCEPT` | `"text/html, application/xhtml+xml, text/plain"` |
| `FETCH_ACCEPT_ENCODING` | `"gzip, deflate"` |
| `FETCH_TOTAL_SECONDS` | `15` |
| `FETCH_CONNECT_SECONDS` | `5` |
| `MAX_PAGE_BYTES` | `2 * 1024 * 1024` (2,097,152) |
| `PAGE_MEDIA_TYPES` | `frozenset({"text/html", "application/xhtml+xml", "text/plain"})` |
| `CHARSET_SNIFF_BYTES` | `1024` |
| `DEFAULT_CHARSET` | `"utf-8"` |
| `MAX_CANDIDATE_LINES` | `400` |
| `MAX_CANDIDATE_CHARACTERS` | `16000` |
| `PICK_EFFORT: Final` | `"low"` |
| `PICK_MAX_TOKENS` | `16000` |

## Error codes

| Code | HTTP | Raised in |
|---|---|---|
| `invalid_link` | 400 | `link_check` (link and every redirect target) |
| `link_not_allowed` | 400 | `address_check` |
| `link_unreachable` | 502 | `address_check` (lookup failure), `page_fetch` (connect, TLS, reset, decode, non-2xx, 6th redirect, missing `Location`) |
| `link_timeout` | 504 | `address_check` (lookup), `page_fetch` (connect timeout, deadline) |
| `link_too_large` | 422 | `page_fetch` |
| `link_not_a_page` | 422 | `page_fetch` |
| `link_no_japanese` | 422 | `candidate_lines` |
| `link_too_much_text` | 422 | `candidate_lines` |
| `link_no_lyrics` | 422 | `lyric_pick` |

Messages are copied from the spec's table into `ERROR_TABLE` and the page's map, word for word. Spec 001 codes keep their status and messages.

## Side effects

- **Dependencies: none new.** `httpx2` (approved, already a direct dependency) and `httpcore2` (its own dependency) provide the transport, `MockTransport`, the `sni_hostname` extension, and the bounded decoders. Everything else is the standard library: `html.parser`, `ipaddress`, `socket`, `concurrent.futures`, `codecs`, `unicodedata`, `re`. The frontend uses no new package.
- `brotli` is **not** installed, so httpx2 cannot decode `br`. The plan does not add it (see risks).
- `claude.py` and `request_log.py` are refactored for reuse. The tests check that spec 001's behavior and log line are unchanged.
- `create_app` gains a `link_network` argument. Nothing is written to disk. No database, no cache, no CI change.
- The guard applies to every backend test, spec 001's included.

## Risks

- **Test addresses.** Python's `ipaddress` marks the documentation ranges (`192.0.2/24`, `198.51.100/24`, `203.0.113/24`, `2001:db8::/32`) as not global. So under the spec's own rule, `203.0.113.10` is refused. AC-18 still holds, because the request is refused either way. But any test that needs an address that passes the check must use a globally routable one. `tests/fake_network.py` defines one `PUBLIC_ADDRESS` constant for that (for example `93.184.215.14`). No packet is ever sent to it.
- **`U+3000` at a line's ends.** Spec 001's `split_lines` uses `rstrip()`, which removes a trailing full-width space. If the candidate step kept one, `lyrics` would change when re-split, which breaks AC-44 and `lines[i].original == line i`. The plan trims all Unicode whitespace at the ends and keeps `U+3000` inside (AC-41 still holds). Needs a yes from the user, since the spec says "kept as written".
- **`br` bodies.** With `Accept-Encoding: gzip, deflate`, a compliant server never sends `br`. If one does, httpx2 passes the bytes through undecoded. They count against the cap (still safe), decode as noise, and end as `link_no_japanese`. Real `br` support would need the `brotli` package (not requested).
- **The lookup thread.** A lookup that hangs past the deadline returns `link_timeout` on time, but its thread lingers until the OS resolver gives up (marked `ponytail:`).
- **`sni_hostname` relies on httpcore2 internals that are documented but not under test.** The default suite cannot open a TLS connection (no network). One manual run against a real https lyrics page before the PR confirms SNI and the certificate check. Unit tests pin what `PinnedTransport` hands down.
- **HTML that is not well nested.** An unclosed skipped element (for example `<nav>` with no `</nav>`) hides the rest of the page. That is a safe failure (`link_no_japanese` or fewer candidates), and site-specific fixes are out of scope.
- **Parsing speed.** `html.parser` on a 2 MiB page takes on the order of a second. The route is a sync `def`, so the work runs in FastAPI's threadpool, not on the event loop.
- **Size.** About 4,500 lines in total (roughly 1,500 source and 3,000 tests; see `tasks.md`), well over the 800-line threshold. It needs the user's permission before T1.

## Decisions before the build (user, 2026-11-17)

- Line ends are trimmed, full-width space included (spec Amendment); full-width spaces inside a line are kept.
- No Brotli support and no new dependency.
- The link route's `invalid_request` uses its own message: "The request must be JSON with a string field url." `ApiError`'s optional `message` (spec 001, T10) carries it.
- The user approved the size: 10 tasks, about 4,500 lines.
