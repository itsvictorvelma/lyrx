# 020 — Deployment: Docker and Caddy on a server

Status: draft

<!-- Agreed in principle on 2026-11-20. Stays draft until the user sets up the droplet and
domain and calls Lyrx ready to go live; review it again then. Builds on spec 014. -->

## Goal

Lyrx runs on a public server (a DigitalOcean droplet with Docker) behind HTTPS at the user's domain, with one command to start or update it. Running it locally does not change.

## In scope

- Settings from the environment, with today's local values as defaults.
- The server serves the built page, so one container answers both the page and the API.
- A two-stage `Dockerfile`, a `compose.yaml` with `caddy` and `lyrx`, a `Caddyfile`, `.env.example`.
- A health check route.
- A "Deploy" section in the README: DNS, `.env`, start, update, back up the database.

## Out of scope

- Buying or setting up the droplet and domain (the user's side).
- CI/CD (building or deploying from GitHub), Postgres, Kubernetes, monitoring.
- Any change to features or the page.

## Rules

Settings (read once in `config.py`; defaults keep local behaviour)
- `LYRX_HOST` (default `127.0.0.1`; `0.0.0.0` inside the container).
- `LYRX_ALLOWED_HOSTS` (default `127.0.0.1,localhost`): used by the Host check and the Origin check (014).
- `LYRX_DATABASE_PATH` (default `data/lyrx.db`).
- `LYRX_SECURE_COOKIES` (default off; on in `compose.yaml`).
- `LYRX_TRUSTED_PROXY`: the address whose `X-Forwarded-For` gives the client IP (uvicorn's `forwarded_allow_ips`). Unset means the direct peer address. In compose, only the Caddy container counts.
- A setting with a bad value stops the server at start with a short message naming the setting, never its value.

Serving the page
- When `frontend/dist` exists (or `LYRX_PAGE_DIR` points to a folder), `/` and every non-`/api` path return `index.html`, and `/assets/...` returns the built files. `/api/...` is unchanged. Without it, nothing changes (Vite runs the page locally).
- `GET /api/health` returns `{"status": "ok"}` after one cheap database read.

Containers
- `Dockerfile` stage 1: Node builds `frontend/dist`. Stage 2: slim Python with uv, the backend, and the built page; runs as a non-root user, with `HEALTHCHECK` on `/api/health`.
- `compose.yaml`: `lyrx` on the private network only (no published port), the database on a named volume `lyrx-data`. `caddy` publishes 80 and 443 and keeps its certificates on a volume. Both restart unless stopped.
- `Caddyfile`: the domain from `LYRX_DOMAIN`, `reverse_proxy lyrx:8000`. Caddy gets and renews the certificate.
- Keys come from `.env` on the server through `env_file`. They are never copied into the image. A `.dockerignore` keeps out `.env*`, `data/`, `*.db`, `*.mp3`, `node_modules/`, `.git/`.

## Security

- The app still refuses foreign `Host` and `Origin` values: the allowed list becomes the domain.
- `X-Forwarded-For` is trusted only from Caddy, so a guest cannot fake their IP to dodge the daily cap.
- Only Caddy is reachable from the internet. The image has no build tools, no keys, and no database.
- `AGENTS.md` security rules change from "bind to 127.0.0.1" to "bind and allowed hosts come from settings; local defaults stay 127.0.0.1".

## Acceptance checks

- AC-1: With no `LYRX_*` variables set, the settings equal today's values.
- AC-2: `LYRX_ALLOWED_HOSTS=lyrx.example` lets `Host: lyrx.example` through and refuses `127.0.0.1`.
- AC-3: A bad setting value stops the start with a message naming the setting, without the value.
- AC-4: With a built page folder, `/` and `/song/5` return `index.html`, an asset is served, and `/api/...` routes are unchanged. Without one, `/` is `404` as today.
- AC-5: `GET /api/health` returns ok.
- AC-6: With `LYRX_TRUSTED_PROXY` set, the guest IP comes from `X-Forwarded-For`. Without it, a forged header is ignored.
- AC-7 (manual): `docker compose up -d --build` on a machine with Docker starts both containers, the health check passes, and the page works through Caddy (`localhost` with Caddy's internal certificate).

## Plan

Added after approval.
