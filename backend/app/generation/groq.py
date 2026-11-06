"""Send one chat completion through Swytchcode.

The Groq key is injected by Swytchcode. This module does not read it
and does not set Authorization.
"""

import json
import subprocess
from pathlib import Path
from typing import Protocol

from app.errors import DomainError

REPO_ROOT = Path(__file__).resolve().parents[3]


class GroqClient(Protocol):
    def complete(self, body: dict[str, object]) -> dict[str, object]: ...


class SwytchcodeGroq:
    def complete(self, body: dict[str, object]) -> dict[str, object]:
        payload = json.dumps({"tool": "groq.chat.completions.create", "args": {"body": body}})
        try:
            completed = subprocess.run(
                ["swytchcode", "exec", "--json"],
                input=payload,
                text=True,
                capture_output=True,
                cwd=REPO_ROOT,
                check=False,
            )
        except OSError as exc:
            raise DomainError("groq_unavailable", "The lyric request failed. Send again.") from exc
        return _response_json(completed.stdout)


def _response_json(stdout: str) -> dict[str, object]:
    start = stdout.find("{")
    if start < 0:
        raise DomainError("groq_unavailable", "The lyric request failed. Send again.")
    try:
        parsed = json.loads(stdout[start:])
    except json.JSONDecodeError as exc:
        raise DomainError("groq_unavailable", "The lyric request failed. Send again.") from exc
    if not isinstance(parsed, dict):
        raise DomainError("groq_unavailable", "The lyric request failed. Send again.")
    return parsed
