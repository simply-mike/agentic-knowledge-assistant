from uuid import uuid4

from app.retrieval.rag import BaselineRAGService, ExtractiveAnswerGenerator, refusal_answer
from app.retrieval.vector_store import RetrievedChunk


class FakeRetriever:
    def __init__(self, chunks: list[RetrievedChunk]) -> None:
        self.chunks = chunks
        self.last_call: dict | None = None

    def search(self, query: str, role: str, top_k: int = 5, filters: dict | None = None) -> list:
        self.last_call = {
            "query": query,
            "role": role,
            "top_k": top_k,
            "filters": filters,
        }
        return self.chunks


def test_baseline_rag_returns_refusal_without_context() -> None:
    service = BaselineRAGService(FakeRetriever([]))

    response = service.answer("Show confidential client metrics", role="developer")

    assert response.answer == refusal_answer()
    assert response.citations == []
    assert response.tool_calls == []


def test_baseline_rag_returns_answer_with_citations() -> None:
    chunk = _chunk(
        title="Kafka Ingestion Runbook",
        content="Kafka ingestion jobs copy events from approved Kafka topics into raw storage.",
    )
    service = BaselineRAGService(FakeRetriever([chunk]))

    response = service.answer("How do I configure Kafka ingestion?", role="developer")

    assert "Kafka ingestion jobs copy events" in response.answer
    assert response.citations[0].title == "Kafka Ingestion Runbook"
    assert response.citations[0].chunk_id == str(chunk.chunk_id)


def test_baseline_rag_passes_role_and_filters_to_retriever() -> None:
    retriever = FakeRetriever([])
    service = BaselineRAGService(retriever)

    service.answer(
        "How do I configure Kafka ingestion?",
        role="developer",
        top_k=3,
        filters={"category": "data_platform"},
    )

    assert retriever.last_call == {
        "query": "How do I configure Kafka ingestion?",
        "role": "developer",
        "top_k": 3,
        "filters": {"category": "data_platform"},
    }


def test_extractive_generator_limits_long_context() -> None:
    chunk = _chunk(
        title="Long Guide",
        content=" ".join(f"word{i}" for i in range(80)),
    )
    generator = ExtractiveAnswerGenerator()

    answer = generator.generate("summarize", [chunk])

    assert "word47..." in answer
    assert "word79" not in answer


def _chunk(title: str, content: str) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=uuid4(),
        document_id=uuid4(),
        title=title,
        source="synthetic_internal",
        url=None,
        category="data_platform",
        permission_level="developer",
        content=content,
        metadata={"chunk_index": 0},
        token_count=len(content.split()),
        distance=0.1,
    )
