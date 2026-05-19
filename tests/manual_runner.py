import sys
from pathlib import Path
from runpy import run_path
from typing import Callable


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root))

    failures: list[tuple[str, str, str]] = []
    for path in sorted(Path(__file__).parent.glob("test_*.py")):
        namespace = run_path(str(path))
        for name, obj in namespace.items():
            if name.startswith("test_") and callable(obj):
                _run_test(path, name, obj, failures)

    if failures:
        for failure in failures:
            print(failure)
        raise SystemExit(1)

    print("all manual tests passed")


def _run_test(
    path: Path,
    name: str,
    obj: Callable[[], None],
    failures: list[tuple[str, str, str]],
) -> None:
    try:
        obj()
    except Exception as exc:
        failures.append((path.name, name, repr(exc)))


if __name__ == "__main__":
    main()
