# 014 — Personal accounts

Status: approved

## Goal

Anyone with the link can search and read songs without an account, so an employer sees the finished app in one click. Friends create an account to keep their own saved songs and video syncs. A daily cap keeps strangers from using up the free Groq and Gemini quota. Hosting itself (Docker, HTTPS, settings from the environment) is spec 020.

## In scope

- Create an account (username + password), sign in, sign out, delete my account.
- Saved songs and each song's video and sync nudge become per person. The song cache (lyrics and versions) stays shared by everyone.
- Guests can search and open songs. Saving needs an account.
- A daily cap on new translations: per account, per guest IP, and for the whole site.
- Limits on sign-ups and failed sign-ins.
- An `Origin` check on requests that change data.
- A small command to reset a friend's password.
- Songs saved before this spec go to the first account created.

## Out of scope

- Email, password reset by email, sign-in with Google or another provider.
- Admin pages, roles, invite codes.
- Docker, Caddy, environment settings, a trusted proxy, serving the built page: spec 020.
- Hidden columns and the theme stay in each browser, as today.
- Featured or example songs on the guest home page (an idea for later).

## Rules

Accounts
- Username: 3–30 characters, `a-z 0-9 _ -`, stored lowercase, unique. Password: 8–128 characters.
- Passwords are hashed with `hashlib.scrypt` (standard library) and a random 16-byte salt per user. No new dependency.
- Sign-in failures never say whether the username exists: one code, `sign_in_failed`. An unknown username still runs one scrypt, so the timing matches.
- Deleting an account asks for the password again and removes the user, their sessions, and their saved songs. Cached songs stay.

Sessions
- Signing in or creating an account sets a cookie `lyrx_session`: a random 32-byte token, `HttpOnly`, `SameSite=Lax`, `Path=/`, and `Secure` when `config.SECURE_COOKIES` is true (off for now, a setting in 020). It lasts 30 days.
- The database keeps only the token's SHA-256 hash, the user, and the expiry time. Signing out deletes that row. Expired rows are ignored and removed when someone signs in.

Per-person data
- The cache table holds the song and its lines only. A new table holds `(user_id, song_id, video_id, offset_ms, saved_at, last_opened_at)`.
- `GET /api/songs`, save, unsave, and playback need a signed-in person, otherwise `401 sign_in_required`. Each one sees and changes only its own rows.
- Opening a song works for everyone. For a signed-in person it also returns their saved state and video, and updates their last-opened time. The `saved` mark in search results is per person (always false for a guest).

Daily cap on new translations
- Only a song that is not cached counts (a call to LRCLIB and the translators). It counts when it starts, so failures count too. Opening a cached song is always free, and so is filling in a cached song's missing lines.
- Caps per UTC day: 20 per account, 20 per guest IP, 300 for the whole site, in `config.py`.
- Over a cap: `429 daily_limit`, "Daily limit reached. Songs already in Lyrx still open." Nothing is fetched.
- Counts are kept in the database, so a restart does not reset them. The guest IP is the direct peer address (020 adds the trusted proxy).

Abuse limits
- Sign-ups: 5 per IP per UTC day. Failed sign-ins: 10 per username per hour, then `429 too_many_attempts` (also for the right password, until the hour passes).

Page
- Header: "Sign in" for guests. A signed-in person sees their username, which links to `/account`.
- `/account` for a guest: username, password, and a switch between "Sign in" and "Create account". Errors show as text.
- `/account` signed in: "Signed in as …", "Sign out", and "Delete account" (asks for the password).
- Guest home: the search box and a short line, "Sign in to save songs." The Save button takes a guest to `/account`, then back to the song.
- Reuses the colour tokens and patterns in `styles.css`. No new look without approval.

## Security

- Untrusted input: username, password, cookie, `Origin`. Request schemas check size and pattern first. The password is never logged, stored in plain text, or returned.
- CSRF: `SameSite=Lax` cookie, and every `POST`/`PUT`/`DELETE` must carry an `Origin` whose host is in `ALLOWED_HOST_NAMES`, otherwise `403 bad_origin`.
- Logs: a user id and event words (`signed_up`, `sign_in_failed`, `daily_limit`). Never passwords, tokens, or cookie values.
- What is sent to outside services: unchanged. No account data leaves the server.
- Error replies stay short codes. The database file stays gitignored.

## Acceptance checks

- AC-1: Creating an account sets the session cookie, and `GET /api/account` returns the username. A taken username (any letter case) gives `409 username_taken`. A bad username or password gives `400 invalid_request`.
- AC-2: The stored password is a salted scrypt hash, and the right password signs in. A wrong password and an unknown username give the same `401 sign_in_failed`.
- AC-3: The cookie is `HttpOnly` and `SameSite=Lax`, and `Secure` only when `SECURE_COOKIES` is true. The database holds the token's hash, not the token.
- AC-4: Signing out removes the session, and the old cookie is no longer accepted. An expired session is not accepted.
- AC-5: A guest gets `401 sign_in_required` on the saved-songs routes. A guest can search and open a song.
- AC-6: Two accounts save different songs and videos, and each sees only their own, in the library, on open, and in search. Unsaving one does not affect the other or remove the cached song.
- AC-7: Opening a cached song does not count toward any cap. The 21st new song of the day for one account gives `429 daily_limit`, and LRCLIB is not called.
- AC-8: Guests are capped per IP, separately from accounts.
- AC-9: The site-wide cap stops new songs for everyone, while cached songs still open.
- AC-10: The 6th sign-up from one IP in a day and the 11th failed sign-in for one username in an hour give `429 too_many_attempts`.
- AC-11: A `POST` with a foreign or missing `Origin` gives `403 bad_origin`. `GET` is not checked.
- AC-12: Deleting an account with the right password removes its sessions and saved songs, and the cached songs stay. A wrong password changes nothing.
- AC-13: An older database upgrades: its songs stay cached, and its saved songs (with videos) belong to the first account created.
- AC-14: The reset command sets a new password and signs that person out everywhere.
- AC-15 (page): A guest sees "Sign in", and Save takes them to `/account`. After signing in they return to the song, the header shows the username, and the library shows only their songs. Sign-in errors show as text.
- AC-16 (page): Sign out and Delete account on `/account` work, and the page returns to the guest home.

## Plan

Backend, new area `backend/src/lyrx/accounts/`:
- `passwords.py`: `hash_password`, `password_matches` (scrypt, `hmac.compare_digest`).
- `users.py`: create (claims unowned saved songs when it is the first user), find by name, delete.
- `sessions.py`: create, find the user for a token, delete, the cookie settings; `signed_in_user(request)` and `require_user(request)` for routes.
- `routes.py`: `GET /api/account`, `POST /api/account/sign-up`, `/sign-in`, `/sign-out`, `DELETE /api/account`. `create_app` registers them like the other routes.
- `reset_password.py`: `uv run python -m lyrx.accounts.reset_password <username>`, password asked with `getpass`.

Backend, other files:
- New `database.py`: `connect()` and every `CREATE TABLE` (moved out of `library.py`), plus the one-time upgrade: old `saved_songs` → `songs` (cache) + `library_entries` with `user_id NULL` for the saved rows.
- `library.py`: queries take a `user_id`. Cache queries (`find_song`, `cache_song`, `replace_lines`) stay shared.
- New `rate_limits.py`: one `request_counts(kind, who, window_start, count)` table, `check_and_count(kind, who, limit, window)`. Used for new songs (account/IP/site), sign-ups, and failed sign-ins.
- New `server/origin_check.py`: ASGI layer, after the Host check.
- `app.py`: routes pass the signed-in user; `get_song_versions` checks the caps before `open_song`.
- `schemas.py`: account request and reply bodies. `errors.py`: `sign_in_required`, `sign_in_failed`, `username_taken`, `daily_limit`, `too_many_attempts`, `bad_origin`.
- `config.py`: username and password rules, scrypt cost, session days, cookie name, `SECURE_COOKIES = False`, the caps.
- Tests: `tests/accounts/test_*.py` per module, `test_database.py` (AC-13), `test_rate_limits.py`, `server/test_origin_check.py`; existing library and app tests updated to sign in. A test fixture signs a user in.

Frontend:
- New `frontend/src/account/`: `accountApi.ts`, `useAccount.ts` (who is signed in, shared through context), `AccountPage.tsx` (+ test).
- `routing.ts`: `/account` route, with a return path for Save.
- `header/Header.tsx`: Sign in / username link. `library/LibraryPage.tsx`: guest state. `lyrics/SaveButton.tsx`: guest goes to `/account`.
- `lyrics/fakeSongPage.tsx`: fake server learns the account routes.

Docs: README folder map, `AGENTS.md` roadmap, `specs/README.md`.
