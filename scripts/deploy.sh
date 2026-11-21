#!/usr/bin/env bash
# Run on the server: pulls main, rebuilds and restarts Lyrx, and waits until it reports healthy.
set -euo pipefail

# Everything is in main(), which bash reads whole before running: `git pull` may rewrite this
# file mid-run.
main() {
  local repo_root domain container status
  repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
  cd "$repo_root"

  if [[ ! -f .env ]]; then
    echo "No .env here. Copy .env.example to .env and fill it in (see the README's Deploy section)."
    exit 1
  fi
  domain="$(sed -n 's/^LYRX_DOMAIN=//p' .env | tail -n 1 | tr -d '[:space:]"')"
  if [[ -z "$domain" ]]; then
    echo "LYRX_DOMAIN is empty in .env. Set it to your domain, without https://."
    exit 1
  fi

  git pull --ff-only
  # Caddy waits for the app to be healthy, so a failed start shows here.
  docker compose up -d --build || {
    echo "Lyrx did not start. See: docker compose logs lyrx"
    exit 1
  }

  container="$(docker compose ps -q lyrx)"
  for _ in $(seq 1 30); do
    status="$(docker inspect -f '{{.State.Health.Status}}' "$container")"
    if [[ "$status" == "healthy" ]]; then
      echo "Lyrx is up: https://$domain"
      exit 0
    fi
    sleep 2
  done
  echo "Lyrx did not report healthy within 60 seconds. See: docker compose logs lyrx"
  exit 1
}

main "$@"
exit
