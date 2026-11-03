#!/usr/bin/env python3
"""beforeShellExecution hook: enforce the two-failed-check-runs limit.

scripts/check.sh counts failed runs per branch in .agent-state/. Once the
limit is reached, agents may not run checks again on that branch, and they
may never reset or delete the counter themselves.
"""

import json
import re
import shlex
import subprocess
import sys
from pathlib import Path

MAX_FAILURES = 2
ROOT = Path(__file__).resolve().parents[2]
STATE_DIR_NAME = ".agent-state"

SEPARATOR_CHARS = set(";&|()\n")
WRAPPERS = {"rtk", "sudo", "env", "time", "command", "exec", "nohup", "nice"}
SHELLS = {"bash", "sh", "zsh"}
CHECK_TOOLS = {"pytest", "oxlint", "vitest", "tsc"}
NPM_CHECK_SCRIPTS = {"build", "test", "lint"}
MUTATING_COMMANDS = {"rm", "mv", "cp", "truncate", "tee", "touch"}
MUTATING_GIT_SUBCOMMANDS = {"rm", "clean", "checkout", "restore"}
HEREDOC_START = re.compile(r"(?<!<)<<(?!<)-?\s*(['\"]?)([A-Za-z_]\w*)\1")
ASSIGNMENT = re.compile(r"^\w+=")


def strip_heredoc_bodies(command: str) -> str:
    kept: list[str] = []
    pending: list[str] = []
    for line in command.split("\n"):
        if pending:
            if line.strip() == pending[0]:
                pending.pop(0)
            continue
        kept.append(line)
        pending.extend(match.group(2) for match in HEREDOC_START.finditer(line))
    return "\n".join(kept)


def tokenize(command: str) -> list[str]:
    """Split like a shell would, so quoted text and heredoc bodies are data, not commands."""
    text = strip_heredoc_bodies(command)
    try:
        lexer = shlex.shlex(text, posix=True, punctuation_chars=";&|()<>\n")
        lexer.whitespace = " \t\r"
        lexer.whitespace_split = True
        lexer.commenters = ""
        return list(lexer)
    except ValueError:
        return re.findall(r"[;&|()\n]+|[^\s;&|()]+", text)


def is_separator(token: str) -> bool:
    return bool(token) and set(token) <= SEPARATOR_CHARS


def segments(command: str) -> list[list[str]]:
    result: list[list[str]] = [[]]
    for token in tokenize(command):
        if is_separator(token):
            result.append([])
        else:
            result[-1].append(token)

    cleaned = []
    for words in result:
        start = 0
        while start < len(words) and (words[start] in WRAPPERS or ASSIGNMENT.match(words[start])):
            start += 1
        if words[start:]:
            cleaned.append(words[start:])
    return cleaned


def program(words: list[str]) -> list[str]:
    if words[0] in SHELLS and len(words) > 1:
        return words[1:]
    return words


def is_check_script(word: str) -> bool:
    return Path(word).name == "check.sh"


def is_check(words: list[str]) -> bool:
    words = program(words)
    head, args = words[0], words[1:]
    if is_check_script(head) or head in CHECK_TOOLS:
        return True
    if head in {"python", "python3"} and args[:2] == ["-m", "pytest"]:
        return True
    if head == "uv" and args[:1] == ["run"] and "pytest" in args[1:]:
        return True
    if head == "npx" and args[:1] and args[0] in CHECK_TOOLS:
        return True
    if head == "npm":
        script = args[1:2] if args[:1] == ["run"] else args[:1]
        return bool(script) and script[0] in NPM_CHECK_SCRIPTS
    return False


def is_tampering(words: list[str]) -> bool:
    words = program(words)
    head, args = words[0], words[1:]
    if is_check_script(head) and "--reset" in args:
        return True
    if not any(STATE_DIR_NAME in word for word in words):
        return False
    if head in MUTATING_COMMANDS:
        return True
    if head == "git" and args[:1] and args[0] in MUTATING_GIT_SUBCOMMANDS:
        return True
    return any(
        ">" in word and index + 1 < len(words) and STATE_DIR_NAME in words[index + 1]
        for index, word in enumerate(words)
    )


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
    state_file = ROOT / STATE_DIR_NAME / f"{branch.replace('/', '-')}.failures"
    try:
        return int(state_file.read_text().strip())
    except (FileNotFoundError, ValueError):
        return 0


def main() -> None:
    try:
        command = json.load(sys.stdin).get("command", "")
    except json.JSONDecodeError:
        respond("allow")

    parts = segments(command)

    if any(is_tampering(part) for part in parts):
        respond(
            "deny",
            agent_message=(
                "Only a human may reset the check guardrail. Stop and write the "
                "failure report described in .cursor/rules/execution-guardrail.mdc."
            ),
            user_message="Blocked an agent from resetting the check guardrail.",
        )

    if not any(is_check(part) for part in parts):
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
