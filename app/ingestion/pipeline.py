import argparse
import logging
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import Chunk, Document
from app.db.session import SessionLocal
from app.ingestion.chunkers import split_markdown
from app.ingestion.cleaners import clean_markdown
from app.ingestion.hashing import calculate_document_hash, should_skip_document
from app.ingestion.loaders import RawMarkdownDocument, load_markdown_directory, load_markdown_file
from app.logging_config import configure_logging
from app.retrieval.embeddings import DeterministicEmbeddingProvider, EmbeddingProvider

logger = logging.getLogger(__name__)

REQUIRED_METADATA_FIELDS = {
    "title",
    "source",
    "category",
    "permission_level",
    "updated_at",
}


@dataclass(frozen=True)
class IngestionStats:
    documents_seen: int = 0
    documents_inserted: int = 0
    documents_updated: int = 0
    documents_skipped: int = 0
    chunks_inserted: int = 0


def ingest_path(
    path: Path,
    db: Session | None = None,
    embedding_provider: EmbeddingProvider | None = None,
) -> IngestionStats:
    settings = get_settings()
    provider = embedding_provider or DeterministicEmbeddingProvider(settings.embedding_dimensions)

    owns_session = db is None
    session = db or SessionLocal()
    try:
        documents = _load_documents(path)
        stats = IngestionStats()

        for raw_document in documents:
            stats = _merge_stats(stats, _ingest_document(raw_document, session, provider))

        if owns_session:
            session.commit()

        return stats
    except Exception:
        if owns_session:
            session.rollback()
        raise
    finally:
        if owns_session:
            session.close()


def _load_documents(path: Path) -> list[RawMarkdownDocument]:
    if path.is_file():
        return [load_markdown_file(path)]
    if path.is_dir():
        return load_markdown_directory(path)
    raise FileNotFoundError(f"Ingestion path does not exist: {path}")


def _ingest_document(
    raw_document: RawMarkdownDocument,
    db: Session,
    embedding_provider: EmbeddingProvider,
) -> IngestionStats:
    _validate_metadata(raw_document.metadata, raw_document.path)

    cleaned_content = clean_markdown(raw_document.content)
    content_hash = calculate_document_hash(cleaned_content, raw_document.metadata)
    existing_document = _find_existing_document(db, raw_document.metadata)

    if existing_document and should_skip_document(existing_document.content_hash, content_hash):
        logger.info("document_unchanged", extra={"path": str(raw_document.path)})
        return IngestionStats(documents_seen=1, documents_skipped=1)

    chunks = split_markdown(
        cleaned_content,
        chunk_size_tokens=get_settings().chunk_size_tokens,
        chunk_overlap_tokens=get_settings().chunk_overlap_tokens,
    )

    if existing_document:
        logger.info("updating_document", extra={"path": str(raw_document.path)})
        db.execute(delete(Chunk).where(Chunk.document_id == existing_document.id))
        document = existing_document
        document.content_hash = content_hash
        document.source = str(raw_document.metadata["source"])
        document.title = str(raw_document.metadata["title"])
        document.url = _optional_string(raw_document.metadata.get("url"))
        document.category = str(raw_document.metadata["category"])
        document.permission_level = str(raw_document.metadata["permission_level"])
        document.updated_at = _parse_datetime(raw_document.metadata["updated_at"])
        document_status = "updated"
    else:
        logger.info("inserting_document", extra={"path": str(raw_document.path)})
        document = Document(
            source=str(raw_document.metadata["source"]),
            title=str(raw_document.metadata["title"]),
            url=_optional_string(raw_document.metadata.get("url")),
            category=str(raw_document.metadata["category"]),
            permission_level=str(raw_document.metadata["permission_level"]),
            content_hash=content_hash,
            updated_at=_parse_datetime(raw_document.metadata["updated_at"]),
        )
        db.add(document)
        document_status = "inserted"

    db.flush()
    embeddings = embedding_provider.embed_texts([chunk.content for chunk in chunks])

    for chunk, embedding in zip(chunks, embeddings, strict=True):
        db.add(
            Chunk(
                document_id=document.id,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                embedding=embedding,
                metadata_json=_chunk_metadata(raw_document, chunk.chunk_index),
                token_count=chunk.token_count,
            )
        )

    if document_status == "inserted":
        return IngestionStats(documents_seen=1, documents_inserted=1, chunks_inserted=len(chunks))
    return IngestionStats(documents_seen=1, documents_updated=1, chunks_inserted=len(chunks))


def _find_existing_document(db: Session, metadata: dict[str, Any]) -> Document | None:
    statement = select(Document).where(
        Document.source == str(metadata["source"]),
        Document.title == str(metadata["title"]),
    )
    return db.scalar(statement)


def _validate_metadata(metadata: dict[str, Any], path: Path) -> None:
    missing_fields = sorted(REQUIRED_METADATA_FIELDS - set(metadata))
    if missing_fields:
        joined_fields = ", ".join(missing_fields)
        raise ValueError(f"{path} is missing required frontmatter fields: {joined_fields}")


def _chunk_metadata(raw_document: RawMarkdownDocument, chunk_index: int) -> dict[str, Any]:
    metadata = dict(raw_document.metadata)
    metadata["chunk_index"] = chunk_index
    metadata["source_path"] = str(raw_document.path)
    return metadata


def _parse_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time(), tzinfo=UTC)

    parsed_date = date.fromisoformat(str(value))
    return datetime.combine(parsed_date, datetime.min.time(), tzinfo=UTC)


def _optional_string(value: Any) -> str | None:
    if value is None or value == "":
        return None
    return str(value)


def _merge_stats(left: IngestionStats, right: IngestionStats) -> IngestionStats:
    return IngestionStats(
        documents_seen=left.documents_seen + right.documents_seen,
        documents_inserted=left.documents_inserted + right.documents_inserted,
        documents_updated=left.documents_updated + right.documents_updated,
        documents_skipped=left.documents_skipped + right.documents_skipped,
        chunks_inserted=left.chunks_inserted + right.chunks_inserted,
    )


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)

    parser = argparse.ArgumentParser(description="Ingest markdown documents into PGVector.")
    parser.add_argument("--path", required=True, type=Path, help="Markdown file or directory path.")
    args = parser.parse_args()

    stats = ingest_path(args.path)
    logger.info("ingestion_complete", extra=stats.__dict__)


if __name__ == "__main__":
    main()
