# The Subbed image (spec 020): Node builds the page, then slim Python serves the page and the API.

# --- Stage 1: build the page into frontend/dist ---------------------------
FROM node:24-slim AS page
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# --- Stage 2: the server ---------------------------------------------------
FROM python:3.14-slim
COPY --from=ghcr.io/astral-sh/uv:0.11.0 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PYTHONUNBUFFERED=1
WORKDIR /app/backend
# Dependencies first, so a code change does not reinstall them.
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --locked --no-dev --no-install-project
COPY backend/src ./src
RUN uv sync --locked --no-dev && rm /usr/local/bin/uv
COPY --from=page /app/frontend/dist /app/frontend/dist

# A non-root user; /data holds the database on a volume.
RUN useradd --system --uid 10001 --no-create-home subbed \
    && mkdir /data && chown subbed /data
USER subbed

ENV PATH=/app/backend/.venv/bin:$PATH \
    SUBBED_HOST=0.0.0.0 \
    SUBBED_DATABASE_PATH=/data/subbed.db \
    SUBBED_SECURE_COOKIES=true \
    SUBBED_PAGE_DIR=/app/frontend/dist
EXPOSE 8000

# The Host check refuses unknown names, so the probe sends the first allowed host.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 CMD ["python", "-c", "import os, urllib.request as r; host = os.environ.get('SUBBED_ALLOWED_HOSTS', 'localhost').split(',')[0].strip().lower(); r.urlopen(r.Request('http://127.0.0.1:8000/api/health', headers={'Host': host}), timeout=4)"]

CMD ["python", "-m", "subbed"]
