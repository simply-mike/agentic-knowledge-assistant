import re


def clean_markdown(content: str) -> str:
    normalized = content.replace("\r\n", "\n").replace("\r", "\n")
    normalized = re.sub(r"<!--.*?-->", "", normalized, flags=re.DOTALL)
    lines = [line.rstrip() for line in normalized.split("\n")]
    cleaned = "\n".join(lines).strip()
    return re.sub(r"\n{3,}", "\n\n", cleaned)
