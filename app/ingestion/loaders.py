from dataclasses import dataclass
from pathlib import Path
from typing import Any


class FrontmatterError(ValueError):
    """Raised when a markdown file has missing or invalid frontmatter."""


@dataclass(frozen=True)
class RawMarkdownDocument:
    path: Path
    metadata: dict[str, Any]
    content: str


def load_markdown_file(path: Path) -> RawMarkdownDocument:
    text = path.read_text(encoding="utf-8")
    metadata, content = parse_frontmatter(text)
    return RawMarkdownDocument(path=path, metadata=metadata, content=content)


def load_markdown_directory(path: Path) -> list[RawMarkdownDocument]:
    files = sorted(file_path for file_path in path.rglob("*.md") if file_path.is_file())
    return [load_markdown_file(file_path) for file_path in files]


def parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    if not normalized.startswith("---\n"):
        raise FrontmatterError("Markdown document must start with YAML frontmatter.")

    closing_marker = normalized.find("\n---\n", 4)
    if closing_marker == -1:
        raise FrontmatterError("Markdown frontmatter must end with a closing --- marker.")

    raw_frontmatter = normalized[4:closing_marker]
    content = normalized[closing_marker + len("\n---\n") :]
    metadata = _parse_simple_yaml(raw_frontmatter)
    return metadata, content


def _parse_simple_yaml(raw_frontmatter: str) -> dict[str, Any]:
    metadata: dict[str, Any] = {}
    for line_number, raw_line in enumerate(raw_frontmatter.splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        if ":" not in line:
            raise FrontmatterError(f"Invalid frontmatter line {line_number}: expected key: value.")

        key, value = line.split(":", 1)
        key = key.strip()
        if not key:
            raise FrontmatterError(f"Invalid frontmatter line {line_number}: empty key.")

        metadata[key] = _parse_scalar(value.strip())

    return metadata


def _parse_scalar(value: str) -> Any:
    if value == "":
        return ""

    lowered = value.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False

    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]

    return value
