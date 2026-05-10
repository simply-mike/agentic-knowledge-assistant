import hashlib
import json
from typing import Any


def calculate_document_hash(content: str, metadata: dict[str, Any]) -> str:
    stable_payload = {
        "content": content,
        "metadata": {
            key: metadata[key]
            for key in sorted(metadata)
            if key not in {"updated_at"}
        },
    }
    encoded = json.dumps(stable_payload, sort_keys=True, ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def should_skip_document(existing_hash: str | None, new_hash: str) -> bool:
    return existing_hash == new_hash
