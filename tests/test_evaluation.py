from pathlib import Path

from app.evaluation.dataset import EvalQuestion, load_eval_questions
from app.evaluation.metrics import aggregate_metrics, evaluate_response
from app.retrieval.rag import RAGResponse, SourceCitation


def test_eval_dataset_loads_questions() -> None:
    questions = load_eval_questions(Path("data/eval/questions.yaml"))

    assert len(questions) >= 20
    assert questions[0].id == "q001"
    assert questions[0].expected_sources


def test_evaluate_response_detects_source_hit_and_tool_call() -> None:
    question = EvalQuestion(
        id="q013",
        question="What was p95 latency?",
        role="data_analyst",
        expected_behavior="tool_call",
        expected_sources=["metrics_api_reference.md"],
        expected_tool="mock_metrics_api",
    )
    response = RAGResponse(
        answer="Synthetic metrics from the mock internal API.",
        citations=[
            SourceCitation(
                title="Metrics API Reference",
                url=None,
                chunk_id="chunk-1",
                source="synthetic_internal",
            )
        ],
        tool_calls=[{"tool": "mock_metrics_api"}],
        trace_id="trace",
    )

    result = evaluate_response(question, response)

    assert result.source_hit is True
    assert result.tool_call_correct is True


def test_aggregate_metrics_counts_denominators() -> None:
    question = EvalQuestion(
        id="q001",
        question="How do I configure Kafka ingestion?",
        role="developer",
        expected_behavior="answer",
        expected_sources=["kafka_ingestion_runbook.md"],
    )
    response = RAGResponse(
        answer="Grounded answer.",
        citations=[
            SourceCitation(
                title="Kafka Ingestion Runbook",
                url=None,
                chunk_id="chunk-1",
                source="synthetic_internal",
            )
        ],
        tool_calls=[],
        trace_id="trace",
    )

    metrics = aggregate_metrics([evaluate_response(question, response)])

    assert metrics["retrieval_hit_rate"]["score"] == 1.0
    assert metrics["answer_has_citation_rate"]["score"] == 1.0
