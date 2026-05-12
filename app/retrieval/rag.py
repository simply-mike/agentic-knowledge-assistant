from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol
from uuid import UUID, uuid4

from app.retrieval.vector_store import RetrievedChunk


@dataclass(frozen=True)
class SourceCitation:
    title: str
    url: str | None
    chunk_id: str
    source: str


@dataclass(frozen=True)
class RAGResponse:
    answer: str
    citations: list[SourceCitation]
    tool_calls: list[dict[str, Any]]
    trace_id: str


class RetrieverProtocol(Protocol):
    def search(
        self,
        query: str,
        role: str,
        top_k: int = 5,
        filters: Mapping[str, Any] | None = None,
    ) -> list[RetrievedChunk]:
        ...


class ExtractiveAnswerGenerator:
    """Builds a conservative answer from retrieved chunks only."""

    def generate(self, query: str, chunks: Sequence[RetrievedChunk]) -> str:
        if not chunks:
            return refusal_answer()

        parts = [
            "I found relevant knowledge-base context. Here is a grounded baseline answer:",
        ]
        for index, chunk in enumerate(chunks[:3], start=1):
            snippet = _compact_snippet(chunk.content)
            parts.append(f"{index}. {snippet} [source: {chunk.title}]")

        parts.append("Use the cited sources below to inspect the supporting context.")
        return "\n\n".join(parts)


class BaselineRAGService:
    def __init__(
        self,
        retriever: RetrieverProtocol,
        answer_generator: ExtractiveAnswerGenerator | None = None,
    ) -> None:
        self.retriever = retriever
        self.answer_generator = answer_generator or ExtractiveAnswerGenerator()

    def answer(
        self,
        query: str,
        role: str,
        top_k: int = 5,
        filters: Mapping[str, Any] | None = None,
        trace_id: UUID | None = None,
    ) -> RAGResponse:
        current_trace_id = str(trace_id or uuid4())
        chunks = self.retriever.search(query=query, role=role, top_k=top_k, filters=filters)
        if not chunks:
            return RAGResponse(
                answer=refusal_answer(),
                citations=[],
                tool_calls=[],
                trace_id=current_trace_id,
            )

        return RAGResponse(
            answer=self.answer_generator.generate(query, chunks),
            citations=_citations_from_chunks(chunks),
            tool_calls=[],
            trace_id=current_trace_id,
        )


def refusal_answer() -> str:
    return (
        "I do not have enough permitted knowledge-base context to answer this. "
        "Try rephrasing the question or using a role with access to the relevant documents."
    )


def _citations_from_chunks(chunks: Sequence[RetrievedChunk]) -> list[SourceCitation]:
    citations: list[SourceCitation] = []
    seen_chunk_ids: set[str] = set()
    for chunk in chunks:
        chunk_id = str(chunk.chunk_id)
        if chunk_id in seen_chunk_ids:
            continue
        seen_chunk_ids.add(chunk_id)
        citations.append(
            SourceCitation(
                title=chunk.title,
                url=chunk.url,
                chunk_id=chunk_id,
                source=chunk.source,
            )
        )
    return citations


def _compact_snippet(content: str, max_words: int = 48) -> str:
    words = content.split()
    if len(words) <= max_words:
        return " ".join(words)
    return " ".join(words[:max_words]) + "..."
