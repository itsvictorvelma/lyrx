import subprocess
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
AUTHORING_ONLY_MODULES = {"authoring", "langchain", "langchain_core", "langgraph"}


def test_api_does_not_load_authoring_libraries() -> None:
    probe = (
        "import sys, app.main\n"
        f"blocked = {sorted(AUTHORING_ONLY_MODULES)!r}\n"
        "print(','.join(sorted({m.split('.')[0] for m in sys.modules} & set(blocked))))"
    )

    result = subprocess.run(
        [sys.executable, "-c", probe],
        cwd=BACKEND_DIR,
        capture_output=True,
        text=True,
        check=True,
    )

    assert result.stdout.strip() == ""
