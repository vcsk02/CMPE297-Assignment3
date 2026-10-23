"""Capture reproducible commands and real output for the submission/video."""

import subprocess
import sys
from pathlib import Path


def main():
    commands = [
        [sys.executable, "-m", "pytest", "-q", "--junitxml=artifacts/test-results.xml"],
        [sys.executable, "-m", "agent_suite.cli", "demo"],
    ]
    log = []
    for argv in commands:
        result = subprocess.run(argv, capture_output=True, text=True, timeout=180, check=False)
        display = "python -m " + " ".join(argv[2:])
        log.extend(
            ["$ " + display, result.stdout, result.stderr, f"exit_code={result.returncode}\n"]
        )
        if result.returncode:
            Path("artifacts/execution-log.txt").write_text("\n".join(log))
            raise SystemExit(result.returncode)
    Path("artifacts/execution-log.txt").write_text("\n".join(log))
    print("Saved actual execution log: artifacts/execution-log.txt")


if __name__ == "__main__":
    main()
