from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any
from uuid import UUID


@dataclass(frozen=True)
class RetrievedChunk:
    chunk_id: UUID
    document_id: UUID
    title: str
    source: str
    url: str | None
    category: str
    permission_level: str
    content: str
    metadata: dict[str, Any]
    token_count: int
    distance: float


def normalize_retrieval_filters(
    filters: Mapping[str, Any] | None,
    allowed_permissions: Sequence[str],
) -> dict[str, list[str]]:
    normalized: dict[str, list[str]] = {
        "permission_level": list(allowed_permissions),
    }
    if not filters:
        return normalized

    for key in ("category", "source"):
        values = _string_list(filters.get(key))
        if values:
            normalized[key] = values

    requested_permissions = _string_list(filters.get("permission_level"))
    if requested_permissions:
        allowed_set = set(allowed_permissions)
        normalized["permission_level"] = [
            permission for permission in requested_permissions if permission in allowed_set
        ]

    return normalized


class PGVectorStore:
    def __init__(self, db: Any) -> None:
        self.db = db

    def search_by_vector(
        self,
        query_embedding: list[float],
        allowed_permissions: Sequence[str],
        top_k: int = 5,
        filters: Mapping[str, Any] | None = None,
    ) -> list[RetrievedChunk]:
        if top_k <= 0:
            raise ValueError("top_k must be positive.")

        normalized_filters = normalize_retrieval_filters(filters, allowed_permissions)
        if not normalized_filters["permission_level"]:
            return []

        statement = self._build_search_statement(query_embedding, normalized_filters, top_k)
        rows = self.db.execute(statement).all()
        return [_row_to_retrieved_chunk(row) for row in rows]

    def _build_search_statement(
        self,
        query_embedding: list[float],
        filters: Mapping[str, list[str]],
        top_k: int,
    ) -> Any:
        from sqlalchemy import select

        from app.db.models import Chunk, Document

        distance = Chunk.embedding.cosine_distance(query_embedding).label("distance")
        statement = (
            select(
                Chunk.id.label("chunk_id"),
                Chunk.document_id,
                Chunk.content,
                Chunk.metadata_json,
                Chunk.token_count,
                Document.title,
                Document.source,
                Document.url,
                Document.category,
                Document.permission_level,
                distance,
            )
            .join(Document, Chunk.document_id == Document.id)
            .where(Document.permission_level.in_(filters["permission_level"]))
            .order_by(distance)
            .limit(top_k)
        )

        if categories := filters.get("category"):
            statement = statement.where(Document.category.in_(categories))
        if sources := filters.get("source"):
            statement = statement.where(Document.source.in_(sources))

        return statement


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        return [str(item) for item in value]
    return [str(value)]


def _row_to_retrieved_chunk(row: Any) -> RetrievedChunk:
    mapping = row._mapping if hasattr(row, "_mapping") else row
    return RetrievedChunk(
        chunk_id=mapping["chunk_id"],
        document_id=mapping["document_id"],
        title=mapping["title"],
        source=mapping["source"],
        url=mapping["url"],
        category=mapping["category"],
        permission_level=mapping["permission_level"],
        content=mapping["content"],
        metadata=dict(mapping["metadata_json"] or {}),
        token_count=mapping["token_count"],
        distance=float(mapping["distance"]),
    )
