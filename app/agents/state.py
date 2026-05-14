from typing import Any, Literal, TypedDict


Intent = Literal[
    "docs_question",
    "metrics_question",
    "sql_question",
    "access_request",
    "general_chat",
    "unknown",
]


class AgentState(TypedDict):
    user_query: str
    user_role: str
    intent: Intent | None
    intent_confidence: float
    candidate_intents: list[dict[str, Any]]
    intent_reason: str | None
    rewritten_query: str | None
    retrieved_chunks: list[dict[str, Any]]
    graded_chunks: list[dict[str, Any]]
    tool_calls: list[dict[str, Any]]
    tool_results: list[dict[str, Any]]
    answer: str | None
    citations: list[dict[str, Any]]
    errors: list[str]
    retry_count: int
    trace_id: str
    filters: dict[str, Any] | None
    top_k: int


def initial_agent_state(
    user_query: str,
    user_role: str,
    trace_id: str,
    filters: dict[str, Any] | None = None,
    top_k: int = 5,
) -> AgentState:
    return AgentState(
        user_query=user_query,
        user_role=user_role,
        intent=None,
        intent_confidence=0.0,
        candidate_intents=[],
        intent_reason=None,
        rewritten_query=None,
        retrieved_chunks=[],
        graded_chunks=[],
        tool_calls=[],
        tool_results=[],
        answer=None,
        citations=[],
        errors=[],
        retry_count=0,
        trace_id=trace_id,
        filters=filters,
        top_k=top_k,
    )
