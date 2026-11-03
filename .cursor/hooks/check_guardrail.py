#!/usr/bin/env python3
"""beforeShellExecution hook: enforce the two-failed-check-runs limit.

scripts/check.sh counts failed runs per branch in .agent-state/. Once the
limit is reached, agents may not run checks again on that branch, and they
may never reset or delete the counter themselves.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

MAX_FAILURES = 2
ROOT = Path(__file__).resolve().parents[2]
CHECK_COMMAND = re.compile(r"check\.sh|pytest|npm (run )?(build|test)|vitest|oxlint|tsc\b")
TAMPER_COMMAND = re.compile(r"\.agent-state|check\.sh\s+--reset")


def respond(permission: str, agent_message: str = "", user_message: str = "") -> None:
    payload: dict[str, str] = {"permission": permission}
    if agent_message:
        payload["agent_message"] = agent_message
    if user_message:
        payload["user_message"] = user_message
    print(json.dumps(payload))
    sys.exit(0)


def current_branch() -> str:
    result = subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() or "unknown"


def failure_count(branch: str) -> int:
    state_file = ROOT / ".agent-state" / f"{branch.replace('/', '-')}.failures"
    try:
        return int(state_file.read_text().strip())
    except (FileNotFoundError, ValueError):
        return 0


def main() -> None:
    try:
        command = json.load(sys.stdin).get("command", "")
    except json.JSONDecodeError:
        respond("allow")

    if TAMPER_COMMAND.search(command):
        respond(
            "deny",
            agent_message=(
                "Only a human may reset the check guardrail. Stop and write the "
                "failure report described in .cursor/rules/execution-guardrail.mdc."
            ),
            user_message="Blocked an agent from resetting the check guardrail.",
        )

    if not CHECK_COMMAND.search(command):
        respond("allow")

    branch = current_branch()
    failures = failure_count(branch)
    if failures >= MAX_FAILURES:
        respond(
            "deny",
            agent_message=(
                f"GUARDRAIL: checks already failed {failures} times on branch {branch}. "
                "Do not try another fix. Write the failure report described in "
                ".cursor/rules/execution-guardrail.mdc, then stop and wait for a human."
            ),
            user_message=(
                f"Agent hit the {MAX_FAILURES}-failure check limit on {branch}. "
                "Review it, then run scripts/check.sh --reset to unblock."
            ),
        )

    respond("allow")


if __name__ == "__main__":
    main()
