import importlib.util
from pathlib import Path

import pytest

HOOK_PATH = Path(__file__).resolve().parents[2] / ".cursor" / "hooks" / "check_guardrail.py"
spec = importlib.util.spec_from_file_location("check_guardrail", HOOK_PATH)
assert spec is not None and spec.loader is not None
guardrail = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guardrail)

STATE = ".agent-state"


def runs_check(command: str) -> bool:
    return any(guardrail.is_check(part) for part in guardrail.segments(command))


def tampers(command: str) -> bool:
    return any(guardrail.is_tampering(part) for part in guardrail.segments(command))


@pytest.mark.parametrize(
    "command",
    [
        "scripts/check.sh",
        "bash scripts/check.sh",
        "CI=1 scripts/check.sh",
        "env CI=1 scripts/check.sh",
        "rtk scripts/check.sh",
        "cd backend && uv run pytest -q",
        "cd backend && rtk uv run pytest -q",
        "uv run --group authoring pytest",
        "python3 -m pytest tests",
        "pytest -x",
        "cd frontend && npm run build",
        "npm test",
        "npm run lint",
        "npx oxlint src",
        "npx tsc -b",
        "git status; pytest",
        "(cd frontend && npm test)",
    ],
)
def test_check_commands_are_recognized(command: str) -> None:
    assert runs_check(command)


@pytest.mark.parametrize(
    "command",
    [
        "ls -la",
        "rtk git status",
        'git commit -m "fix pytest import"',
        'gh pr comment 3 --body "Failing command: uv run pytest -q"',
        'gh pr comment 3 --body "Error output:\npytest -q\nnpm run build\nscripts/check.sh"',
        "cat > .agent-reports/ISSUE-3-FAILED.md <<'EOF'\n# ISSUE-3 FAILED\n- Failing command:\npytest -q\nnpm run build\nEOF",
        "cat <<EOF > /tmp/report.md\nscripts/check.sh\nEOF\necho done",
        "uv run python -c 'import pytest'",
        "npm install",
        "gh issue view #12 && gh pr list",
    ],
)
def test_text_that_mentions_checks_is_not_a_check(command: str) -> None:
    assert not runs_check(command)


def test_command_after_a_heredoc_is_still_checked() -> None:
    assert runs_check("cat > /tmp/notes.md <<'EOF'\nnotes\nEOF\nscripts/check.sh")


@pytest.mark.parametrize(
    "command",
    [
        "scripts/check.sh --reset",
        "bash scripts/check.sh --reset",
        "rtk scripts/check.sh --reset",
        f"rm -rf {STATE}",
        f"cd /repo && rm -f {STATE}/main.failures",
        f'rm -rf "{STATE}"',
        f"rtk rm -rf {STATE}",
        f"echo 0 > {STATE}/main.failures",
        f"git clean -fdx {STATE}",
        f"true | tee {STATE}/main.failures",
    ],
)
def test_tampering_is_recognized(command: str) -> None:
    assert tampers(command)


@pytest.mark.parametrize(
    "command",
    [
        f"ls {STATE}",
        f"cat {STATE}/main.failures",
        'gh pr create --body "Victor resets with scripts/check.sh --reset"',
        f"cat > /tmp/body.md <<'EOF'\nrm -rf {STATE}\nscripts/check.sh --reset\nEOF",
        f'echo "counts live in {STATE}"',
    ],
)
def test_reading_or_mentioning_state_is_not_tampering(command: str) -> None:
    assert not tampers(command)


def test_unbalanced_quotes_fall_back_to_conservative_split() -> None:
    assert runs_check("pytest -k 'unterminated")


def test_failure_count_reads_branch_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(guardrail, "ROOT", tmp_path)
    assert guardrail.failure_count("agent/3-thing") == 0

    state_dir = tmp_path / STATE
    state_dir.mkdir()
    (state_dir / "agent-3-thing.failures").write_text("2\n")
    assert guardrail.failure_count("agent/3-thing") == 2

    (state_dir / "agent-3-thing.failures").write_text("garbage")
    assert guardrail.failure_count("agent/3-thing") == 0
