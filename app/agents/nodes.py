import re
from collections.abc import Sequence
from typing import Any

from app.agents.intent import classify_query_intent
from app.agents.prompts import NO_CONTEXT_MESSAGE, UNSUPPORTED_TOOL_MESSAGE
from app.agents.state import AgentState
from app.retrieval.rag import ExtractiveAnswerGenerator, SourceCitation
from app.retrieval.vector_store import RetrievedChunk
from app.tools.mock_metrics_api import infer_period, infer_pipeline_name, mock_metrics_api
from app.tools.sql_tool import UnsafeSQLQueryError, build_pipeline_runs_query


class RetrieverDependency:
    def search(
        self,
        query: str,
        role: str,
        top_k: int = 5,
        filters: dict[str, Any] | None = None,
    ) -> list[RetrievedChunk]:
        raise NotImplementedError


class SQLToolDependency:
    def run(self, sql_query: str) -> dict[str, Any]:
        raise NotImplementedError


def classify_intent(state: AgentState) -> dict[str, Any]:
    classification = classify_query_intent(state["user_query"])
    intent = classification.intent
    reason = classification.reason
    if _is_restricted_confidential_query(state):
        intent = "access_request"
        reason = "restricted confidential query for non-admin role"
    elif _is_admin_confidential_policy_query(state):
        intent = "docs_question"
        reason = "admin confidential policy query can use permitted docs"

    return {
        "intent": intent,
        "intent_confidence": classification.confidence,
        "candidate_intents": [
            {
                "intent": candidate.intent,
                "score": candidate.score,
                "matched_terms": list(candidate.matched_terms),
            }
            for candidate in classification.candidates
        ],
        "intent_reason": reason,
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


def retrieve_related_docs(state: AgentState, retriever: RetrieverDependency) -> dict[str, Any]:
    query = _related_docs_query(state)
    chunks = retriever.search(
        query=query,
        role=state["user_role"],
        top_k=min(state["top_k"], 3),
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
    if state["answer"] and (state["citations"] or state["tool_results"]):
        return {}
    return {"errors": [*state["errors"], "answer_not_grounded"]}


def should_finish_or_fallback(state: AgentState) -> str:
    if state["answer"] and (state["citations"] or state["tool_results"]):
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


def call_mock_metrics_api(
    state: AgentState,
    metrics_client=mock_metrics_api,
) -> dict[str, Any]:
    pipeline_name = infer_pipeline_name(state["user_query"])
    period = infer_period(state["user_query"])
    result = metrics_client(pipeline_name=pipeline_name, period=period)
    tool_call = {
        "tool": "mock_metrics_api",
        "args": {"pipeline_name": pipeline_name, "period": period},
        "status": "ok",
    }
    tool_result = {"tool": "mock_metrics_api", "result": result}
    return {
        "tool_calls": [*state["tool_calls"], tool_call],
        "tool_results": [*state["tool_results"], tool_result],
    }


def generate_answer_with_tool_result(state: AgentState) -> dict[str, Any]:
    metrics_result = _latest_tool_result(state, "mock_metrics_api")
    if not metrics_result:
        return fallback_answer(state)

    metrics = metrics_result["result"]
    answer = (
        "Synthetic metrics from the mock internal API:\n\n"
        f"- Pipeline: {metrics['pipeline_name']}\n"
        f"- Period: {metrics['period']}\n"
        f"- Average latency: {metrics['avg_latency_ms']} ms\n"
        f"- P95 latency: {metrics['p95_latency_ms']} ms\n"
        f"- Failed jobs: {metrics['failed_jobs']}\n"
        f"- Success rate: {metrics['success_rate']:.3f}\n\n"
        "These values are synthetic demo metrics, not production telemetry."
    )
    citations = [
        _citation_to_dict(citation)
        for citation in _citations_from_chunks(
            _dict_to_chunk(chunk) for chunk in state["retrieved_chunks"]
        )
    ]
    return {"answer": answer, "citations": citations}


def generate_safe_sql(state: AgentState) -> dict[str, Any]:
    sql_query = build_pipeline_runs_query(state["user_query"])
    return {"generated_sql": sql_query}


def run_sql_tool(state: AgentState, sql_tool: SQLToolDependency | None) -> dict[str, Any]:
    sql_query = state["generated_sql"]
    if sql_query is None:
        return {"errors": [*state["errors"], "sql_generation_failed"]}
    if sql_tool is None:
        return {"errors": [*state["errors"], "sql_tool_unavailable"]}

    tool_call = {
        "tool": "sql_tool",
        "args": {"sql_query": sql_query},
        "status": "ok",
    }
    try:
        result = sql_tool.run(sql_query)
    except UnsafeSQLQueryError as exc:
        tool_call["status"] = "rejected"
        return {
            "tool_calls": [*state["tool_calls"], tool_call],
            "errors": [*state["errors"], str(exc)],
        }

    return {
        "tool_calls": [*state["tool_calls"], tool_call],
        "tool_results": [*state["tool_results"], {"tool": "sql_tool", "result": result}],
    }


def generate_answer_with_table(state: AgentState) -> dict[str, Any]:
    sql_result = _latest_tool_result(state, "sql_tool")
    if not sql_result:
        return fallback_answer(state)

    result = sql_result["result"]
    rows = result["rows"]
    if not rows:
        answer = (
            "The read-only SQL tool returned no matching demo pipeline runs. "
            f"SQL used: `{result['sql']}`"
        )
        return {"answer": answer, "citations": []}

    row_summaries = []
    for row in rows[:5]:
        row_summaries.append(
            "- "
            f"{row['pipeline_name']} at {row['started_at']}: "
            f"{row['status']}, records={row['records_processed']}, "
            f"latency_ms={row['latency_ms']}, error_code={row['error_code']}"
        )
    answer = (
        "The read-only SQL tool queried the local demo `pipeline_runs` table.\n\n"
        + "\n".join(row_summaries)
        + f"\n\nRows returned: {result['row_count']}. SQL used: `{result['sql']}`"
    )
    return {"answer": answer, "citations": []}


def route_by_intent(state: AgentState) -> str:
    if state["intent"] == "docs_question":
        return "docs_question"
    if state["intent"] == "metrics_question":
        return "metrics_question"
    if state["intent"] == "sql_question":
        return "sql_question"
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


def _related_docs_query(state: AgentState) -> str:
    if state["intent"] == "metrics_question":
        pipeline_name = infer_pipeline_name(state["user_query"])
        return f"{pipeline_name} metrics api reference sla runbook"
    return state["user_query"]


def _latest_tool_result(state: AgentState, tool_name: str) -> dict[str, Any] | None:
    for tool_result in reversed(state["tool_results"]):
        if tool_result["tool"] == tool_name:
            return tool_result
    return None


def _is_restricted_confidential_query(state: AgentState) -> bool:
    return "confidential" in state["user_query"].lower() and state["user_role"] != "admin"


def _is_admin_confidential_policy_query(state: AgentState) -> bool:
    normalized = state["user_query"].lower()
    return (
        state["user_role"] == "admin"
        and "confidential" in normalized
        and "policy" in normalized
    )
