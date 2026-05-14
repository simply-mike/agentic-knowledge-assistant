from uuid import uuid4

from app.agents.nodes import (
    fallback_answer,
    generate_answer,
    grade_context,
    refuse_or_fallback,
    retrieve_context,
    rewrite_query,
    route_by_intent,
    should_finish_or_fallback,
    should_rewrite_or_answer,
    validate_grounding,
    classify_intent,
)
from app.agents.state import AgentState, initial_agent_state
from app.retrieval.rag import RAGResponse, SourceCitation
from app.retrieval.retriever import KnowledgeRetriever


class LangGraphAgent:
    def __init__(self, retriever: KnowledgeRetriever) -> None:
        self.retriever = retriever
        self.graph = _build_graph(retriever)

    def answer(
        self,
        query: str,
        role: str,
        top_k: int = 5,
        filters: dict | None = None,
    ) -> RAGResponse:
        state = initial_agent_state(
            user_query=query,
            user_role=role,
            trace_id=str(uuid4()),
            filters=filters,
            top_k=top_k,
        )
        final_state = self.graph.invoke(state)
        return RAGResponse(
            answer=final_state["answer"] or "",
            citations=[
                SourceCitation(
                    title=citation["title"],
                    url=citation["url"],
                    chunk_id=citation["chunk_id"],
                    source=citation["source"],
                )
                for citation in final_state["citations"]
            ],
            tool_calls=final_state["tool_calls"],
            trace_id=final_state["trace_id"],
        )


def _build_graph(retriever: KnowledgeRetriever):
    from langgraph.graph import END, START, StateGraph

    workflow = StateGraph(AgentState)
    workflow.add_node("classify_intent", classify_intent)
    workflow.add_node("retrieve_context", lambda state: retrieve_context(state, retriever))
    workflow.add_node("grade_context", grade_context)
    workflow.add_node("rewrite_query", rewrite_query)
    workflow.add_node("generate_answer", generate_answer)
    workflow.add_node("validate_grounding", validate_grounding)
    workflow.add_node("fallback_answer", fallback_answer)
    workflow.add_node("refuse_or_fallback", refuse_or_fallback)

    workflow.add_edge(START, "classify_intent")
    workflow.add_conditional_edges(
        "classify_intent",
        route_by_intent,
        {
            "docs_question": "retrieve_context",
            "refuse_or_fallback": "refuse_or_fallback",
        },
    )
    workflow.add_edge("retrieve_context", "grade_context")
    workflow.add_conditional_edges(
        "grade_context",
        should_rewrite_or_answer,
        {
            "generate_answer": "generate_answer",
            "rewrite_query": "rewrite_query",
            "fallback_answer": "fallback_answer",
        },
    )
    workflow.add_edge("rewrite_query", "retrieve_context")
    workflow.add_edge("generate_answer", "validate_grounding")
    workflow.add_conditional_edges(
        "validate_grounding",
        should_finish_or_fallback,
        {
            "end": END,
            "fallback_answer": "fallback_answer",
        },
    )
    workflow.add_edge("fallback_answer", END)
    workflow.add_edge("refuse_or_fallback", END)
    return workflow.compile()
