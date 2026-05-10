from dataclasses import dataclass


@dataclass(frozen=True)
class TextChunk:
    chunk_index: int
    content: str
    token_count: int


def estimate_token_count(text: str) -> int:
    return len(text.split())


def split_markdown(
    content: str,
    chunk_size_tokens: int = 900,
    chunk_overlap_tokens: int = 120,
) -> list[TextChunk]:
    if chunk_size_tokens <= 0:
        raise ValueError("chunk_size_tokens must be positive.")
    if chunk_overlap_tokens < 0:
        raise ValueError("chunk_overlap_tokens must be zero or positive.")
    if chunk_overlap_tokens >= chunk_size_tokens:
        raise ValueError("chunk_overlap_tokens must be smaller than chunk_size_tokens.")

    words = content.split()
    if not words:
        return []

    chunks: list[TextChunk] = []
    start = 0
    index = 0
    step = chunk_size_tokens - chunk_overlap_tokens

    while start < len(words):
        end = min(start + chunk_size_tokens, len(words))
        chunk_words = words[start:end]
        chunk_content = " ".join(chunk_words)
        chunks.append(
            TextChunk(
                chunk_index=index,
                content=chunk_content,
                token_count=len(chunk_words),
            )
        )
        if end == len(words):
            break
        start += step
        index += 1

    return chunks
