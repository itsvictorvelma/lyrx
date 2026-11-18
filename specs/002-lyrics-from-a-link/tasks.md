# 002 — Tasks

Each task is one test-writer → implementer → reviewer round. Server tests use the fake network and spec 001's fake Claude client; no test calls the network or the Claude API. Line counts are rough estimates (source + tests).

- [ ] T1 (AC-57; test setup): The network guard and the test fakes.
  - `tests/network_guard.py`: autouse in `conftest.py`. It records and raises on `socket.getaddrinfo`, `socket.create_connection`, and `socket.socket.connect`/`connect_ex`. Teardown fails the test if anything was recorded.
  - `test_network_guard.py` proves it trips on a real lookup.
  - `tests/fake_network.py`: scripted `resolve` with per-call answers and failures; `MockTransport` handler with scripted responses, redirects, slow and oversized bodies, and connect, TLS, and timeout errors. Records lookups, connection targets, requests, and chunks read. Defines `PUBLIC_ADDRESS` (globally routable).
  - `fake_claude.py`: `messages.replies` queue.
  - `tests/pages.py`: invented pages.
  - Spec 001's suite still passes under the guard.
  - ~220 lines.
- [ ] T1b (AC-58 to AC-73, user priority 2026-11-17): Paste cleanup. One shared cleanup module (Hangul and zero-width removal, empty brackets, trimming, splitting over-long lines at whitespace incl. U+00A0 then after 。！？!?) used by `read_paste` before the limits. The link-route parts of AC-70/71 are tested when T6/T8 build the candidates and the route.
- [ ] T2 (AC-9, 10, 11, 12 link part, 13, 14, 15 unit part): Link rules.
  - `link_check.py`, `CheckedLink` in `schemas.py`, the 9 new codes and messages in `errors.py`, and the link settings in `config.py`.
  - Unit tests on `check_link`. The "fake records no lookup" clauses are asserted end-to-end in T8.
  - ~320 lines.
- [ ] T3 (AC-16, 17, 18; unit part of AC-19): Address refusal and pinning.
  - `address_check.py`: `is_public` with the IPv4-mapped and multicast rules; `public_address` with one lookup bounded by a timeout, `link_not_allowed`, `link_unreachable` on lookup failure, and `link_timeout`.
  - `pinned_transport.py`: unit tests that the inner transport receives the IP in the URL (IPv4 and bracketed IPv6), `Host` and `sni_hostname` set to the host name, and a refusal for any other host.
  - ~290 lines.
- [ ] T4 (AC-15, 19, 20, 21, 22, 23, 24, 32): The fetch, part 1: hops.
  - `page_fetch.py` with `LinkNetwork`, the hop loop, request headers, manual redirects (re-checked, at most 5, relative `Location`), non-2xx, and the lookup, connect, and TLS error mapping.
  - Tested on `fetch_page` with the fake network.
  - ~450 lines.
- [ ] T5 (AC-25, 26, 27, 28 fetch part, 29, 30, 31): The fetch, part 2: limits.
  - The 15 s deadline and the 5 s connect limit; content-type check before the body; `Content-Length` refusal with no chunk read; the streaming cap on decoded bytes (a missing or false `Content-Length`, a gzip bomb, exactly 2 MiB accepted).
  - ~360 lines.
- [ ] T6 (AC-33, 34, 36, 37, 38, 39, 40, 41; unit part of AC-42 and AC-52): From bytes to candidates.
  - `page_charset.py`, `page_text.py`, `candidate_lines.py`, with the cost-cap settings.
  - Includes the `<body>`-ends-`<head>` rule, the end-of-line trim (pending the user's answer on `U+3000`), and the final NFC.
  - ~640 lines.
- [ ] T7 (AC-46, 47, 49, 49b unit part, 50, 51): The selection call.
  - Refactor `claude.send_request` into the shared `send_completion` (spec 001 tests unchanged and passing).
  - `lyric_pick_prompt.py`, `lyric_pick.py`, `LyricPick` and `PickedLines` in `schemas.py`, and `PICK_EFFORT`/`PICK_MAX_TOKENS`.
  - ~480 lines.
- [ ] T8 (AC-12 body part, 35, 42, 43, 44, 45, 48, 49b, 52, 53, 54, 55, 56; end-to-end "no lookup" and "no Claude call" clauses of AC-9–14, 28, 37): The pipeline, the route, and logging.
  - `versions_from_link.py`; `VersionsFromLinkRequest`/`VersionsFromLinkResponse`; the route in `app.py` with `link_network`; generic fields in `request_log.py`.
  - Tests through `TestClient` with the fake network and the scripted fake Claude client. They check the reply keys, the over-limit reply for all three limits, readings errors passing through, error bodies with no link, host, IP, or text, the log fields with no secret, Host/405/64 KB, and the API key checked before any lookup.
  - ~680 lines.
- [ ] T9 (AC-6 reply and message part, AC-7 notice text): Page data.
  - `types.ts` (new codes, `LinkResult`); `api.ts` (`getFourVersionsFromLink` and the shared `postJson`, with the 200-reply checks); `errorMessages.ts` (9 messages, `overLimitNotice` with the AC-48 sentence and the AC-45 fallback).
  - Unit tests in `api.test.ts` and `errorMessages.test.ts`.
  - ~340 lines.
- [ ] T10 (AC-1, 2, 3, 4, 5, 6, 7, 8): The page.
  - `LinkForm.tsx`, controlled `PasteForm.tsx` with `statusText`, `pageState.ts`, `App.tsx` (state, the paste text lifted, focus per state), and the link-form layout in `styles.css` (no new color).
  - Tests in `LinkForm.test.tsx`, `pageState.test.ts`, `App.test.tsx`; the PasteForm tests are updated for the new props.
  - ~670 lines.
- [ ] README: the link flow, up to two Claude calls per link, and the folder map with the new modules and test helpers. ~30 lines.
- [ ] Manual check before the PR (not in the default suite): one real https lyrics page loads end to end. This confirms SNI and the certificate check through `PinnedTransport`.
- [ ] Final review of the whole diff, then the explainer's walkthrough, then the PR.

**Total: about 4,480 lines** (roughly 1,500 source and 3,000 tests). This is over the 800-line threshold in AGENTS.md, so it needs the user's permission before T1. The largest tasks (T6, T8, T10) are each under 700 lines.
