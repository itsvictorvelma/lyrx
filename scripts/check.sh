#!/usr/bin/env bash
# Runs every check CI runs: backend tests, then frontend tests, lint, and build.
#
# Failed runs are counted per git branch in .agent-state/. After MAX_FAILURES,
# .cursor/hooks/check_guardrail.py blocks agents from running checks again
# until a human runs: scripts/check.sh --reset
# The count is skipped only on GitHub Actions. Agent terminals also set CI,
# so keying off CI would let agent failures slip past the limit.
set -uo pipefail

MAX_FAILURES=2
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
branch="$(git -C "$root" rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)"
state_file="$root/.agent-state/${branch//\//-}.failures"

if [[ "${1:-}" == "--reset" ]]; then
  rm -f "$state_file"
  echo "Guardrail counter reset for branch $branch."
  exit 0
fi

run_checks() {
  (cd "$root/backend" && uv run pytest -q) &&
    (cd "$root/frontend" && npm test && npm run lint && npm run build)
}

if run_checks; then
  rm -f "$state_file"
  echo "All checks passed."
  exit 0
fi

if [[ -n "${GITHUB_ACTIONS:-}" ]]; then
  exit 1
fi

mkdir -p "$(dirname "$state_file")"
failures=$(( $(cat "$state_file" 2>/dev/null || echo 0) + 1 ))
echo "$failures" > "$state_file"

if (( failures >= MAX_FAILURES )); then
  echo "GUARDRAIL: $failures failed check runs on branch $branch."
  echo "Stop. Write the failure report described in .cursor/rules/execution-guardrail.mdc and wait for a human."
else
  echo "Checks failed ($failures of $MAX_FAILURES allowed failed runs on branch $branch)."
fi
exit 1
