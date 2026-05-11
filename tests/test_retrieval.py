from types import SimpleNamespace
from uuid import uuid4

from app.retrieval.retriever import KnowledgeRetriever
from app.retrieval.vector_store import _row_to_retrieved_chunk, normalize_retrieval_filters


class FakeEmbeddingProvider:
    dimensions = 3

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [[1.0, 0.0, 0.0] for _ in texts]

    def embed_query(self, text: str) -> list[float]:
        return [1.0, 0.0, 0.0]


class FakeVectorStore:
    def __init__(self) -> None:
        self.last_call: dict | None = None

    def search_by_vector(
        self,
        query_embedding: list[float],
        allowed_permissions: list[str],
        top_k: int,
        filters: dict | None = None,
    ) -> list:
        self.last_call = {
            "query_embedding": query_embedding,
            "allowed_permissions": allowed_permissions,
            "top_k": top_k,
            "filters": filters,
        }
        return []


def test_normalize_filters_always_applies_role_permissions() -> None:
    filters = normalize_retrieval_filters(None, ["public", "developer"])

    assert filters == {"permission_level": ["public", "developer"]}


def test_permission_filter_can_narrow_but_not_expand_access() -> None:
    filters = normalize_retrieval_filters(
        {"permission_level": ["analytics", "developer"], "category": "data_platform"},
        ["public", "developer"],
    )

    assert filters["permission_level"] == ["developer"]
    assert filters["category"] == ["data_platform"]


def test_retriever_passes_role_permissions_to_vector_store() -> None:
    vector_store = FakeVectorStore()
    retriever = KnowledgeRetriever(vector_store, FakeEmbeddingProvider())

    retriever.search("kafka ingestion", role="developer", top_k=3)

    assert vector_store.last_call == {
        "query_embedding": [1.0, 0.0, 0.0],
        "allowed_permissions": ["public", "developer"],
        "top_k": 3,
        "filters": None,
    }


def test_row_to_retrieved_chunk_maps_database_row() -> None:
    chunk_id = uuid4()
    document_id = uuid4()
    row = SimpleNamespace(
        _mapping={
            "chunk_id": chunk_id,
            "document_id": document_id,
            "title": "Kafka Runbook",
            "source": "synthetic_internal",
            "url": None,
            "category": "data_platform",
            "permission_level": "developer",
            "content": "Configure Kafka ingestion.",
            "metadata_json": {"chunk_index": 0},
            "token_count": 3,
            "distance": 0.25,
        }
    )

    chunk = _row_to_retrieved_chunk(row)

    assert chunk.chunk_id == chunk_id
    assert chunk.document_id == document_id
    assert chunk.metadata == {"chunk_index": 0}
    assert chunk.distance == 0.25
