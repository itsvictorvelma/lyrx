#!/usr/bin/env bash
# Runs every backend and frontend check; stops at the first failure.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export UV_LOCKED=1

step() {
  printf '\n==> %s\n' "$1"
}

cd "$repo_root/backend"
step "backend: ruff format"
uv run ruff format --check --no-cache
step "backend: ruff lint"
uv run ruff check --no-cache
step "backend: mypy"
uv run mypy
step "backend: pytest"
uv run pytest

cd "$repo_root/frontend"
step "frontend: prettier"
npm run format:check
step "frontend: eslint"
npm run lint
step "frontend: typecheck"
npm run typecheck
step "frontend: vitest"
npm test -- --run
step "frontend: build"
npm run build

step "all checks passed"
