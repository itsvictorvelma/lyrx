#!/usr/bin/env bash
# Runs scripts/check.sh quietly: one line when everything passes, only the failing step's tail otherwise.
set -uo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
tail_lines="${1:-40}"
log="$(mktemp)"
trap 'rm -f "$log"' EXIT

if "$repo_root/scripts/check.sh" >"$log" 2>&1; then
  echo "all checks passed"
  exit 0
fi

failed_step="$(grep '^==> ' "$log" | tail -n 1)"
echo "FAILED at: ${failed_step#==> }"
# Only the output after the last step header, trimmed to its last lines.
awk '/^==> /{section=""; next} {section = section $0 "\n"} END{printf "%s", section}' "$log" \
  | tail -n "$tail_lines"
exit 1
