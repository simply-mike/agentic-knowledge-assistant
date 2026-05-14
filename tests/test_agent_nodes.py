from uuid import uuid4

from app.agents.nodes import (
    classify_intent,
    fallback_answer,
    grade_context,
    refuse_or_fallback,
    rewrite_query,
    route_by_intent,
    should_rewrite_or_answer,
)
from app.agents.state import initial_agent_state


def test_classify_docs_question() -> None:
    state = initial_agent_state("How do I configure Kafka ingestion?", "developer", "trace")

    update = classify_intent(state)

    assert update["intent"] == "docs_question"
    assert update["intent_confidence"] > 0
    assert update["candidate_intents"]


def test_classify_metrics_question() -> None:
    state = initial_agent_state("What is p95 latency?", "developer", "trace")

    update = classify_intent(state)

    assert update["intent"] == "metrics_question"


def test_classify_mixed_docs_and_metrics_prefers_docs_with_secondary_intent() -> None:
    state = initial_agent_state(
        "Explain Kafka latency metrics documentation",
        "developer",
        "trace",
    )

    update = classify_intent(state)

    assert update["intent"] == "docs_question"
    assert any(
        candidate["intent"] == "metrics_question" for candidate in update["candidate_intents"]
    )
    assert "secondary intents" in update["intent_reason"]


def test_classify_unknown_for_tiny_query() -> None:
    state = initial_agent_state("?", "developer", "trace")

    update = classify_intent(state)

    assert update["intent"] == "unknown"
    assert update["intent_confidence"] == 0.0


def test_route_docs_question_to_retrieval() -> None:
    state = initial_agent_state("How do I configure Kafka ingestion?", "developer", "trace")
    state["intent"] = "docs_question"

    assert route_by_intent(state) == "docs_question"


def test_grade_context_keeps_overlapping_chunks() -> None:
    state = initial_agent_state("Kafka ingestion", "developer", "trace")
    state["retrieved_chunks"] = [
        {
            "chunk_id": str(uuid4()),
            "document_id": str(uuid4()),
            "title": "Kafka Ingestion Runbook",
            "source": "synthetic_internal",
            "url": None,
            "category": "data_platform",
            "permission_level": "developer",
            "content": "Kafka ingestion jobs copy events.",
            "metadata": {},
            "token_count": 5,
            "distance": 0.1,
        }
    ]

    update = grade_context(state)

    assert update["graded_chunks"][0]["title"] == "Kafka Ingestion Runbook"
    assert update["graded_chunks"][0]["relevance_score"] > 0


def test_weak_context_rewrites_once_then_falls_back() -> None:
    state = initial_agent_state("nonsense", "developer", "trace")

    assert should_rewrite_or_answer(state) == "rewrite_query"
    update = rewrite_query(state)
    state.update(update)

    assert state["retry_count"] == 1
    assert should_rewrite_or_answer(state) == "fallback_answer"


def test_fallback_answer_has_no_citations() -> None:
    state = initial_agent_state("nonsense", "developer", "trace")

    update = fallback_answer(state)

    assert update["answer"]
    assert update["citations"] == []


def test_tool_intent_returns_phase_message() -> None:
    state = initial_agent_state("What is p95 latency?", "developer", "trace")
    state["intent"] = "metrics_question"

    update = refuse_or_fallback(state)

    assert "not implemented" in update["answer"]
