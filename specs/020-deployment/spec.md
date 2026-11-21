# 020 — Deployment: Docker and Caddy on a server

Status: approved

<!-- Agreed in principle on 2026-11-20, refreshed after 027 on 2026-11-20. Builds on spec 014.
The user sets up the droplet and domain; this spec makes the app ready so going live is a few
commands. -->

## Goal

Lyrx runs on a public server (a DigitalOcean droplet with Docker) behind HTTPS at the user's domain, started or updated with one command. Running it locally does not change.

## In scope

- Settings from the environment, with today's local values as defaults.
- The server serves the built page, so one container answers both the page and the API.
- A health check route.
- A two-stage `Dockerfile`, `.dockerignore`, `compose.yaml` (`caddy` and `lyrx`), `Caddyfile`, and new lines in `.env.example`.
- `scripts/deploy.sh`, run on the server: pull `main`, rebuild, restart, wait for healthy.
- A "Deploy" section in the README: droplet size and firewall, DNS, `.env`, first start, update, logs, password reset, and database backup.

## Out of scope

- Buying or setting up the droplet and domain (the user's side).
- CI/CD, Postgres, Kubernetes, monitoring, more than one server worker.
- A Content-Security-Policy (the YouTube embed needs care; a later spec if wanted).
- Any change to features or the page.

## Rules

Settings (read once in `config.py`; unset means today's local value)
- `LYRX_HOST`: the bind address. Default `127.0.0.1`; `0.0.0.0` in the container.
- `LYRX_ALLOWED_HOSTS`: comma-separated host names for the Host check and the Origin check. Default `127.0.0.1,localhost`.
- `LYRX_DATABASE_PATH`: default `data/lyrx.db` in the repo; `/data/lyrx.db` in the container.
- `LYRX_SECURE_COOKIES`: `true` or `false`, default `false`; `true` in the container.
- `LYRX_TRUSTED_PROXY`: the one IP address whose `X-Forwarded-For` names the client (uvicorn's `forwarded_allow_ips`). Unset means the direct peer address is used and the header is ignored.
- `LYRX_PAGE_DIR`: the built page folder (must hold `index.html`). Default unset; `/app/frontend/dist` in the container.
- A bad value (empty host list, a host with a scheme, port, or space, a non-boolean, an invalid IP) stops the server at start with a short message naming the setting, never its value.

Serving the page
- With a page folder: `/assets/...` returns built files; `/`, and any other non-`/api` path with no matching file, returns `index.html`. `/api/...` is unchanged, and an unknown `/api` path is still the JSON `not_found`. Files are only served from inside the page folder.
- Without one: nothing changes (Vite serves the page locally; `/` is `404`).
- `GET /api/health` returns `{"status": "ok"}` after one cheap database read, else `503` with the short error code.

Containers
- `Dockerfile` stage 1: Node builds `frontend/dist` from the lockfile. Stage 2: slim Python, uv installs the locked backend (no dev tools), the built page is copied in. Runs as a non-root user. `HEALTHCHECK` calls `/api/health` with Python's standard library, sending the first allowed host as `Host`.
- `compose.yaml`: `lyrx` has no published port; the database is on the named volume `lyrx-data`. `caddy` publishes 80 and 443 (TCP and UDP) and keeps certificates on the volume `caddy-data`. Both `restart: unless-stopped`. The private network has a fixed subnet, and Caddy a fixed address that `LYRX_TRUSTED_PROXY` points to.
- `Caddyfile`: the site is `{$LYRX_DOMAIN}`, `reverse_proxy lyrx:8000`. Caddy gets and renews the certificate, redirects HTTP to HTTPS, and adds `Strict-Transport-Security`, `X-Content-Type-Options: nosniff`, and `Referrer-Policy: strict-origin-when-cross-origin`.
- Keys and `LYRX_DOMAIN` come from `.env` on the server through `env_file`; the container's `LYRX_ALLOWED_HOSTS` is set from `LYRX_DOMAIN`. Nothing from `.env` is copied into the image. `.dockerignore` keeps out `.env*`, `data/`, `*.db*`, `*.mp3`, `node_modules/`, `dist/`, `.venv/`, `.git/`, and the local tool folders.

Deploy script (`scripts/deploy.sh`)
- Stops if `.env` is missing or `LYRX_DOMAIN` is empty.
- `git pull --ff-only`, then `docker compose up -d --build`, then waits up to 60 s for `lyrx` to report healthy and prints the result. Never deletes volumes.

## Security

- The app still refuses foreign `Host` and `Origin` values; on the server the allowed list is the domain.
- `X-Forwarded-For` is trusted only from Caddy's fixed address, so a guest cannot fake an IP to dodge the daily cap or the sign-up limit.
- Only Caddy is reachable from the internet; the app port is never published. The firewall allows only SSH, 80, and 443.
- The image holds no build tools, no keys, and no database. Keys never appear in logs or in `docker compose config` output that the README asks the user to run.
- Session cookies are `Secure` on the server.
- `AGENTS.md`: "bind to 127.0.0.1" becomes "bind address and allowed hosts come from settings; the local defaults stay 127.0.0.1 and localhost".

## Acceptance checks

- AC-1: With no `LYRX_*` variables set, the settings equal today's values.
- AC-2: `LYRX_ALLOWED_HOSTS=lyrx.example` lets `Host: lyrx.example` through and refuses `Host: 127.0.0.1`; a POST with `Origin: https://lyrx.example` passes the Origin check.
- AC-3: A bad value for each setting stops the start with a message naming the setting, without the value.
- AC-4: With a page folder, `/` and `/song/5` return `index.html`, an asset is served, `/api/...` routes are unchanged, an unknown `/api/x` is JSON `404`, and `/../` style paths never leave the folder. Without one, `/` is `404` as today.
- AC-5: `GET /api/health` returns ok; with a broken database it returns `503`.
- AC-6: With `LYRX_TRUSTED_PROXY` set, the guest IP comes from `X-Forwarded-For` sent by that address. Without it, or from another address, a forged header is ignored.
- AC-7: `LYRX_SECURE_COOKIES=true` makes the session cookie `Secure`.
- AC-8 (manual, local): `docker compose build` succeeds, the image has no `.env` or database, and with `LYRX_DOMAIN=localhost` the stack starts, reports healthy, and the page loads at `https://localhost` (Caddy's local certificate).
- AC-9 (manual, server): on the droplet, `scripts/deploy.sh` brings the site up at `https://<domain>` with a real certificate; sign up, search, open a song, save it.

## Plan

Backend
- `config.py`: one small reader per setting (`read_host`, `read_allowed_hosts`, `read_database_path`, `read_secure_cookies`, `read_trusted_proxy`, `read_page_dir`); an empty value counts as unset; relative paths are from the repo root. A bad value raises `SettingError(name)`, turned into `SystemExit("... setting LYRX_X is not valid")` while the module loads. Cache headers for the page live here too.
- `__main__.py`: passes `proxy_headers` and `forwarded_allow_ips` to uvicorn only when `TRUSTED_PROXY` is set (uvicorn otherwise trusts 127.0.0.1 by default; that is turned off).
- `app.py`: `page_response(page_dir, path)`: a file inside the folder, else `index.html`; `assets/` files cached for a year, `index.html` `no-cache` (in `app.py`, not its own file: it is under 40 lines). The 404 handler hands non-`/api` `GET`/`HEAD` misses to it when `PAGE_DIR` is set, so `/api` routing (404 and 405) is untouched. Adds `GET /api/health`.
- `errors.py`: new `server_unavailable` (503); the `host_not_allowed` message no longer names 127.0.0.1.
- `host_check.py`, `origin_check.py`, `rate_limits.py`: docstrings and the ponytail updated; logic unchanged (they already read `config`).
- Tests: `test_config.py` (AC-1, AC-3 via a subprocess import), `test_host_check.py`/`test_origin_check.py` (AC-2), `test_app.py` (AC-4, AC-5, AC-6 with uvicorn's own proxy middleware), `test_main.py` (AC-6), `test_sessions.py` (AC-7).

Deployment files (repo root unless noted)
- `Dockerfile`, `.dockerignore`, `compose.yaml`, `Caddyfile`, `.env.example` (adds `LYRX_DOMAIN`), `scripts/deploy.sh`.
- `README.md`: Deploy section and folder map; `AGENTS.md`: the bind rule and the app-wide file list.
