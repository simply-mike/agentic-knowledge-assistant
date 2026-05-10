from app.ingestion.chunkers import split_markdown
from app.ingestion.cleaners import clean_markdown
from app.ingestion.hashing import calculate_document_hash, should_skip_document
from app.ingestion.loaders import parse_frontmatter
from app.retrieval.embeddings import DeterministicEmbeddingProvider


def test_parse_frontmatter_extracts_metadata_and_content() -> None:
    metadata, content = parse_frontmatter(
        """---
title: Kafka Ingestion Runbook
source: synthetic_internal
category: data_platform
permission_level: developer
updated_at: 2026-05-01
synthetic: true
---
# Runbook

Configure ingestion jobs.
"""
    )

    assert metadata["title"] == "Kafka Ingestion Runbook"
    assert metadata["synthetic"] is True
    assert content.startswith("# Runbook")


def test_clean_markdown_normalizes_spacing_and_comments() -> None:
    cleaned = clean_markdown("Title  \n\n\n<!-- hidden -->\nBody\r\n")

    assert cleaned == "Title\n\nBody"


def test_split_markdown_uses_overlap() -> None:
    content = " ".join(f"token{i}" for i in range(10))

    chunks = split_markdown(content, chunk_size_tokens=6, chunk_overlap_tokens=2)

    assert len(chunks) == 2
    assert chunks[0].content.split()[-2:] == chunks[1].content.split()[:2]
    assert chunks[0].token_count == 6


def test_document_hash_supports_skip_unchanged() -> None:
    metadata = {
        "title": "Doc",
        "source": "synthetic_internal",
        "category": "data_platform",
        "permission_level": "developer",
        "updated_at": "2026-05-01",
    }
    content_hash = calculate_document_hash("same content", metadata)

    assert should_skip_document(content_hash, content_hash)
    assert not should_skip_document(content_hash, calculate_document_hash("new content", metadata))


def test_deterministic_embeddings_are_stable_and_sized() -> None:
    provider = DeterministicEmbeddingProvider(dimensions=8)

    first = provider.embed_texts(["Kafka ingestion latency"])[0]
    second = provider.embed_texts(["Kafka ingestion latency"])[0]

    assert first == second
    assert len(first) == 8
