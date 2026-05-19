from __future__ import annotations

import compileall
import os
import subprocess
import sys
from argparse import ArgumentParser, Namespace
from collections.abc import Callable
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PYTHON_LINE_LENGTH = 100


def main() -> None:
    args = parse_args()
    checks: list[tuple[str, Callable[[], None]]] = [
        ("compile Python files", compile_python),
        ("check Python line length", check_python_line_length),
        ("check git whitespace errors", check_git_whitespace),
    ]

    if args.with_tests:
        checks.insert(1, ("run manual unit tests", run_manual_tests))

    for name, check in checks:
        print(f"==> {name}")
        check()

    print("smoke checks passed")


def parse_args() -> Namespace:
    parser = ArgumentParser(description="Run lightweight repository smoke checks.")
    parser.add_argument(
        "--with-tests",
        action="store_true",
        help="Run tests/manual_runner.py. Requires project dependencies to be installed.",
    )
    return parser.parse_args()


def compile_python() -> None:
    paths = [REPO_ROOT / "app", REPO_ROOT / "tests", REPO_ROOT / "scripts"]
    success = all(compileall.compile_dir(str(path), quiet=1) for path in paths)
    if not success:
        raise SystemExit("Python compilation failed")


def run_manual_tests() -> None:
    run([sys.executable, "tests/manual_runner.py"])


def check_python_line_length() -> None:
    python_files = [
        *sorted((REPO_ROOT / "app").rglob("*.py")),
        *sorted((REPO_ROOT / "tests").rglob("*.py")),
        *sorted((REPO_ROOT / "scripts").rglob("*.py")),
    ]
    violations: list[str] = []

    for path in python_files:
        for line_number, line in enumerate(path.read_text().splitlines(), start=1):
            if len(line) > PYTHON_LINE_LENGTH:
                relative = path.relative_to(REPO_ROOT)
                violations.append(f"{relative}:{line_number}: {len(line)} chars")

    if violations:
        preview = "\n".join(violations[:20])
        raise SystemExit(f"Python line-length violations:\n{preview}")


def check_git_whitespace() -> None:
    run(["git", "diff", "--check"])


def run(command: list[str]) -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT)
    completed = subprocess.run(command, cwd=REPO_ROOT, check=False, env=env)
    if completed.returncode != 0:
        joined = " ".join(command)
        raise SystemExit(f"Command failed with exit code {completed.returncode}: {joined}")


if __name__ == "__main__":
    main()
