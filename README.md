<h1 align="center">subbed 字幕</h1>

<p align="center"><strong>Read any Japanese song, line by line.</strong></p>

<p align="center">
  Type a song's name. Subbed shows every line four ways: the original, hiragana, romaji, and English.<br>
  Then play along with the video while the sung line lights up.
</p>

<p align="center">
  <a href="docs/demo/subbed-demo.mp4"><img src="docs/demo/preview.gif" alt="Searching for a song: kana rain while it loads, then the lyrics in four columns, the sung line lighting up, and the romaji column hidden for self-testing" width="880"></a>
</p>

<p align="center"><sub>The song shown is invented. Click the preview for a longer walkthrough with sound (recorded on an earlier build).</sub></p>

---

## Features

- **One search box.** Type a title, an artist, or both. The best match opens right away, and "Not this one?" lists the others.
- **Four columns, one row per line.** Original, hiragana, romaji, and English, side by side. On a phone, tabs pick which reading sits next to the original.
- **Play along.** Paste a YouTube link or play an audio file from your computer (it is never uploaded). The sung line lights up and stays in view, using LRCLIB's line timings. Click a line to jump to it, nudge the sync earlier or later, slow down to 0.75× or 0.5×, and loop a single line.
- **Study tools.** Hide the hiragana, romaji, or English column and reveal one line at a time to test yourself. Focus mode shows only the lyrics and the player, with larger text.
- **Your songs.** Save a song with its video and sync. Sort and filter your library, and pick up where you left off from the home page.
- **Instant reopen.** Every translated song is cached, so opening it again is instant and costs no quota. Anyone can open songs already in Subbed.
- **Accounts without email.** A username and a password. Guests can search and play along; saving needs an account.
- **Keyboard first.** Press <kbd>?</kbd> on any page for the full list, and <kbd>/</kbd> to search.
- **Dark and light.** Follows your system setting, with a switch that remembers your choice.

## Screenshots

<sub>Every song and lyric line in these images is invented.</sub>

<p align="center">
  <img src="docs/screenshots/song-dark.png" alt="A song in four columns, the sung line highlighted, the video window and the player bar" width="880">
</p>

| Light theme | Your songs |
|---|---|
| ![The same song in the light theme](docs/screenshots/song-light.png) | ![The library: saved songs as tiles, sorted by recent](docs/screenshots/library.png) |

<p align="center">
  <img src="docs/screenshots/home.png" alt="Home: the example line, the large search box, Continue, and songs already in Subbed" width="680">
</p>


## How it works

```
 search box ──► LRCLIB search ──► ranked matches (Japanese first, duplicates removed)
                                        │
 open a song ──► cache hit? ── yes ──► instant reply
                     │ no
                     ▼
             LRCLIB lyrics + line timings
                     │
                     ▼
     Groq (Gemini as backup) ──► schema + script checks ──► cache ──► page
       chunks of 40 lines            hiragana: no kanji
       sent in parallel              romaji: no kana or kanji
```

- **Lyrics** come from [LRCLIB](https://lrclib.net). It is free and needs no key.
- **Readings and translation** come from free-tier AI models, with Groq first. When Groq is busy or out of quota, the same request goes to Gemini. The lyrics are sent as data, never as instructions.
- **Every reply is checked** against a strict schema before it is used. A line that fails is asked for again on its own. A line that still fails shows "Not available" and is retried the next time the song opens.
- **Limits keep the free tier healthy.** New (uncached) songs are capped each day: 20 per account, 20 per guest, and 300 for the whole site.

## Tech stack

| | |
|---|---|
| **Backend** | Python 3.12+, FastAPI, uvicorn, SQLite, managed with [uv](https://docs.astral.sh/uv/) |
| **Frontend** | React 19, TypeScript, Vite. No UI library: hand-written CSS with design tokens |
| **Quality** | ruff, mypy `--strict`, pytest · Prettier, ESLint (strict, type-checked), `tsc`, Vitest + Testing Library |
| **Hosting** | Docker Compose on one small server, with [Caddy](https://caddyserver.com) for HTTPS |
| **Services** | LRCLIB (lyrics), Groq and Gemini free tiers (readings and translation). No paid APIs. |

## Getting started

**You need:**
- [uv](https://docs.astral.sh/uv/) (Python 3.12 or later);
- Node.js with npm;
- a free API key from [Groq](https://console.groq.com/keys), [Google AI Studio](https://aistudio.google.com/apikey) (Gemini), or both. One is enough; with both, a busy translator hands over to the other.

```bash
# 1. Install
cd backend && uv sync && cd ..
cd frontend && npm install && cd ..

# 2. Add your keys (the file is gitignored)
cp .env.example .env        # then fill in GROQ_API_KEY and/or GEMINI_API_KEY

# 3. Run the server (terminal 1), on 127.0.0.1:8000
cd backend && uv run --env-file ../.env python -m subbed

# 4. Run the page (terminal 2)
cd frontend && npm run dev  # open http://127.0.0.1:5173
```

<details>
<summary>Free-tier limits and the translator order</summary>

Each request goes to Groq (`gpt-oss-120b`) first, then to Gemini Flash-Lite, then to a second Flash-Lite model. The order is `TRANSLATORS` in [`backend/src/subbed/config.py`](backend/src/subbed/config.py).

Rough free limits:
- Groq: about 1,000 requests a day and 8,000 tokens a minute per model, which is about one long song a minute.
- Gemini Flash-Lite: about 500 requests a day per model.

A song takes one call per 40 lines, so most songs need one or two calls. When every translator is at its limit, the page says so. Google may use what is sent on Gemini's free tier to improve its products.

</details>

<details>
<summary>Resetting a password</summary>

There is no email, so a forgotten password is reset by hand (for now). From `backend/`:

```bash
uv run python -m subbed.accounts.reset_password <username>
```

It asks for the new password twice and signs that person out everywhere.

</details>

## Deploy

Subbed runs on one small server (for example a DigitalOcean droplet) with Docker. Caddy sits in front, gets the HTTPS certificate, and is the only part reachable from the internet. The app container serves both the page and the API, and keeps the database on a Docker volume.

**1. The server.** Ubuntu 24.04 with at least 1 GB of memory. On 1 GB, add swap so the page build does not run out of memory:

```bash
fallocate -l 1G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab
curl -fsSL https://get.docker.com | sh                 # Docker and Compose
ufw allow OpenSSH && ufw allow 80 && ufw allow 443 && ufw enable
```

**2. The domain.** Add an `A` record for your domain pointing to the server's IPv4 address. Add no `AAAA` record: Docker's network is IPv4 only, so every IPv6 visitor would share one address for the daily caps. Wait until `dig +short your.domain` shows that IP. Caddy can only get the certificate after this.

**3. First start.** On the server:

```bash
git clone https://github.com/itsvictorvelma/subbed.git && cd subbed
cp .env.example .env && chmod 600 .env
nano .env                  # GROQ_API_KEY, GEMINI_API_KEY, SUBBED_DOMAIN=your.domain
scripts/deploy.sh          # builds, starts, waits until healthy
```

Open `https://your.domain`. The first account you create also gets the songs saved before accounts existed (there are none on a fresh server).

**4. Update** after a PR is merged into `main`:

```bash
cd subbed && scripts/deploy.sh
```

<details>
<summary>Logs, password reset, backup</summary>

```bash
docker compose ps                     # both containers, and whether subbed is healthy
docker compose logs -f subbed         # the app log (Caddy: logs -f caddy)
docker compose exec subbed python -m subbed.accounts.reset_password <username>
```

Back up the database (safe while it runs), then copy the file off the server:

```bash
docker compose exec subbed python -c "import sqlite3; sqlite3.connect('/data/subbed.db').backup(sqlite3.connect('/data/backup.db'))"
docker compose cp subbed:/data/backup.db ./subbed-backup-$(date +%F).db
# from your computer: scp root@your.domain:subbed/subbed-backup-*.db .
```

Each update leaves the old image behind; free the disk now and then with `docker image prune` (it never touches volumes). `docker compose down` stops everything and keeps the data. Never add `-v`: it deletes the database and the certificates.

</details>

<details>
<summary>Try the server setup on your own computer</summary>

With Docker running, add `SUBBED_DOMAIN=localhost` to your `.env`, then:

```bash
docker compose up -d --build    # open https://localhost and accept the local certificate
docker compose down
```

</details>

The server settings are environment variables, read once at start. Unset, they keep the local values:

| Setting | Local | In the container |
|---|---|---|
| `SUBBED_HOST` | `127.0.0.1` | `0.0.0.0` |
| `SUBBED_ALLOWED_HOSTS` | `127.0.0.1,localhost` | your domain |
| `SUBBED_DATABASE_PATH` | `data/subbed.db` | `/data/subbed.db` (volume) |
| `SUBBED_SECURE_COOKIES` | `false` | `true` |
| `SUBBED_TRUSTED_PROXY` | unset | Caddy's address |
| `SUBBED_PAGE_DIR` | unset (Vite serves the page) | the built page |

## Checks

```bash
scripts/check.sh         # everything, with full output
scripts/check-quiet.sh   # one line when it all passes
```

- Backend: ruff format, ruff lint, mypy `--strict`, and pytest.
- Frontend: Prettier, ESLint, `tsc`, Vitest, and the production build.
- No test calls Groq, Gemini, LRCLIB, or the network: a guard fails any test that tries.

## Project structure

```
subbed/
├── backend/                  Python server
│   ├── src/subbed/
│   │   ├── app.py              Builds the app: routes, error handlers, shared HTTP clients, the built page
│   │   ├── config.py           Every setting in one place
│   │   ├── schemas.py          What the page sends and receives
│   │   ├── errors.py           Error codes, their HTTP status, and their message
│   │   ├── song.py             Open a song: LRCLIB id → every line in four versions
│   │   ├── library.py          The shared song cache and each person's saved songs
│   │   ├── database.py         The SQLite file and its tables
│   │   ├── rate_limits.py      Daily caps on new songs, sign-ups, and failed sign-ins
│   │   ├── accounts/           Passwords (scrypt), users, session cookies, account routes
│   │   ├── lyrics/             LRCLIB client, search ranking, lines and timings, Japanese detection
│   │   ├── translation/        Translator chain, chunking, prompt, reply checks, Groq, Gemini
│   │   └── server/             Guards on every request: Host, Origin, body size, crash guard, log
│   └── tests/                The same folders, one test_<module>.py per module, plus fakes
├── frontend/                 The page
│   ├── index.html            Page shell: title, link preview, icons
│   ├── public/               Favicon, phone icon, link preview image
│   └── src/
│       ├── main.tsx            Mounts the app
│       ├── App.tsx             The shell: header, page switch, search and open flow
│       ├── api.ts              Every server call, reply checks, and error wording
│       ├── types.ts            Shared data shapes
│       ├── routing.ts          Addresses: /, /library, /song/{id}, /account
│       ├── browser.ts          Media queries and remembered settings
│       ├── icons.tsx           Every icon
│       ├── styles.css          Design tokens (dark and light), layout, motion, phone layout
│       ├── account/            Sign in, create, sign out, delete; who is signed in
│       ├── header/             The top bar and the theme switch
│       ├── search/             Search box, loading screen, kana rain
│       ├── shortcuts/          Keyboard shortcuts and their list
│       ├── home/               Home page and the animated example line
│       ├── library/            Your songs: tiles, sorting, filter, Undo
│       ├── song/               The song page: four-column table, study tools, following
│       └── player/             Player bar, YouTube and audio-file players, playback rules
├── specs/                    One short spec per feature, from idea to done
├── docs/                     README media (invented songs only)
├── scripts/                  check.sh, check-quiet.sh, and deploy.sh (run on the server)
├── Dockerfile                The image: builds the page, then runs the server
├── compose.yaml              The server setup: Caddy in front of the app
├── Caddyfile                 HTTPS and security headers
└── AGENTS.md                 The rules every contributor (human or agent) follows
```

## How this project is built

Every change starts as a short spec in [`specs/`](specs/), is built with a test for each acceptance check, and lands as a reviewed pull request. [AGENTS.md](AGENTS.md) holds the rules: security first, then correctness, then a working page, then polish.

## Credits

- Lyrics and line timings from [LRCLIB](https://lrclib.net), a free, community-run lyrics database.
- Readings and translations by [Groq](https://groq.com) and [Google Gemini](https://ai.google.dev).
- Built by Victor Velma.
