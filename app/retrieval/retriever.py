from collections.abc import Mapping
from typing import Any, Protocol

from app.permissions.policies import allowed_permission_levels
from app.retrieval.embeddings import EmbeddingProvider
from app.retrieval.vector_store import RetrievedChunk


class VectorSearchStore(Protocol):
    def search_by_vector(
        self,
        query_embedding: list[float],
        allowed_permissions: list[str],
        top_k: int = 5,
        filters: Mapping[str, Any] | None = None,
    ) -> list[RetrievedChunk]:
        ...


class KnowledgeRetriever:
    def __init__(
        self,
        vector_store: VectorSearchStore,
        embedding_provider: EmbeddingProvider,
    ) -> None:
        self.vector_store = vector_store
        self.embedding_provider = embedding_provider

    def search(
        self,
        query: str,
        role: str,
        top_k: int = 5,
        filters: Mapping[str, Any] | None = None,
    ) -> list[RetrievedChunk]:
        allowed_permissions = allowed_permission_levels(role)
        query_embedding = self.embedding_provider.embed_query(query)
        return self.vector_store.search_by_vector(
            query_embedding=query_embedding,
            allowed_permissions=allowed_permissions,
            top_k=top_k,
            filters=filters,
        )
