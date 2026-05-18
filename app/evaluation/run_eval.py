import argparse
import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from app.agents.graph import LangGraphAgent
from app.config import get_settings
from app.db.session import SessionLocal
from app.evaluation.dataset import EvalQuestion, filter_questions, load_eval_questions
from app.evaluation.metrics import QuestionEvaluation, aggregate_metrics, evaluate_response
from app.logging_config import configure_logging
from app.retrieval.embeddings import build_embedding_provider
from app.retrieval.rag import BaselineRAGService, RAGResponse
from app.retrieval.retriever import KnowledgeRetriever
from app.retrieval.vector_store import PGVectorStore
from app.tools.sql_tool import ReadOnlySQLTool


EvalMode = Literal["baseline", "agentic"]
AnswerFn = Callable[[EvalQuestion, int], RAGResponse]


def run_evaluation(
    dataset_path: Path,
    modes: list[EvalMode],
    top_k: int,
    tags: list[str] | None = None,
    roles: list[str] | None = None,
    behaviors: list[str] | None = None,
) -> dict:
    settings = get_settings()
    configure_logging(settings.log_level)
    questions = filter_questions(
        questions=load_eval_questions(dataset_path),
        tags=tags or [],
        roles=roles or [],
        behaviors=behaviors or [],
    )

    with SessionLocal() as db:
        embedding_provider = build_embedding_provider(settings)
        vector_store = PGVectorStore(db)
        retriever = KnowledgeRetriever(vector_store, embedding_provider)
        runners = _build_runners(modes, retriever, db)

        results = {
            mode: _run_mode(mode, runner, questions, top_k)
            for mode, runner in runners.items()
        }

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "dataset": str(dataset_path),
        "top_k": top_k,
        "filters": {
            "tags": tags or [],
            "roles": roles or [],
            "behaviors": behaviors or [],
        },
        "results": results,
    }


def _build_runners(modes: list[EvalMode], retriever: KnowledgeRetriever, db) -> dict[str, AnswerFn]:
    runners: dict[str, AnswerFn] = {}
    if "baseline" in modes:
        baseline = BaselineRAGService(retriever)
        runners["baseline"] = lambda question, top_k: baseline.answer(
            query=question.question,
            role=question.role,
            top_k=top_k,
            filters=question.filters,
        )
    if "agentic" in modes:
        agent = LangGraphAgent(retriever, sql_tool=ReadOnlySQLTool(db))
        runners["agentic"] = lambda question, top_k: agent.answer(
            query=question.question,
            role=question.role,
            top_k=top_k,
            filters=question.filters,
        )
    return runners


def _run_mode(
    mode: str,
    runner: AnswerFn,
    questions: list[EvalQuestion],
    top_k: int,
) -> dict:
    del mode
    evaluations: list[QuestionEvaluation] = []
    for question in questions:
        response = runner(question, top_k)
        evaluations.append(evaluate_response(question, response))

    return {
        "metrics": aggregate_metrics(evaluations),
        "per_question": [evaluation.as_dict() for evaluation in evaluations],
    }


def _parse_modes(value: str) -> list[EvalMode]:
    if value == "both":
        return ["baseline", "agentic"]
    if value in {"baseline", "agentic"}:
        return [value]  # type: ignore[list-item]
    raise ValueError(f"Unsupported evaluation mode: {value}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run RAG evaluation dataset.")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path("data/eval/questions.yaml"),
        help="Path to YAML evaluation dataset.",
    )
    parser.add_argument(
        "--mode",
        choices=("baseline", "agentic", "both"),
        default="both",
        help="Evaluation mode to run.",
    )
    parser.add_argument("--top-k", type=int, default=5, help="Retriever top_k.")
    parser.add_argument(
        "--tag",
        action="append",
        default=[],
        help="Run only questions with this tag. Can be passed multiple times.",
    )
    parser.add_argument(
        "--role",
        action="append",
        default=[],
        help="Run only questions for this role. Can be passed multiple times.",
    )
    parser.add_argument(
        "--behavior",
        action="append",
        default=[],
        help="Run only questions with this expected behavior. Can be passed multiple times.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional path to write the JSON report.",
    )
    args = parser.parse_args()

    report = run_evaluation(
        dataset_path=args.dataset,
        modes=_parse_modes(args.mode),
        top_k=args.top_k,
        tags=args.tag,
        roles=args.role,
        behaviors=args.behavior,
    )
    rendered_report = json.dumps(report, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered_report + "\n", encoding="utf-8")
    print(rendered_report)


if __name__ == "__main__":
    main()
