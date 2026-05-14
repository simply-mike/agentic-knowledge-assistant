from uuid import uuid4

from app.agents.graph import LangGraphAgent
from app.retrieval.vector_store import RetrievedChunk


class FakeRetriever:
    def __init__(self, chunks: list[RetrievedChunk]) -> None:
        self.chunks = chunks
        self.calls: list[dict] = []

    def search(self, query: str, role: str, top_k: int = 5, filters: dict | None = None) -> list:
        self.calls.append(
            {
                "query": query,
                "role": role,
                "top_k": top_k,
                "filters": filters,
            }
        )
        return self.chunks


def test_langgraph_agent_answers_docs_question_with_citation() -> None:
    retriever = FakeRetriever(
        [
            _chunk(
                title="Kafka Ingestion Runbook",
                content="Kafka ingestion jobs copy events from approved Kafka topics.",
            )
        ]
    )
    agent = LangGraphAgent(retriever)

    response = agent.answer("How do I configure Kafka ingestion?", role="developer")

    assert "Kafka ingestion jobs copy events" in response.answer
    assert response.citations[0].title == "Kafka Ingestion Runbook"
    assert retriever.calls[0]["role"] == "developer"
    assert retriever.calls[0]["top_k"] == 5


def test_langgraph_agent_passes_top_k_and_filters() -> None:
    retriever = FakeRetriever(
        [
            _chunk(
                title="Kafka Ingestion Runbook",
                content="Kafka ingestion jobs copy events from approved Kafka topics.",
            )
        ]
    )
    agent = LangGraphAgent(retriever)

    agent.answer(
        "How do I configure Kafka ingestion?",
        role="developer",
        top_k=2,
        filters={"category": "data_platform"},
    )

    assert retriever.calls[0]["top_k"] == 2
    assert retriever.calls[0]["filters"] == {"category": "data_platform"}


def test_langgraph_agent_falls_back_without_context() -> None:
    agent = LangGraphAgent(FakeRetriever([]))

    response = agent.answer("How do I configure Kafka ingestion?", role="developer")

    assert "do not have enough permitted" in response.answer
    assert response.citations == []


def test_langgraph_agent_refuses_tool_branch_until_phase_8() -> None:
    agent = LangGraphAgent(FakeRetriever([]))

    response = agent.answer("What is p95 latency for kafka_ingestion?", role="data_analyst")

    assert "not implemented" in response.answer
    assert response.citations == []


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
        metadata={},
        token_count=len(content.split()),
        distance=0.1,
    )
