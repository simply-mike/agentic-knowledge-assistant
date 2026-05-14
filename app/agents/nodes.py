import re
from collections.abc import Sequence
from typing import Any

from app.agents.intent import classify_query_intent
from app.agents.prompts import NO_CONTEXT_MESSAGE, UNSUPPORTED_TOOL_MESSAGE
from app.agents.state import AgentState
from app.retrieval.rag import ExtractiveAnswerGenerator, SourceCitation
from app.retrieval.vector_store import RetrievedChunk


class RetrieverDependency:
    def search(
        self,
        query: str,
        role: str,
        top_k: int = 5,
        filters: dict[str, Any] | None = None,
    ) -> list[RetrievedChunk]:
        raise NotImplementedError


def classify_intent(state: AgentState) -> dict[str, Any]:
    classification = classify_query_intent(state["user_query"])
    return {
        "intent": classification.intent,
        "intent_confidence": classification.confidence,
        "candidate_intents": [
            {
                "intent": candidate.intent,
                "score": candidate.score,
                "matched_terms": list(candidate.matched_terms),
            }
            for candidate in classification.candidates
        ],
        "intent_reason": classification.reason,
    }


def retrieve_context(state: AgentState, retriever: RetrieverDependency) -> dict[str, Any]:
    query = state["rewritten_query"] or state["user_query"]
    chunks = retriever.search(
        query=query,
        role=state["user_role"],
        top_k=state["top_k"],
        filters=state["filters"],
    )
    return {"retrieved_chunks": [_chunk_to_dict(chunk) for chunk in chunks]}


def grade_context(state: AgentState) -> dict[str, Any]:
    query_terms = _important_terms(state["rewritten_query"] or state["user_query"])
    graded_chunks: list[dict[str, Any]] = []
    for chunk in state["retrieved_chunks"]:
        content_terms = _important_terms(chunk["content"])
        overlap = len(query_terms & content_terms)
        if overlap > 0 or not query_terms:
            graded_chunks.append({**chunk, "relevance_score": overlap})
    return {"graded_chunks": graded_chunks}


def should_rewrite_or_answer(state: AgentState) -> str:
    if state["graded_chunks"]:
        return "generate_answer"
    if state["retry_count"] < 1:
        return "rewrite_query"
    return "fallback_answer"


def rewrite_query(state: AgentState) -> dict[str, Any]:
    rewritten = _rewrite_query_text(state["user_query"])
    return {
        "rewritten_query": rewritten,
        "retry_count": state["retry_count"] + 1,
    }


def generate_answer(state: AgentState) -> dict[str, Any]:
    chunks = [_dict_to_chunk(chunk) for chunk in state["graded_chunks"]]
    answer = ExtractiveAnswerGenerator().generate(state["user_query"], chunks)
    citations = [_citation_to_dict(citation) for citation in _citations_from_chunks(chunks)]
    return {"answer": answer, "citations": citations}


def validate_grounding(state: AgentState) -> dict[str, Any]:
    if state["answer"] and state["citations"]:
        return {}
    return {"errors": [*state["errors"], "answer_not_grounded"]}


def should_finish_or_fallback(state: AgentState) -> str:
    if state["answer"] and state["citations"]:
        return "end"
    return "fallback_answer"


def fallback_answer(state: AgentState) -> dict[str, Any]:
    return {
        "answer": NO_CONTEXT_MESSAGE,
        "citations": [],
    }


def refuse_or_fallback(state: AgentState) -> dict[str, Any]:
    intent = state["intent"]
    if intent in {"metrics_question", "sql_question"}:
        message = UNSUPPORTED_TOOL_MESSAGE
    elif intent == "general_chat":
        message = "Ask me a question about the indexed knowledge base and I will cite sources."
    else:
        message = NO_CONTEXT_MESSAGE
    return {"answer": message, "citations": []}


def route_by_intent(state: AgentState) -> str:
    if state["intent"] == "docs_question":
        return "docs_question"
    return "refuse_or_fallback"


def _chunk_to_dict(chunk: RetrievedChunk) -> dict[str, Any]:
    return {
        "chunk_id": str(chunk.chunk_id),
        "document_id": str(chunk.document_id),
        "title": chunk.title,
        "source": chunk.source,
        "url": chunk.url,
        "category": chunk.category,
        "permission_level": chunk.permission_level,
        "content": chunk.content,
        "metadata": chunk.metadata,
        "token_count": chunk.token_count,
        "distance": chunk.distance,
    }


def _dict_to_chunk(chunk: dict[str, Any]) -> RetrievedChunk:
    from uuid import UUID

    return RetrievedChunk(
        chunk_id=UUID(chunk["chunk_id"]),
        document_id=UUID(chunk["document_id"]),
        title=chunk["title"],
        source=chunk["source"],
        url=chunk["url"],
        category=chunk["category"],
        permission_level=chunk["permission_level"],
        content=chunk["content"],
        metadata=chunk["metadata"],
        token_count=chunk["token_count"],
        distance=chunk["distance"],
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


def _citation_to_dict(citation: SourceCitation) -> dict[str, Any]:
    return {
        "title": citation.title,
        "url": citation.url,
        "chunk_id": citation.chunk_id,
        "source": citation.source,
    }


def _important_terms(text: str) -> set[str]:
    stop_words = {"the", "a", "an", "and", "or", "to", "of", "in", "is", "what", "how"}
    return {
        term
        for term in re.findall(r"[a-zA-Z0-9_]+", text.lower())
        if len(term) > 2 and term not in stop_words
    }


def _rewrite_query_text(query: str) -> str:
    stripped = query.strip()
    if "configure" in stripped.lower():
        return stripped
    return f"{stripped} documentation guide overview"
